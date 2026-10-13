# TechVault integration endpoint ownership and verification

Issue [#294](https://github.com/OpenRAE/env-packs/issues/294) describes a retired
post-admission proxy. Its August dependency pause no longer describes the
current implementation. This record classifies the removed behavior, reconciles
the replacement contracts, and distinguishes delivered regression coverage
from the live evidence still required for closure.

## Architectural evidence

The inspection uses env-packs integration revision `dd8d5c2`, LilRAE revision
[`5bef477`](https://github.com/OpenRAE/lilrae/tree/5bef477de828dc77c0df1dc9592487809e52df14),
and RAES revision
[`3512210`](https://github.com/OpenRAE/rae/tree/35122105b0c1bb648754625d8e3920eafa9bc599).
APTL is the previous name of LilRAE. These are source-inspection identities,
not identities of a newly verified deployment.

- [ADR-039](https://github.com/OpenRAE/lilrae/blob/5bef477de828dc77c0df1dc9592487809e52df14/docs/adrs/adr-039-web-control-plane-authentication.md)
  governs the authenticated operator web control plane and its loopback default.
  It does not authorize participant access to a scenario service.
- [ADR-053](https://github.com/OpenRAE/lilrae/blob/5bef477de828dc77c0df1dc9592487809e52df14/docs/adrs/adr-053-pack-backend-deployment-serving-interaction-seam.md)
  implements closed issue #895. Its installed provider returns operator-group
  memberships only; it cannot supply containers, networks, mounts, ports,
  configuration or observation policy. It is not an endpoint realization seam.
- [RAES realization authority](https://github.com/OpenRAE/rae/blob/35122105b0c1bb648754625d8e3920eafa9bc599/docs/explain/reference/explicitness-realization-semantics.md)
  carries scoped author permission through planning and observation. Backend
  capability is not permission; exact leaves remain exact under an open scope.
  Closure and apparatus evidence consume the governing RAES contracts.
- [PR #1108](https://github.com/OpenRAE/lilrae/pull/1108) removed the executable
  SOAR fixup. [#989](https://github.com/OpenRAE/lilrae/issues/989) confirms its
  collision-causing proxy was removed. The surviving workshop `.sh.txt` is
  historical evidence, not a supported startup path.
- [PR #1047](https://github.com/OpenRAE/lilrae/pull/1047) makes host-run MCP
  configuration consume the run's resolved host ports. Current TechVault
  intentionally contains no host publications; see the
  [internal service-port record](techvault-internal-service-ports-preflight.md).

The four recorded blockers (#895, #915, #916 and RAES #1067) are closed.
The earlier claim that an audience-aware endpoint DTO must exist before any
work can proceed is superseded by the existing service, participant-access,
deployment and realization authorities. No local endpoint schema is needed.

## Classification of every removed proxy behavior

The [archived script](https://github.com/OpenRAE/lilrae/blob/5bef477de828dc77c0df1dc9592487809e52df14/tools/workshop/arsenal-2026/envpack-soar-fixups.sh.txt)
identifies the actual effects. Its mixed concerns must be classified separately.

| Removed behavior | Semantic owner and current authority |
| --- | --- |
| Access to MISP, TheHive and Shuffle functionality | TechVault authors service/application outcomes through RAES. Their existing nodes and `security-net` topology remain authoritative. |
| Host MCP clients calling the services | LilRAE deployment-serving transport and private client configuration. PR #1047 resolves per-run ports; a reachable host endpoint does not establish participant authority. |
| Participant use of stdio MCP tools | TechVault declares separate byte-bound red/blue MCP sources and SSH access to Kali/SOC workstation. Tool execution is in-world scenario content; host-run MCP clients are a separate backend path. |
| `alpine/socat` process, shell entrypoint, restart policy and `aptl-mcp-endpoints` container | Retired backend transport workaround. The process supplied no measurement function and is not experimental measurement apparatus. It must not become a scenario node merely because it was a container. |
| Compose project/service labels on that container | Backend ownership bookkeeping; labels alone did not admit the extra runtime object. |
| Attachment to TheHive's discovered network | Retired backend transport attachment. The scenario's authored service links remain; any replacement attachment requires backend admission and observed reachability accounting. |
| Read-only mount of MISP's leaf certificate and private key as proxy credentials | Retired credential reuse across service identities. Generated-output selection governs consumers; read-only access does not authorize a new private-key consumer. The producer-private CA key must remain withheld. |
| MISP port 8443 TCP passthrough to `misp:443` | Backend forwarding implementation; the authored MISP outcome is HTTPS on its declared service with its service identity. |
| TheHive port 9000 TLS termination followed by plaintext to `thehive:9000` | Retired transport adaptation. Current native TheHive configuration terminates HTTPS using its own selected keystore; author the HTTPS application outcome rather than revive the shared-certificate proxy. |
| Shuffle port 3443 TLS termination/re-origination with upstream verification disabled | Retired backend trust bypass. Current frontend has its own selected certificate/key; client trust and upstream trust require separate verification. |
| Loopback host publications 8443, 9000 and 3443 | Backend deployment exposure, now resolved/remapped through existing host-port configuration. Loopback is binding scope, not an audience or authorization grant. |
| Endpoint reachability, TLS identity and runtime inventory observation | RAES owns portable meaning; LilRAE owns acquisition and deployment readback. Participant, operator and measurement projections must retain their actual caller/namespace and authority. |

## Current authored outcome and concrete correction

MISP declares `https:443`; Shuffle frontend declares `https:443` and `http:80`.
TheHive declares `thehive-api:9000`. All are service-side declarations without
host locators. Generated SOC material uses read-only, selected-output consumers;
the CA private key is producer-private.

TheHive's application declared `protocol: http`, while its generated keystore,
[native TLS configuration](https://github.com/OpenRAE/lilrae/blob/5bef477de828dc77c0df1dc9592487809e52df14/config/thehive/application.conf)
(`https.port = 9000`, HTTP disabled), and host MCP client require HTTPS.
The pack correction is `protocol: https` on `thehive-web`, preserving its
service reference, port, authenticated route, topology and certificate
selection. The participant-study derivative carries the same correction; its
existing base-equivalence regression prevents the two authored environments
from drifting. The regression must compile that outcome through RAES and verify
the existing least-privilege certificate contract. Rebind the SDL and external
concept subjects through `tools/refresh_pack_sdl_binding.py`.

## Acceptance-criterion reconciliation

| #294 criterion | Delivered evidence and remaining proof |
| --- | --- |
| Classify every proxy behavior | The effect-by-effect table above, archived script, ADR-039/053 and RAES authority provide the classification. |
| Author scenario-significant endpoint outcomes | Existing service/application declarations, in-world participant sources and SSH access; correct TheHive's HTTPS application outcome and guard it with a compiled regression. |
| Govern backend-only behavior separately | Native deployment configuration, port resolution and private MCP config own host transport. ADR-053 expressly cannot authorize realization effects. No proxy metadata is added to the pack. |
| Account for every runtime object, attachment, mount, certificate grant and publication | Backend inventory, runtime readback and selected-output tests exist. A fresh run must bind its actual inventory and authorized apparatus to the admitted plan; source inspection alone is not this proof. |
| Clean realization without injection | Executable fixup removed in PR #1108; that PR reports an installed-wheel clean start. Reproduce with the corrected pack identity and record absence of the retired proxy. |
| Distinguish audiences and detect excess exposure | Authored workstation access and separate backend host configuration establish distinct paths. Negative backend tests reject excess ports, mounts, attachments and containers. Record both audience projections from the fresh run. |
| Test reachability, certificate identity, binding scope and unexpected objects | Existing coverage is indexed below. Record full service MCP operations plus positive/negative TLS identity/trust checks and effective bind scope for the same fresh realization. |

## Existing regression evidence and live handoff

At the pinned LilRAE revision, these tests exercise existing enforcement:

- `tests/test_deployment_stateful_realization.py`: certificate key/chain/SAN and
  permissions; wrong keys/SANs; undeclared certificate mounts.
- `tests/test_raes_runtime_observation.py`: mismatched/wildcard publications,
  undeclared published ports, substituted/extra mounts.
- `tests/test_compose_network_readback.py`: extra project attachment and default
  bridge removal must be corroborated by readback.
- `tests/test_techvault_live_gate.py`: missing/unhealthy/stopped nodes and
  undeclared containers fail readiness.
- `tests/test_curated_live_proof.py`: unexpected containers and networks fail
  snapshot comparison.
- `src/aptl_techvault/participant_smoke.py`: `FULL_TECHVAULT_SMOKE_OPERATIONS`
  includes case, threat-intelligence and workflow operations. The smaller
  participant smoke set alone does not exercise these three services.

Nine focused backend regression cases were run read-only at LilRAE revision
`59eaae3945cce3554dfa7d0849acd32c6668cc74` and passed: certificate
chain/key/SAN validation, wrong-key/wrong-SAN rejection, unauthorized certificate
mounts, wildcard/excess publication, excess bind mounts, extra network
attachments, and undeclared-container readiness. Their pytest cache and scratch
files were confined to `/tmp`; the backend checkout was not changed. These are
controlled fixture tests, not a fresh deployment qualification.

Fresh live proof must record pack set digest, backend identity, admitted plan,
authorized apparatus, native observed inventory, per-audience service results,
TLS identity/trust and bind scope, plus cleanup. Use the backend's existing
bounded evidence/redaction paths; do not persist credentials, key material,
private configuration or raw tool payloads in this repository.

Until that proof is available, #294 remains open. Closed dependencies and a
successful TCP connection are insufficient evidence to check all its criteria.
