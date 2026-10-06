#!/bin/bash
set -euo pipefail

MODEL_SUBNET=172.34.0.0/24
GOOGLE_PRIVATE=199.36.153.8/30
RESPONDER_PORT=988
LAB_SUBNETS=(172.29.0.0/16 172.30.0.0/16 172.31.0.0/16 172.32.0.0/16 172.33.0.0/16 172.34.0.0/24)

rule() {
  local table=$1 chain=$2
  shift 2
  if ! iptables --table "$table" --check "$chain" "$@" 2>/dev/null; then
    iptables --table "$table" --insert "$chain" 1 "$@"
  fi
}

for _ in {1..30}; do
  iptables --check DOCKER-USER -j RETURN >/dev/null 2>&1 && break
  sleep 1
done
iptables --check DOCKER-USER -j RETURN >/dev/null 2>&1

if ! iptables --check DOCKER-USER -s "$MODEL_SUBNET" -j DROP 2>/dev/null; then
  iptables --insert DOCKER-USER 1 -s "$MODEL_SUBNET" -j DROP
fi
rule filter DOCKER-USER -s "$MODEL_SUBNET" -d "$GOOGLE_PRIVATE" -p tcp --dport 443 -j RETURN
rule filter DOCKER-USER -d 169.254.169.254/32 -j DROP

for subnet in "${LAB_SUBNETS[@]}"; do
  if ! iptables --check INPUT -s "$subnet" -j REJECT 2>/dev/null; then
    iptables --insert INPUT 1 -s "$subnet" -j REJECT
  fi
done
rule filter INPUT -s "$MODEL_SUBNET" -p tcp --dport "$RESPONDER_PORT" -j ACCEPT
