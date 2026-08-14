# TechVault integration endpoint ownership preflight

Issue #294 is not ready for endpoint implementation. The TechVault pack already
declares the three SOC service surfaces, their loopback publications, and their
certificate consumers. It does not declare `aptl-mcp-endpoints`, and the
repository has no evidence that the injected container is itself TechVault
scenario content.

Implementation remains gated on the APTL and RAES records named below. The gate
prevents a backend transport from being copied into the SDL merely because the
current backend realizes it as a container.

## Current authority and evidence

The authored TechVault SDL already contains these service outcomes:

| Service | Authored service | Authored host publication | Authored certificate consumer |
| --- | --- | --- | --- |
| MISP | `misp:https/tcp/443` | `127.0.0.1:8443` to `443` | CA, MISP leaf certificate, and MISP private key |
| TheHive | `thehive:thehive-api/tcp/9000` | `127.0.0.1:9000` to `9000` | CA, TheHive keystore, and keystore password |
| Shuffle | `shuffle-frontend:https/tcp/443` and `http/tcp/80` | `127.0.0.1:3443` to `443` and `127.0.0.1:3001` to `80` | CA, Shuffle leaf certificate, and Shuffle private key |

All three nodes attach to `security-net`. The certificate bundle keeps the CA
private key producer-private and gives each consumer only selected outputs.
`aptl-mcp-endpoints` is absent from `nodes`, `infrastructure`, generated-artifact
consumers, and the pack's topology regression guard.

The existing `kali-ssh-proxy` and `webapp-proxy` nodes are a useful but narrow
precedent. They are authored operator entry surfaces with a constrained RAES
materialization specification, explicit network links, dependencies, and
loopback publications. That precedent applies only after an endpoint has been
shown to be scenario-authored. It is not permission to model every backend
bridge as a scenario node.

`assets/content/misp-sync-readme.md` records the migrated APTL connection
assumption: APTL builds local MCP servers and writes a private `.mcp.json` with
generated lab credentials. It also draws the MCP layer outside the scenario and
SOC subgraphs. This byte-bound migration artifact is useful evidence of the
consumer model, but it is not a portable contract or a replacement for APTL
ADR-039, APTL issue #895, or RAES semantics.

## Concern classification

| Concern supplied by the injected container | Semantic owner | Constraint |
| --- | --- | --- |
| MISP, TheHive, and Shuffle service availability | TechVault author, expressed through RAES SDL | Reuse the existing node and service declarations. Do not create parallel endpoint metadata. |
| Whether a participant reaches those services through MCP | RAES participant-access semantics plus the TechVault authoring decision | Unresolved in the current SDL. A loopback binding does not establish an audience. Do not infer participant visibility from reachability. |
| MCP server processes, private client configuration, and generated connection credentials | APTL control plane / participant-access adapter | Keep backend process topology, credential delivery, and client configuration out of portable pack metadata. |
| The proxy container image, process, and lifecycle | Presumptively APTL realization apparatus | It belongs in the admitted authorized-apparatus set unless architectural evidence shows the proxy itself is participant-visible scenario content. It must never be injected after plan admission. |
| Attachment of apparatus to `security-net` | APTL realization binding against an admitted portable or backend contract | Account for the attachment in the admitted plan and observed graph. Do not turn apparatus attachment into TechVault topology by default. |
| MISP, TheHive, and Shuffle certificate identity as observed by a participant | TechVault/RAES outcome when participant-visible; otherwise APTL transport policy | Preserve the authored per-service consumer boundary. A proxy must not receive the CA private key or reuse service private keys without an explicit, least-privilege certificate-consumer contract. |
| TLS termination or forwarding performed only to connect host MCP processes to range services | APTL transport implementation | Parameterize it by a declared target service and required TLS outcome, not by a TechVault-specific shell branch or copied port table. |
| Host publication and interface binding | Split: RAES/TechVault when the exposure is a scenario outcome; APTL when it is apparatus transport | Record audience separately from bind scope. Loopback is a security boundary, not evidence that an endpoint is operator-only or participant-visible. |
| Observation of endpoint reachability, certificate identity, and excess exposure | RAES owns portable observation/evidence meaning; APTL owns backend observation | Compare the realized graph with authored nodes plus authorized apparatus. Report participant and operator projections separately and fail on extra containers, attachments, mounts, certificate grants, or publications. |

## Evidence required before coding

The implementation decision must cite the actual contents of APTL ADR-039, the
pack/backend interaction boundary in
[APTL #895](https://github.com/Brad-Edwards/aptl/issues/895), and the relevant
RAES participant-access, measurement-apparatus, and realization-designation
contracts. This checkout does not carry those records. If RAES cannot express a
scenario-significant outcome, the gap is fixed in RAES rather than with a local
pack schema or an APTL-only semantic alias.

The APTL-side evidence must enumerate the exact injected image/process,
networks, mounts, certificate files, published addresses and ports, TLS
direction, upstream targets, callers, and credentials. Each row must identify
one audience (`participant`, `operator/control-plane`, or `measurement
apparatus`) and one authority. Mixed-audience behavior must be split before a
carrier is selected.

The durable design has one endpoint-binding seam: a semantic target-service
reference plus audience, protocol/TLS outcome, and exposure policy. APTL may
lower that record to backend-specific ports, mounts, and proxy processes and
may render the private MCP client configuration from the admitted realization.
The pack must not carry APTL container names, shell commands, host paths,
credential values, secret-store coordinates, or a second endpoint schema.

## Validation and proof boundaries

Changes to the TechVault SDL must continue through the pinned RAES parser,
`validate_pack()`, the author gate, the TechVault topology tests, and exact
associated-artifact byte binding. The manifest is derived after the final pack
bytes change; it is not hand-edited as a substitute for validation.

Static tests in this repository may guard authored service, audience, exposure,
and certificate-consumer declarations. Backend live tests belong with APTL and
must prove clean realization without post-plan injection, MCP endpoint
reachability from the intended audience, certificate chain and identity,
loopback-only host binding where required, and exact absence of unexpected
runtime objects or excess exposure. A successful TCP connection alone is not
realization evidence.

Diagnostics added here must reuse the bounded `ValidationResult` surface and
shared static authority; content-identity failures continue to use
`PackDigestError`. Neither path may include authored values, certificate or
credential material, absolute paths, raw upstream errors, or unbounded output.
Runtime observation and persistence remain APTL-owned and must use APTL's
existing admitted-plan, evidence, error-envelope, and logging contracts rather
than creating env-packs equivalents.

## Non-goals and rejected shortcuts

- Do not copy `aptl-mcp-endpoints` into the SDL because it happens to be a
  container.
- Do not retain a TechVault-specific post-realization fixup as an exception.
- Do not add endpoint, apparatus, observation, certificate, or realization
  schemas to env-packs; RAES owns those meanings.
- Do not use `pack.compatibility.yaml.operator_surfaces` for runtime endpoints;
  that field indexes shipped pack-local files and tools.
- Do not duplicate the existing MISP, TheHive, Shuffle, published-port, or
  generated-certificate declarations.
- Do not treat loopback, TLS, container health, or reachability as proof of
  participant visibility, authorization, certificate identity, or a clean
  closed-world realization.

No new ADR is required for this preflight. ADR-0009, ADR-0036, and the public
[ownership boundary](../public/ownership-boundary.md) already establish the
applicable repository decision.
