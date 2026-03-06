#!/usr/bin/env bash
# Source this file to route AWS CLI and GCP SDK to the local Vera emulators.
#
#   source ./vera-env.sh
#
# After sourcing, standard CLI commands work without extra flags:
#   aws ec2 create-vpc --cidr-block 10.0.0.0/16
#   gcloud compute instances list --project=vera-project

export AWS_ENDPOINT_URL="${AWS_ENDPOINT_URL:-http://localhost:5003}"
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

export CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE="${CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE:-http://localhost:9100/}"
export CLOUDSDK_CORE_PROJECT="${CLOUDSDK_CORE_PROJECT:-vera-project}"
export CLOUDSDK_AUTH_DISABLE_CREDENTIALS=true

printf "Vera environment active\n"
printf "  AWS CLI  → %s\n" "$AWS_ENDPOINT_URL"
printf "  GCP SDK  → %s\n" "$CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE"
