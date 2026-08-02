#!/bin/bash
# Per-boot CTF flag generator for the image-free generic nodes (#581 parity).
#
# The v5.0.0 base image generated CTF flags at container start (base entrypoint
# generate_flags), and the still-image AD node still does. The generic nodes
# (victim, workstation, webapp, fileshare) carry no baked entrypoint, so a
# oneshot systemd unit runs this at boot to reproduce it exactly: a fresh
# per-boot nonce and an HMAC-SHA-256 authenticated aptl:v2 token that the
# scoring collector verifies. One script serves every node; the per-node
# oneshot unit supplies the generated key file, node name, and user placement.
set -eu

if [ -z "${APTL_FLAG_KEY_FILE:-}" ]; then
  echo "APTL_FLAG_KEY_FILE required" >&2
  exit 78
fi
KEY_FILE="$APTL_FLAG_KEY_FILE"
NODE="${APTL_FLAG_NODE:?APTL_FLAG_NODE required}"
USER_PATH="${APTL_FLAG_USER_PATH:?APTL_FLAG_USER_PATH required}"
USER_OWNER="${APTL_FLAG_USER_OWNER:?APTL_FLAG_USER_OWNER required}"

if [ ! -r "$KEY_FILE" ]; then
  echo "flag signing key unavailable" >&2
  exit 78
fi
KEY=$(cat "$KEY_FILE")
if [ -z "$KEY" ]; then
  echo "flag signing key is empty" >&2
  exit 78
fi

for level in user root; do
  nonce=$(od -A n -t x1 -N 16 /dev/urandom | tr -d ' \n')
  flag="APTL{${level}_${NODE}_${nonce}}"
  sig=$(printf '%s' "${NODE}:${level}:${nonce}" | openssl dgst -sha256 -hmac "$KEY" | awk '{print $NF}')
  token="aptl:v2:${NODE}:${level}:${nonce}:${sig}"

  if [ "$level" = user ]; then
    dest="$USER_PATH"
  else
    dest="${APTL_FLAG_ROOT_PATH:-/root/root.txt}"
  fi

  mkdir -p "$(dirname "$dest")"
  cat > "$dest" <<EOF
===== APTL CTF Flag =====
Flag:  ${flag}
Token: ${token}
==========================
EOF

  if [ "$level" = user ]; then
    chown "$USER_OWNER" "$dest"
    chmod 644 "$dest"
  else
    chown root:root "$dest"
    chmod 600 "$dest"
  fi
done

echo "CTF flags generated for ${NODE}"
