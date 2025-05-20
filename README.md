# ReadRecall Backend

This repository contains the backend code for the ReadRecall application, which processes and analyzes books to generate summaries and character analyses. The project has been migrated from AWS SAM to AWS CDK for infrastructure management.

## Architecture

The ReadRecall backend uses a serverless architecture on AWS with the following components:

## Infrastructure as Code

The AWS infrastructure is now managed using AWS CDK (Cloud Development Kit) with Python. We've migrated from AWS SAM to AWS CDK to gain the following benefits:

- Infrastructure changes are versioned in Git
- Changes can be reviewed through Pull Requests
- Consistent deployments across environments
- Clear separation between code and infrastructure changes
- Enhanced developer experience with hot-swap deployments

### Developer Workflow

#### For Code-Only Changes (e.g., Lambda Function Logic)

Developer workflow for updating Lambda code only:

1. Make changes to Lambda function code in the `lambdas/` directory
2. Test your changes locally if possible
3. Deploy using the hot-swap approach (bypasses CloudFormation for speed):
   ```bash
   cd infrastructure
   source .venv/bin/activate
   ./update_lambda.py <function-name>  # or: cdk deploy --hotswap
   ```

#### For Infrastructure Changes

Changes to infrastructure (new resources, permissions, etc.) follow a more controlled process:

1. Create a feature branch: `git checkout -b feature/my-new-resource`
2. Make changes to the CDK code in the `infrastructure/` directory
3. Test with `cdk diff` to see what will change
4. Submit a PR for review
5. GitHub Actions will validate the changes
6. After approval and merge, changes are automatically deployed

## Security Guardrails

The repository implements security guardrails to enforce the separation between code and infrastructure changes:

- **ReadRecallDevLimited** IAM role for developers - can only update Lambda code, not infrastructure
- **ReadRecallInfraCI** IAM role for CI/CD - has permissions to deploy infrastructure changes
- GitHub Actions workflow enforces that infrastructure changes must go through PR review

## Getting Started

### Prerequisites

- AWS CDK v2 CLI: `npm i -g aws-cdk`
- Python 3.9+
- AWS CLI configured with appropriate credentials
- Node.js (for CDK)

### Setup

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd read-recall-backend
   ```

2. Set up the CDK infrastructure:
   ```bash
   cd infrastructure
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Explore the codebase:
   - `infrastructure/` - CDK infrastructure code
     - `infrastructure_stack.py` - Main infrastructure stack that imports existing resources
     - `iam_roles_stack.py` - IAM roles and policies for security guardrails
   - `lambdas/` - Lambda function code for various services
   - `.github/workflows/` - CI/CD pipeline definitions with PR-based infrastructure changes

## CI/CD Pipeline

The repository uses GitHub Actions for continuous integration and deployment:

1. **Pull Requests**: The workflow runs `cdk diff --fail --strict` to detect infrastructure changes
2. **Merged to Main**: Automatically deploys the changes using `cdk deploy`

See `.github/workflows/deploy.yml` for the full workflow definition.

## Additional Resources

- [CDK Documentation](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.html)
- For more detailed infrastructure documentation, see [infrastructure/README.md](infrastructure/README.md)

## Migration Notes

This project was recently migrated from AWS SAM to AWS CDK. The migration process involved:

1. Creating CDK stacks to import existing resources
2. Setting up IAM roles to enforce code vs. infrastructure separation
3. Configuring GitHub Actions for PR-based infrastructure changes
4. Removing SAM-specific files and configurations

The Lambda functions and core business logic remain unchanged, but they're now managed through CDK rather than SAM.
