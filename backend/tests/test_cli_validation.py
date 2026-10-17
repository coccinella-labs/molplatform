"""Boundary tests for CLI validation of the mutation count.

The server rejects num_mutations above MAX_MUTATIONS_PER_REQUEST with a 400.
Before this change the CLI accepted any such value, confirmed it with
"Mutations set to N", and only surfaced the rejection later as an opaque HTTP
failure. These tests pin the expected local behaviour instead.

The contract these tests encode:

  * Values from 0 to MAX_MUTATIONS_PER_REQUEST inclusive are accepted. 0 is
    included because the server's own lower bound is non-negative, and a CLI
    that rejected 0 locally would be stricter than the API it calls.
  * Values above the bound are rejected locally, with a message that names the
    limit rather than deferring to an HTTP error.
  * A rejected value leaves the previously accepted value in place. The CLI
    should not corrupt session state on bad input.
  * The bound itself does not move. The CLI ships as a standalone PyInstaller
    binary and cannot import the server module, so the value is duplicated;
    test_cli_bound_matches_server guards against that duplication drifting.

Run with: cd backend && python -m pytest tests/test_cli_validation.py -v
"""

import builtins
import io
from contextlib import redirect_stdout

import pytest

from src import cli
from src.main import MAX_MUTATIONS_PER_REQUEST

# Values the CLI must accept, and values it must refuse.
ACCEPTED = [0, 1, 3, 9, 10]
REJECTED_HIGH = [11, 50, 1000]


def run_interactive(script: str) -> str:
    """Drive interactive_mode with a scripted stdin and return its output."""
    lines = iter(script.splitlines())
    original = builtins.input

    def fake_input(prompt=""):
        try:
            return next(lines)
        except StopIteration:
            raise EOFError

    builtins.input = fake_input
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            cli.interactive_mode("http://127.0.0.1:1", "key")
    except EOFError:
        # Expected once the script runs out. interactive_mode treats EOF as
        # end of input and returns, so reaching here just means the loop ended
        # rather than being quit explicitly. Swallowing it lets the caller read
        # whatever the loop printed up to that point, which is the whole point
        # of capturing output instead of asserting on a return value.
        pass
    finally:
        builtins.input = original
    return out.getvalue()


def set_and_report(value: str) -> tuple:
    """Run 'set mutations <value>' then 'status'; return (stored, messages)."""
    text = run_interactive(f"set mutations {value}\nstatus\nquit\n")
    stored = None
    for line in text.splitlines():
        if line.startswith("Mutations:"):
            stored = line.split(":", 1)[1].strip()
    messages = [
        line for line in text.splitlines() if "Mutations set" in line or "Error" in line
    ]
    return stored, messages


@pytest.mark.parametrize("value", ACCEPTED)
def test_interactive_accepts_values_within_bound(value):
    """Every value the server would accept is accepted locally, unchanged."""
    stored, messages = set_and_report(str(value))
    assert stored == str(value), f"{value} should be stored, got {stored}"
    assert any("Mutations set" in m for m in messages), messages


def test_interactive_accepts_zero_because_the_server_does():
    """0 is valid at the API, so the CLI must not be stricter than the API.

    Guards a specific over-correction: rejecting 0 locally while the server
    accepts it would make the CLI refuse requests the API would serve.
    """
    stored, _ = set_and_report("0")
    assert stored == "0"


@pytest.mark.parametrize("value", REJECTED_HIGH)
def test_interactive_rejects_values_above_bound(value):
    """An out-of-range value is refused at set time, not at generate time."""
    stored, messages = set_and_report(str(value))
    assert not any("Mutations set" in m for m in messages), (
        f"{value} must not be confirmed as accepted: {messages}"
    )
    assert any("Error" in m for m in messages), messages


def test_interactive_rejection_names_the_limit():
    """The error tells the user the actual limit instead of a bare refusal."""
    _, messages = set_and_report("50")
    joined = " ".join(messages)
    assert str(MAX_MUTATIONS_PER_REQUEST) in joined, joined


def test_interactive_rejection_preserves_previous_value():
    """A bad value must not wipe out the value already in the session."""
    text = run_interactive("set mutations 5\nset mutations 50\nstatus\nquit\n")
    stored = [
        line.split(":", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith("Mutations:")
    ]
    assert stored == ["5"], stored


@pytest.mark.parametrize("value", ["-1", "abc", "3.5"])
def test_interactive_rejects_bad_numbers_and_keeps_previous(value):
    """Non-numeric and negative input are refused and state is untouched.

    This is pre-existing behaviour, asserted so the new upper-bound check does
    not regress the lower bound that was already handled.
    """
    text = run_interactive(f"set mutations 4\nset mutations {value}\nstatus\nquit\n")
    stored = [
        line.split(":", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith("Mutations:")
    ]
    assert stored == ["4"], stored


@pytest.mark.parametrize("value", REJECTED_HIGH)
def test_argparse_path_rejects_above_bound(value, monkeypatch):
    """--mutations above the bound exits non-zero without making a request."""
    sent = []

    def fake_post(*args, **kwargs):
        sent.append(kwargs.get("json"))
        raise AssertionError("no request should be sent for an invalid count")

    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "--api-key", "k", "--generate", "CCO", "--mutations", str(value)],
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main()
    assert rc != 0, f"exit code should be non-zero for {value}, got {rc}"
    assert sent == [], sent
    assert str(MAX_MUTATIONS_PER_REQUEST) in out.getvalue()


@pytest.mark.parametrize("value", ["-1", "-10", "50"])
def test_health_alone_ignores_the_mutation_count(value, monkeypatch):
    """--mutations is only read for generation, so --health must not trip on it.

    Added after self-review found the range check firing for a value the run
    never uses. On main, `--health --mutations 50` reaches the health endpoint;
    an unconditional check rejects it before connecting, which is a
    behaviour change unrelated to validating generation.
    """
    seen = []

    class Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"status": "healthy", "version": "0"}

    def fake_get(url, headers=None, **kwargs):
        seen.append(url)
        return Resp()

    monkeypatch.setattr(cli.requests, "get", fake_get)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "--api-key", "k", "--health", "--mutations", str(value)],
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main()
    assert rc == 0, out.getvalue()
    assert seen, "the health request should still have been made"
    assert "must be between 0 and" not in out.getvalue(), out.getvalue()


@pytest.mark.parametrize("value", ["-1", "-10"])
def test_argparse_path_rejects_negative(value, monkeypatch):
    """--mutations below zero exits non-zero without making a request.

    Added after mutation testing found the lower bound of this check was
    uncovered: widening it to accept negatives left the suite green.
    """
    sent = []

    def fake_post(*args, **kwargs):
        sent.append(kwargs.get("json"))
        raise AssertionError("no request should be sent for an invalid count")

    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "--api-key", "k", "--generate", "CCO", "--mutations", str(value)],
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main()
    assert rc != 0, f"exit code should be non-zero for {value}, got {rc}"
    assert sent == [], sent


@pytest.mark.parametrize("value", ACCEPTED)
def test_argparse_path_allows_within_bound(value, monkeypatch):
    """A valid --mutations value still reaches the request path."""
    sent = []

    class Resp:
        status_code = 200

        @staticmethod
        def json():
            return {
                "original_smiles": "CCO",
                "generated_smiles": "CCO",
                "properties": {},
                "requested_mutations": value,
                "successful_mutations": value,
                "failed_mutations": 0,
                "mutated": True,
            }

    def fake_post(url, json=None, headers=None, **kwargs):
        sent.append(json)
        return Resp()

    monkeypatch.setattr(cli.requests, "post", fake_post)
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "--api-key", "k", "--generate", "CCO", "--mutations", str(value)],
    )
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main()
    assert rc == 0, out.getvalue()
    assert sent and sent[0]["num_mutations"] == value


def test_cli_bound_matches_server():
    """The duplicated constant has not drifted from the server's.

    cli.py cannot import from main.py: it is frozen by PyInstaller as a
    standalone entry script with no package context, so the value is written
    out again. This test is the only thing standing between that duplication
    and a silent mismatch.
    """
    assert cli.MAX_MUTATIONS_PER_REQUEST == MAX_MUTATIONS_PER_REQUEST
