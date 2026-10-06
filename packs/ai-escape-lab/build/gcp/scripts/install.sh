#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
ROOT=/opt/ai-escape-lab
SOURCE_SHA256=138c611ec9520d99723389133e4e989ef5b2c536cae0ccb41f8f0e422c4a16a2
MONGO_IMAGE=mongo@sha256:494b956596706b19ba44908cb9d03648b585214600987b86cd2a34249358e572
LOCAL_MONGO=ai-escape-lab/internal-db:fcb25ec9874b

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl docker.io docker-compose-v2 iptables jq openssh-server python3 sudo
systemctl enable --now docker ssh

install -d -m 0755 "$ROOT" "$ROOT/source" /usr/local/lib/ai-escape-lab
python3 /tmp/ai-escape-scripts/prepare-source.py \
  --archive /tmp/upstream-ai-escape-room.tar.gz \
  --destination "$ROOT/source" \
  --sha256 "$SOURCE_SHA256"
install -m 0644 /tmp/ai-escape-runtime/participant-briefing.md \
  "$ROOT/source/eval-sandbox/briefing.md"

python3 - <<'PY'
import base64
import hashlib
import io
import json
import os
import tarfile
import urllib.request
from pathlib import Path

lock = json.loads(Path("/tmp/claude-code.lock.json").read_text(encoding="utf-8"))
with urllib.request.urlopen(lock["url"], timeout=120) as response:
    body = response.read()
observed = base64.b64encode(hashlib.sha512(body).digest()).decode()
if observed != lock["integrity_sha512_base64"]:
    raise SystemExit("Claude Code package integrity mismatch")
with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as archive:
    member = archive.getmember("package/claude")
    if not member.isfile():
        raise SystemExit("Claude Code package has no regular binary")
    source = archive.extractfile(member)
    if source is None:
        raise SystemExit("Claude Code binary extraction failed")
    binary = source.read()
destination = Path("/opt/ai-escape-lab/source/eval-sandbox/claude")
destination.write_bytes(binary)
os.chmod(destination, 0o755)
PY

docker compose --file "$ROOT/source/docker-compose.yml" \
  --file /tmp/build-images.override.yml build --pull
rm -f "$ROOT/source/eval-sandbox/claude"
docker pull "$MONGO_IMAGE"
docker tag "$MONGO_IMAGE" "$LOCAL_MONGO"

cp /tmp/ai-escape-runtime/docker-compose.yml "$ROOT/docker-compose.yml"
cp /tmp/ai-escape-runtime/readiness.json "$ROOT/readiness.json"
for script in start-lab.sh stop-lab.sh readiness.sh probe-agent.sh; do
  install -m 0755 "/tmp/ai-escape-runtime/$script" "$ROOT/$script"
done
install -m 0755 /tmp/ai-escape-runtime/participant-shell.sh /usr/local/sbin/ai-escape-shell
install -m 0755 /tmp/ai-escape-runtime/ai-escape-enter /usr/local/sbin/ai-escape-enter
install -m 0755 /tmp/ai-escape-scripts/metadata-token-responder.py \
  /usr/local/lib/ai-escape-lab/metadata-token-responder.py
install -m 0755 /tmp/ai-escape-scripts/firewall.sh /usr/local/sbin/ai-escape-firewall

cat > /etc/systemd/system/ai-escape-model-metadata.service <<'EOF'
[Unit]
Description=AI Escape Lab scoped GCE metadata responder
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/lib/ai-escape-lab/metadata-token-responder.py 0.0.0.0 988
Restart=on-failure
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/ai-escape-firewall.service <<'EOF'
[Unit]
Description=AI Escape Lab model-egress firewall
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ai-escape-firewall
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF

install -d -m 0755 /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/90-ai-escape-firewall.conf <<'EOF'
[Service]
ExecStartPost=/usr/local/sbin/ai-escape-firewall
EOF

cat > /etc/systemd/system/ai-escape-lab.service <<'EOF'
[Unit]
Description=AI Escape Lab container range
After=docker.service ai-escape-model-metadata.service ai-escape-firewall.service network-online.target
Requires=docker.service ai-escape-model-metadata.service ai-escape-firewall.service

[Service]
Type=oneshot
ExecStart=/opt/ai-escape-lab/start-lab.sh
ExecStop=/opt/ai-escape-lab/stop-lab.sh
RemainAfterExit=true
TimeoutStartSec=300
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/ssh/sshd_config.d/60-ai-escape-lab.conf <<'EOF'
Match User participant
    ForceCommand /usr/local/sbin/ai-escape-shell
    PermitTTY yes
    AllowTcpForwarding no
    X11Forwarding no
    PermitTunnel no
    GatewayPorts no
EOF
cat > /etc/sudoers.d/ai-escape-lab <<'EOF'
participant ALL=(root) NOPASSWD: /usr/local/sbin/ai-escape-enter *
EOF
chmod 0440 /etc/sudoers.d/ai-escape-lab
visudo --check --file=/etc/sudoers.d/ai-escape-lab
sshd -t

python3 - <<'PY'
import json
import subprocess
from pathlib import Path

names = [
    "eval-sandbox", "registry-cache", "cybergym", "request-capture", "pastebin",
    "hf-api", "dataset-worker", "k8s-api", "internal-db", "mesh-gateway", "source-control",
]
images = {}
for name in names:
    ref = f"ai-escape-lab/{name}:fcb25ec9874b"
    image_id = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", ref], text=True).strip()
    images[name] = {"reference": ref, "image_id": image_id}
manifest = {
    "schema_version": "ai-escape-lab-image-manifest/v1",
    "upstream_revision": "fcb25ec9874b0676706b9aca650f22efc90f711e",
    "claude_code": json.loads(Path("/tmp/claude-code.lock.json").read_text(encoding="utf-8")),
    "images": images,
}
Path("/opt/ai-escape-lab/image-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
PY

systemctl daemon-reload
systemctl enable ai-escape-model-metadata.service ai-escape-firewall.service ai-escape-lab.service
systemctl start ai-escape-model-metadata.service
systemctl restart docker
"$ROOT/start-lab.sh" --bake
"$ROOT/stop-lab.sh"
systemctl stop ai-escape-model-metadata.service
rm -rf /run/ai-escape-lab /tmp/ai-escape-runtime /tmp/ai-escape-scripts \
  /tmp/build-images.override.yml /tmp/claude-code.lock.json \
  /tmp/upstream-ai-escape-room.tar.gz
apt-get clean
rm -rf /var/lib/apt/lists/* /var/tmp/*
