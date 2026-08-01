# TechVault Live Build

This directory contains the pack-local realization of the APTL-derived
TechVault ACES scenario. The scenario authority remains
`../sdl/techvault.sdl.yaml`; the build is a Docker Compose provider binding
over those ACES resources.

## Runtime Profile

- Profile id: `operational`
- Provider: Docker Compose
- Participant entry surface: ACES `kali`, reachable through the loopback-only
  `kali-ssh-proxy`
- Source snapshot: APTL commit
  `43f137450268f25615c07b9a24144540dfac3c34` under `aptl-runtime/`

## Usage

```sh
cd scenarios/techvault
./build/launch.sh
./build/health-check.sh
./build/reset.sh
./build/cleanup.sh
```

The default credential file is `build/operator-defaults.env`. It contains
synthetic range credentials committed as scenario content. Operators can point
`TECHVAULT_OPERATOR_ENV` at another pack-local env file when they need different
lab values; the build refuses env files outside the pack or symlinked env
files, and it never requires the repository root `.env`. `TECHVAULT_COMPOSE_PROJECT`
is also validated before any wrapper touches Docker state. The default
`APTL_DNS_HOST_PORT=55353` keeps the host publish off UDP 5353 so desktop mDNS
listeners do not block the range; in-world DNS still listens on container port
53.

Generated certificates, SSH keys, Wazuh rendered config, Compose volumes, run
archives, and operator receipts stay under gitignored build paths. They are
runtime state, not pack source.

## Validation

```sh
python3 build/validate_build.py validate
python3 -m unittest discover -s build/tests
( cd build/aptl-runtime/web && npm ci && npm test )
```

## Automated Live Rehearsal

The automated rehearsal is packaged as `build/rehearsal.py`. It launches the
same `operational` profile through the build wrappers, enters through the
loopback `kali-ssh-proxy`, runs a participant-equivalent representative path,
collects value-sparse telemetry evidence, resets the range, proves stale
participant state is gone, and verifies cleanup residuals.

Run it only on a disposable isolated Docker host:

```sh
python3 build/rehearsal.py run --isolated-docker-host
```

Without `--isolated-docker-host`, the harness writes a blocked report and exits
before Docker is touched. Successful live runs update
`../docs/rehearsal-report-392.md`; raw runtime evidence stays under the ignored
`aptl-runtime/runs/` store.

## Manual Participant Walkthrough

The reusable human procedure is
[`../docs/walkthroughs/manual-participant-walkthrough.md`](../docs/walkthroughs/manual-participant-walkthrough.md).
It keeps lifecycle/observer work separate from commands issued as `kali`
through `kali-ssh-proxy`. The completed #393 evidence is
[`../docs/manual-participant-walkthrough-report-393.md`](../docs/manual-participant-walkthrough-report-393.md).

## Proof Boundary

The `operational` profile is the golden reference build. #392 records a passing
automated isolated-host rehearsal. #393 records the final command-by-command
Kali participant journey, red/blue comparison, reset/freshness proof,
post-manual automated pass, and independently verified Docker/AWS teardown.
Generated state and raw evidence remain uncommitted.
