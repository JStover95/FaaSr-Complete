# FaaSr Framework - Repository Coordination Overview

This document provides a high-level overview of how the three core FaaSr repositories coordinate to enable serverless Function-as-a-Service (FaaS) workflows across multiple cloud platforms.

## Repository Architecture

The FaaSr framework consists of three interdependent repositories:

```plaintext
┌─────────────────────┐
│  faasr-workflow     │  User-facing workflow management
│  (GitHub Actions)   │  • Workflow JSON schemas
└──────────┬──────────┘  • Registration/Invocation
           │              • Credentials storage
           │
           ├──────────────────────────────────┐
           ▼                                  ▼
┌─────────────────────┐           ┌─────────────────────┐
│   faasr-docker      │           │   faasr-backend     │
│   (Containers)      │◄──────────│   (FaaSr_py)        │
│   • Base images     │   Used by │   • Orchestration   │
│   • Platform images │           │   • Validation      │
│   • Entry points    │           │   • S3 API          │
└─────────────────────┘           └─────────────────────┘
```

## 1. faasr-workflow: Workflow Management Repository

**Purpose:** Central hub for workflow configuration, registration, and invocation

### Key Components

- **Workflow JSON Schemas**: DAG definitions with actions, dependencies, and configurations
- **GitHub Actions**:
  - `FAASR REGISTER`: Deploys workflows to cloud platforms
  - `FAASR INVOKE`: Triggers workflow execution
  - `sync-secret`: Synchronizes secrets across platforms
- **Secrets Storage**: GitHub repository secrets for cloud credentials
  - Compute servers: `GH_PAT`, `AWS_AccessKey`, `AWS_SecretKey`, `GCP_SecretKey`, `OW_APIKey`, `SLURM_Token`
  - Data stores: `S3_AccessKey`, `S3_SecretKey`

### Workflow Lifecycle

1. **Design**: User creates workflow JSON using [FaaSr Workflow Builder](https://faasr.io/FaaSr-workflow-builder/)
2. **Upload**: JSON file committed to this repository
3. **Register**: `FAASR REGISTER` action creates/updates functions on cloud platforms
4. **Invoke**: `FAASR INVOKE` action triggers the workflow entry point
5. **Execute**: Platform-specific actions execute sequentially per DAG

### Registration Process

When `FAASR REGISTER` runs:

1. Installs dependencies: `boto3`, `PyGithub`, `FaaSr_py`, OpenWhisk CLI
2. Reads workflow JSON from repository
3. Uses `FaaSr_py` package to validate workflow
4. Creates platform-specific deployments:
   - **GitHub Actions**: Creates `.yml` files (e.g., `tutorial-start.yml`)
   - **AWS Lambda**: Creates Lambda functions from ECR images
   - **Google Cloud Run**: Creates Cloud Run jobs
   - **OpenWhisk**: Creates actions using `wsk` CLI
   - **Slurm**: Configures Slurm jobs
5. Names format: `{WorkflowName}-{ActionName}`

### Invocation Process

When `FAASR INVOKE` runs:

1. Installs `FaaSr_py` and platform CLIs
2. Reads workflow JSON and validates
3. Invokes entry point action with initial payload
4. Entry action executes and triggers successors per DAG

## 2. faasr-backend: FaaSr_py Orchestration Engine

**Purpose:** Python package that coordinates workflow execution within each action

### faasr-backend Key Components

#### Core Modules

- **`engine/`**
  - `faasr_payload.py`: Parses and validates workflow JSON
  - `executor.py`: Executes user functions
  - `scheduler.py`: Invokes successor actions on appropriate platforms

- **`s3_api/`**
  - User-facing API for S3 operations:
    - `get_file()`, `put_file()`, `delete_file()`
    - `faasr_log()`, `get_folder_list()`, `get_s3_creds()`

- **`server/`**
  - `faasr_server.py`: Platform-specific invocation handlers
  - Supports: GitHub Actions, AWS Lambda, GCP, OpenWhisk, Slurm

- **`builtin_functions/`**
  - Special functions: `vm_start`, `vm_stop`, `vm_poll`

- **`vm/`**
  - Virtual machine management for persistent compute resources

- **`config/`**
  - Logging configuration and S3 log handlers

#### Action Execution Flow

When an action executes (using `FaaSr_py`):

1. **Initialization**
   - Parse FaaSr payload from environment/input
   - Retrieve secrets from platform-specific stores (AWS Secrets Manager, GCP Secret Manager, or env vars)
   - Configure logging to S3

2. **Validation**
   - Validate workflow JSON schema
   - Verify compute and data server configurations
   - Check action dependencies

3. **Function Execution**
   - Fetch user function from GitHub repository
   - Install user-specified packages (R/Python)
   - Execute function with action-specific arguments
   - Provide S3 API to function

4. **Orchestration**
   - Determine successor actions from DAG
   - Handle conditional branching (if function returns True/False)
   - Handle ranked actions (parallel instances)
   - Invoke successors on their designated platforms

5. **Logging**
   - Stream logs to S3 bucket
   - Store structured execution metadata

### Package Distribution

- Published as `FaaSr_py` on PyPI
- Version specified in `setup.py` (e.g., `0.1.13`)
- Installed in Docker images and by GitHub Actions

## 3. faasr-docker: Container Image Repository

**Purpose:** Build and publish Docker containers for all supported platforms

### Architecture: Two-Tier Build System

#### Tier 1: Base Images

Platform-agnostic images with R/Python environments:

- **`base/base.Dockerfile`**: Pure Python base
  - Source: `python:3.13`
  - Installs: Python packages from `requirements.txt`

- **`base/base-rocker.Dockerfile`**: R + Python base (preferred for R)
  - Source: `rocker/tidyverse:4.4`
  - Installs: R packages from `R_packages.R` + Python

- **`base/base-r.Dockerfile`**: Debian R + Python (deprecated)

**Base images install:**

- Core Python packages: `boto3`, `requests`, etc.
- FaaSr_py package (specific version/tag from GitHub)
- System dependencies from `apt-packages.txt`

#### Tier 2: Platform-Specific Images

Built from base images, add platform entry points:

- **`faas_specific/github-actions.Dockerfile`** → GHCR
  - Entry: GitHub Actions event handler
  - Secrets: From environment variables

- **`faas_specific/openwhisk.Dockerfile`** → DockerHub
  - Entry: OpenWhisk HTTP handler
  - Secrets: From environment variables

- **`faas_specific/aws-lambda.Dockerfile`** → Amazon ECR
  - Entry: AWS Lambda handler
  - Secrets: From AWS Secrets Manager

- **`faas_specific/gcp.Dockerfile`** → DockerHub
  - Entry: Google Cloud Run HTTP handler
  - Secrets: From GCP Secret Manager

- **`faas_specific/slurm.Dockerfile`** → DockerHub
  - Entry: Slurm job handler
  - Secrets: From environment variables

### Common Entry Point: `faasr_entry.py`

All platform images use `faasr_entry.py` as the execution entry point:

1. **Platform Detection**: Reads `FAASR_PLATFORM` environment variable
2. **Secret Retrieval**: Platform-specific logic to fetch credentials
3. **Payload Processing**: Parses workflow JSON and current action info
4. **Execution**: Calls `FaaSr_py.Executor` to run the action
5. **Scheduling**: Calls `FaaSr_py.Scheduler` to invoke successors

### Build Process (via GitHub Actions)

1. **Base Image Build**:
   - Triggered manually from `faasr-docker/.github/workflows/`
   - Inputs: Base image tag (e.g., `python:3.13`), FaaSr version
   - Installs FaaSr_py from specified GitHub release/tag
   - Publishes to DockerHub: `faasr/base-python:2.1.0`

2. **Platform Image Build**:
   - Builds from base image
   - Inputs: Base image name, FaaSr-py version, registry
   - Copies `faasr_entry.py` into image
   - Publishes to platform-specific registries:
     - GitHub Actions: `ghcr.io/faasr/github-actions-python:2.1.0`
     - AWS Lambda: `{account}.dkr.ecr.{region}.amazonaws.com/aws-lambda-python:2.1.0`
     - Others: `faasr/{platform}-python:2.1.0`

### Container Usage Flow

```plaintext
User Workflow JSON
      ↓
Specifies container image per action
      ↓
FAASR REGISTER reads image name
      ↓
Platform pulls image from registry
      ↓
Container starts with faasr_entry.py
      ↓
faasr_entry.py uses FaaSr_py
      ↓
Action executes
```

## Cross-Repository Integration Points

### 1. Version Coordination

**Critical:** All three repos must use compatible versions

```yaml
faasr-docker (builds):
  base-python:2.1.0
    └── FROM python:3.13
    └── pip install FaaSr_py @ faasr/FaaSr-Backend@v2.1.0

faasr-workflow (registers):
  register-workflow.yml
    └── pip install FaaSr_py==2.1.0

faasr-backend (publishes):
  setup.py: version="2.1.0"
```

**Version Update Process:**

1. Update `faasr-backend/setup.py` version
2. Tag release in `faasr-backend`
3. Rebuild base images in `faasr-docker` pointing to new tag
4. Rebuild platform images from new base images
5. Update `faasr-workflow` GitHub Actions to install new version
6. Update default image references in workflow JSON schemas

### 2. Payload Format (JSON Schema)

All repos depend on consistent workflow JSON structure:

```json
{
  "FunctionList": {
    "action-name": {
      "FunctionName": "my_function",
      "Language": "Python",
      "FaaSServer": "GH",
      "Actioncontainer": "ghcr.io/faasr/github-actions-python:2.1.0",
      "Arguments": {}
    }
  },
  "ComputeServers": {
    "GH": {"Endpoint": "https://github.com/..."}
  },
  "DataStores": {
    "S3": {"Bucket": "my-bucket", ...}
  },
  "FunctionInvoke": "entry-action",
  "InvocationID": "uuid"
}
```

**Shared by:**

- `faasr-workflow`: Stores and passes to registration/invocation
- `faasr-backend`: Validates with `FaaSrPayload` class
- `faasr-docker`: `faasr_entry.py` parses and uses

### 3. S3 API Contract

User functions call standardized S3 API from `faasr-backend`:

```python
# User function code (hosted in separate GitHub repo)
from FaaSr_py import faasr_get_file, faasr_put_file, faasr_log

def my_function(args):
    # Get input from S3
    faasr_get_file("input.csv", "input.csv")
    
    # Process data
    result = process(...)
    
    # Put output to S3
    faasr_put_file("output.csv", "output.csv")
    
    # Log to S3
    faasr_log("Processing complete")
    
    return True
```

**Provided by:** `faasr-backend/FaaSr_py/s3_api/`
**Available in:** All `faasr-docker` containers via installed `FaaSr_py`

### 4. Secret Management

Secrets flow from workflow repo to containers:

```plaintext
faasr-workflow (GitHub Secrets)
      ↓ (env vars during register/invoke)
Cloud Platform Secret Stores
      ↓ (platform-specific APIs)
faasr-docker containers
      ↓ (faasr_entry.py retrieval)
faasr-backend FaaSr_py
      ↓ (available to user functions)
User function code
```

**Secret Retrieval in `faasr_entry.py`:**

- **GitHub/Slurm/OpenWhisk**: `os.getenv(key)`
- **AWS Lambda**: `boto3.client('secretsmanager').get_secret_value()`
- **GCP**: `secretmanager.SecretManagerServiceClient().access_secret_version()`

## Making Changes Across Repositories

### Scenario 1: Adding a New S3 API Function

1. **faasr-backend**: Implement new function in `s3_api/`
2. **faasr-backend**: Add to `__init__.py` exports
3. **faasr-backend**: Update version, create release
4. **faasr-docker**: Rebuild base images with new backend version
5. **faasr-docker**: Rebuild all platform images
6. **faasr-workflow**: Update `pip install FaaSr_py==X.Y.Z` in actions
7. **Documentation**: Update API docs with new function

### Scenario 2: Supporting a New Cloud Platform

1. **faasr-backend**: Add platform handler to `server/faasr_server.py`
2. **faasr-backend**: Add secret retrieval logic
3. **faasr-backend**: Update `Scheduler` to invoke on new platform
4. **faasr-docker**: Create new `{platform}.Dockerfile`
5. **faasr-docker**: Add GitHub Action to build and publish
6. **faasr-docker**: Update `faasr_entry.py` platform detection
7. **faasr-workflow**: Add `{PLATFORM}_Credentials` secrets
8. **faasr-workflow**: Update `register-workflow.yml` and `invoke-workflow.yml`
9. **faasr-workflow**: Add registration/invocation scripts for platform

### Scenario 3: Changing Workflow JSON Schema

1. **faasr-backend**: Update `FaaSrPayload` validation logic
2. **faasr-backend**: Update `Executor` and `Scheduler` if needed
3. **faasr-backend**: Version bump and release
4. **faasr-docker**: Rebuild containers (if entry point logic changes)
5. **faasr-workflow**: Update example JSON files
6. **Documentation**: Update workflow builder and schema docs
7. **Workflow Builder UI**: Update to generate new schema format

### Scenario 4: Adding Dependencies to Containers

1. **faasr-docker**: Update `base/requirements.txt` (Python) or `base/R_packages.R` (R)
2. **faasr-docker**: Rebuild base images
3. **faasr-docker**: Rebuild all platform images from new base
4. **Documentation**: Document new available packages

## Testing Changes

### Local Testing

```bash
# Test backend changes
cd faasr-backend
pip install -e .
python -m pytest

# Test container locally
cd faasr-docker
docker build -f base/base.Dockerfile -t test-base .
docker build -f faas_specific/github-actions.Dockerfile --build-arg BASE_IMAGE=test-base -t test-gh .
docker run -e FAASR_PLATFORM=github test-gh

# Test workflow registration (requires secrets)
cd faasr-workflow
python scripts/register_workflow.py --workflow-file tutorial.json
```

### Integration Testing

1. Fork `faasr-workflow` repository
2. Add test workflow JSON
3. Build custom containers pointing to development backend branches
4. Register and invoke test workflows
5. Verify logs in S3

## Dependency Graph

```plaintext
User Workflow JSON File
      ↓
┌─────────────────────┐
│  faasr-workflow     │
│  (GitHub Actions)   │
└──────┬──────────────┘
       │ installs FaaSr_py
       │ reads workflow JSON
       │ invokes cloud platforms
       ↓
┌─────────────────────┐
│  Cloud Platforms    │ pulls containers
│  (GH/AWS/GCP/etc)   ├──────────────┐
└──────┬──────────────┘              │
       │ runs container              │
       ↓                             ↓
┌─────────────────────┐    ┌─────────────────────┐
│  faasr-docker       │    │  faasr-backend      │
│  (Container Image)  │    │  (FaaSr_py Package) │
│  • faasr_entry.py   │    │  • Executor         │
│  • FaaSr_py (installed)  │  • Scheduler        │
└──────┬──────────────┘    │  • S3 API           │
       │                   └──────────────────────┘
       │ imports FaaSr_py
       │ calls Executor/Scheduler
       ↓
User Function Execution
       ↓
Successor Actions Invoked
```

## Key Takeaways for Developers

1. **Backend Changes = Container Rebuilds**: Any change to `faasr-backend` requires rebuilding all Docker images

2. **Version Synchronization**: Always keep versions aligned:
   - Backend package version
   - Docker build arguments
   - Workflow GitHub Actions `pip install` statements

3. **JSON Schema is Contract**: Changes to workflow JSON affect all three repos

4. **Platform-Specific Logic**:
   - Registration: `faasr-workflow/scripts/register_workflow.py`
   - Secret retrieval: `faasr-docker/faas_specific/faasr_entry.py`
   - Invocation: `faasr-backend/FaaSr_py/server/faasr_server.py`

5. **Entry Point is Critical**: `faasr_entry.py` is the bridge between containers and backend logic

6. **S3 is Persistent Storage**: All data between actions must flow through S3

7. **Secrets Flow Unidirectionally**: From workflow repo → cloud platforms → containers

## Additional Resources

- **FaaSr Documentation**: <https://faasr.io>
- **Workflow Builder**: <https://faasr.io/FaaSr-workflow-builder/>
- **Main GitHub Organization**: <https://github.com/FaaSr>
- **Tutorial**: See `faasr-docs/docs/tutorial.md`
- **Example Workflows**: See `faasr-workflow/*.json`

## License

All FaaSr repositories follow the MIT open-source license.

## Support

For questions and issues:

- GitHub Issues on respective repositories
- Documentation: <https://faasr.io>
- Research funded by NSF grants OAC-2450241 and OAC-2311124
