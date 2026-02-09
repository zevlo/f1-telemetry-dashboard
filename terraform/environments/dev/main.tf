# Dev Environment
# Calls root modules with dev-specific values

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "f1-telemetry"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

# Module calls will be added here as each module is built
# module "ingestion" {
#   source = "../../modules/ingestion"
#   ...
# }
