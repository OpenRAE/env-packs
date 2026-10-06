packer {
  required_version = ">= 1.10.0"
  required_plugins {
    googlecompute = {
      version = ">= 1.1.6, < 2.0.0"
      source  = "github.com/hashicorp/googlecompute"
    }
  }
}

variable "project_id" {
  type = string
}

variable "zone" {
  type = string
}

variable "network" {
  type = string
}

variable "subnetwork" {
  type = string
}

variable "source_image" {
  type        = string
  description = "Exact Ubuntu 24.04 GCE source-image self link; image families are not accepted."
  validation {
    condition     = can(regex("^projects/[^/]+/global/images/[^/]+$", var.source_image))
    error_message = "source_image must be an exact projects/.../global/images/... reference"
  }
}

variable "service_account_email" {
  type    = string
  default = ""
}

variable "image_version" {
  type        = string
  description = "Immutable build version such as 20261006-1."
  validation {
    condition     = can(regex("^[0-9]{8}-[1-9][0-9]*$", var.image_version))
    error_message = "image_version must match YYYYMMDD-N"
  }
}

variable "machine_type" {
  type    = string
  default = "e2-standard-8"
}

source "googlecompute" "ai_escape_lab" {
  project_id              = var.project_id
  zone                    = var.zone
  source_image            = var.source_image
  network                 = var.network
  subnetwork              = var.subnetwork
  use_internal_ip         = true
  omit_external_ip        = true
  use_iap                 = true
  iap_tunnel_launch_wait  = 300
  ssh_username            = "packer"
  service_account_email   = var.service_account_email
  scopes                  = ["https://www.googleapis.com/auth/userinfo.email"]
  machine_type            = var.machine_type
  disk_size               = 50
  disk_type               = "pd-balanced"
  image_name              = "shifter-ai-escape-lab-v${var.image_version}"
  image_family            = "shifter-ai-escape-lab"
  image_storage_locations = ["us"]
  image_labels = {
    scenario        = "ai-escape-lab"
    source-revision = "fcb25ec9874b"
  }
}

build {
  sources = ["source.googlecompute.ai_escape_lab"]

  provisioner "shell" {
    inline = [
      "mkdir -p /tmp/ai-escape-runtime /tmp/ai-escape-scripts",
    ]
  }

  provisioner "file" {
    source      = "${path.root}/../../assets/upstream-ai-escape-room-fcb25ec9874b.tar.gz"
    destination = "/tmp/upstream-ai-escape-room.tar.gz"
  }

  provisioner "file" {
    source      = "${path.root}/../runtime/"
    destination = "/tmp/ai-escape-runtime"
  }

  provisioner "file" {
    source      = "${path.root}/scripts/"
    destination = "/tmp/ai-escape-scripts"
  }

  provisioner "file" {
    source      = "${path.root}/build-images.override.yml"
    destination = "/tmp/build-images.override.yml"
  }

  provisioner "file" {
    source      = "${path.root}/claude-code.lock.json"
    destination = "/tmp/claude-code.lock.json"
  }

  provisioner "shell" {
    script          = "${path.root}/scripts/install.sh"
    execute_command = "sudo -E bash '{{.Path}}'"
  }
}
