<p align="center">
  <img src="https://raw.githubusercontent.com/Coccinella-Labs/molplatform/main/.github/assets/thumbnail.png" alt="molplatform" width="100%">
</p>

# mol-platform

A containerized microservice for molecular generation and analysis. Generates molecular variants through systematic mutations using RDKit. Features a REST API, web interface, and CLI tool with secure API key authentication.

---

## Prerequisites

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/)

---

## Execution

To initiate the platform:

```bash
docker-compose up --build
```

## Command Line Testing

For testing without the web interface, install and use the provided CLI tool:

```bash
# Build and install CLI (one-time)
cd backend
python3 -m venv venv && source venv/bin/activate && pip install build && python -m build
pipx install dist/mol_platform-1.0.0-py3-none-any.whl

# Test health
mol-platform --api-key your-key --health

# Generate molecule
mol-platform --api-key your-key --generate "CC(=O)OC1=CC=CC=C1C(=O)O"
```

## Access Points

- **API Documentation:** http://localhost:8000/docs
- **Frontend Interface:** http://localhost:3000

---

## API Reference

### Molecule Generation

**Endpoint:** `POST /generate_molecule`

Facilitates the creation of molecular variants through systematic mutations.

**Request Structure**

```json
{
  "base_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
  "num_mutations": 3,
  "mutation_types": ["substituent", "bond_order", "atom_swap"]
}
```

**Parameters:**
- `base_smiles`: SMILES representation (required)
- `num_mutations`: Mutation count (optional, default: 3)
- `mutation_types`: Permitted mutation categories (optional)

**Response Structure:**
```json
{
  "original_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
  "generated_smiles": "CC(=O)Oc1cSCN)cccc1C(=O)O",
  "molecular_image": "base64_encoded_png",
  "properties": {
    "Molecular Weight": 180.16,
    "LogP": 1.31,
    "H-Bond Donors": 1,
    "H-Bond Acceptors": 3,
    "Topological Polar Surface Area": 63.6
  }
}
```

**Available Mutations:**
- `substituent`: Introduces substituent groups
- `bond_order`: Adjusts bonding configurations
- `atom_swap`: Exchanges atomic elements

### Health Verification

**Endpoint:** `GET /health`

Provides service status confirmation.

**Response Structure:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```