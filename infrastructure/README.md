
# ReadRecall Infrastructure as Code

This directory contains the AWS CDK (Cloud Development Kit) code that defines the infrastructure for the ReadRecall application. The infrastructure is managed as code using AWS CDK v2 with Python.

## Architecture Overview

The ReadRecall backend consists of the following components:

- Lambda functions for handling various tasks (normalizing books, generating summaries, etc.)
- S3 buckets for storing books and processed data
- SQS queues for handling asynchronous processing
- IAM roles and policies for security

## Important Guardrails

This repository is set up with guardrails to enforce the following workflow:

1. **Code-only changes** can be deployed directly by developers with limited permissions
2. **Infrastructure changes** must go through a PR review process


## Development Setup

### Prerequisites

- AWS CDK v2 CLI: `npm i -g aws-cdk`
- Python 3.9+
- AWS CLI configured with appropriate credentials

### Getting Started

1. Set up your virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

2. Synthesize the CloudFormation template to validate your changes:

   ```bash
   cdk synth
   ```

### Developer Workflow

#### For Code-only Changes (Lambda Functions)

If you're only changing Lambda function code (not infrastructure):

1. Make your code changes in the appropriate Lambda directory
2. Test locally if possible
3. Deploy using hot-swap for fast development:
   ```bash
   cdk deploy --hotswap
   ```
   This bypasses CloudFormation and directly updates the Lambda code.

#### For Infrastructure Changes

1. Create a feature branch: `git checkout -b feature/new-infra-component`
2. Make your infrastructure changes in the CDK code
3. Validate with `cdk diff` to see what will change
4. Submit a PR for review
5. GitHub Actions will run the CDK diff and post the results to your PR
6. After approval and merge, the changes will be automatically deployed

NOTE: The CI/CD pipeline enforces that infrastructure changes cannot be deployed directly, only through the PR process.

## IAM Roles

Two IAM roles have been created to enforce the separation of concerns:

1. **ReadRecallInfraCI** - Used by the CI/CD pipeline for infrastructure deployments
2. **ReadRecallDevLimited** - Used by developers for code-only updates
   - Has a permission boundary that prevents infrastructure changes
   - Can only update Lambda function code, view logs, etc.

## Useful Commands

* `cdk ls` - List all stacks in the app
* `cdk synth` - Emit the synthesized CloudFormation template
* `cdk diff` - Compare deployed stack with current state
* `cdk deploy ReadRecallStack` - Deploy the infrastructure stack
* `cdk deploy IamRolesStack` - Deploy the IAM roles stack
* `cdk deploy --hotswap` - Fast deploy for Lambda code updates (bypasses CloudFormation)
* `cdk watch` - Auto-deploy changes on save (useful during development)

## Importing New Resources

If you need to add existing AWS resources to CDK management:

```bash
cdk import ReadRecallStack --resource-type AWS::ResourceType --identifier name=resource-name
```
