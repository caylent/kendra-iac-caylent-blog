# AWS Kendra Infrastructure as Code

This repository contains Terraform configurations for deploying and managing AWS Kendra infrastructure with custom connectors and EventBridge integration.

## Prerequisites

- Terraform >= 1.11.0
- AWS CLI configured with appropriate credentials
- AWS account with permissions to create Kendra resources

## Project Structure

```
.
├── custom_connector/        # Custom connector Lambda function code
├── custom_connector.tf      # Custom connector infrastructure
├── eventbridge.tf           # EventBridge rules and targets
├── kendra.tf                # Main Kendra index and configurations
├── locals.tf                # Local variables
├── parameter_store.tf       # SSM Parameter Store configurations
├── provider.tf              # AWS provider configuration
├── secrets.tf               # Secrets management
├── terraform.tf             # Terraform backend configuration
├── variables.tf             # Input variables
└── terraform.tfvars         # Variable values (included in .gitignore)
```

## Usage

1. Clone this repository
2. Update `terraform.tfvars` with your desired configuration
3. Initialize Terraform:
   ```bash
   terraform init
   ```
4. Review the planned changes:
   ```bash
   terraform plan
   ```
5. Apply the configuration:
   ```bash
   terraform apply
   ```

## Configuration

The main configuration parameters can be adjusted in `terraform.tfvars`. See `variables.tf` for all available options and their descriptions.

## Security

- Sensitive information is stored in AWS Secrets Manager
- IAM roles follow the principle of least privilege
- All resources are tagged for proper resource management
- Sensitive variables are masked in .tfstate
