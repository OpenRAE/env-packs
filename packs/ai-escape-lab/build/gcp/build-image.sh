#!/bin/bash
set -euo pipefail

usage() {
  echo "usage: build-image.sh PROJECT ZONE NETWORK SUBNETWORK SOURCE_IMAGE IMAGE_VERSION [SERVICE_ACCOUNT]" >&2
  exit 2
}

[[ $# -ge 6 && $# -le 7 ]] || usage
project=$1
zone=$2
network=$3
subnetwork=$4
source_image=$5
image_version=$6
service_account=${7:-}

for value in "$project" "$zone" "$network" "$subnetwork" "$source_image" "$image_version"; do
  [[ -n "$value" && "$value" != *$'\n'* ]] || usage
done

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
packer init "$here/ai-escape-lab.pkr.hcl"
packer validate \
  -var "project_id=$project" \
  -var "zone=$zone" \
  -var "network=$network" \
  -var "subnetwork=$subnetwork" \
  -var "source_image=$source_image" \
  -var "image_version=$image_version" \
  -var "service_account_email=$service_account" \
  "$here/ai-escape-lab.pkr.hcl"
packer build \
  -var "project_id=$project" \
  -var "zone=$zone" \
  -var "network=$network" \
  -var "subnetwork=$subnetwork" \
  -var "source_image=$source_image" \
  -var "image_version=$image_version" \
  -var "service_account_email=$service_account" \
  "$here/ai-escape-lab.pkr.hcl"
