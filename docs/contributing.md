# Contributing

We welcome contributions to mol-platform! Please follow these guidelines.

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/coccinella-labs/mol-platform.git`
3. Set up development environment (see [Installation](installation.md))
4. Create a feature branch: `git checkout -b feature/your-feature`

## Code Style

- **Python:** Follow PEP 8, use ruff for linting
- **JavaScript/React:** Follow ESLint rules
- **Commits:** Use conventional commits (feat, fix, docs, etc.)

## Testing

- Write tests for new features
- Ensure all tests pass: `python -m pytest tests/ -v`
- Test both backend and frontend changes

## Pull Request Process

1. Update documentation as needed
2. Ensure CI passes
3. Fill out the PR template completely
4. Request review from maintainers

## Commit Convention

This project follows the **Conventional Commits** specification.

### Format Rules

* Begin with a type: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`, `revert`
* Use lowercase
* Keep the summary ≤ 60 characters

Example:
```
feat: add new molecule visualization
fix: resolve docker build issue
docs: update API documentation
```

## Issue Reporting

- Use GitHub Issues for bugs and feature requests
- Provide detailed steps to reproduce bugs
- Include environment information

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.