# First-party infrastructure kits

Use this reference to select an exact kit release and find its original authoring material.
For composition steps, use the [integration guide](kit-integration.md).
For a learning exercise, use the [first-pack tutorial](../public/quickstart.md).
The [kit explanation](../public/kit-content-strategy.md) describes why kits exist.

## Release references

Each version link opens that release's original README.
The integration link opens the newest listed release's exact integration material.
For an older version, open `assets/integration.md` under that version's directory.
The table identifies the domain parameter for the newest listed release.
Read its module for defaults, types, exports, and constraints.

Kit versions are independent of the package version.
The package contains historical releases as well as newer releases.
A newer version does not qualify a backend or prove runtime readiness.

| Kit | Exact release references | Integration reference | Domain parameter |
| --- | --- | --- | --- |
| Application/API service | [1.0.0](../../kits/infrastructure.application-api-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.application-api-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.application-api-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.application-api-service/1.2.0/assets/integration.md) | `api_base_path` |
| Authoritative DNS service | [1.0.0](../../kits/infrastructure.authoritative-dns-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.authoritative-dns-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.authoritative-dns-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.authoritative-dns-service/1.2.0/assets/integration.md) | `zone_name` |
| Browser workstation | [1.0.0](../../kits/infrastructure.browser-workstation/1.0.0/README.md), [1.1.0](../../kits/infrastructure.browser-workstation/1.1.0/README.md), [1.2.0](../../kits/infrastructure.browser-workstation/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.browser-workstation/1.2.0/assets/integration.md) | `browser_profile` |
| Cache / key-value store | [1.0.0](../../kits/infrastructure.cache-key-value-store/1.0.0/README.md), [1.1.0](../../kits/infrastructure.cache-key-value-store/1.1.0/README.md), [1.2.0](../../kits/infrastructure.cache-key-value-store/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.cache-key-value-store/1.2.0/assets/integration.md) | `key_prefix` |
| Certificate authority | [1.0.0](../../kits/infrastructure.certificate-authority/1.0.0/README.md), [1.1.0](../../kits/infrastructure.certificate-authority/1.1.0/README.md), [1.2.0](../../kits/infrastructure.certificate-authority/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.certificate-authority/1.2.0/assets/integration.md) | `authority_name` |
| Container orchestration | [1.0.0](../../kits/infrastructure.container-orchestration/1.0.0/README.md), [1.1.0](../../kits/infrastructure.container-orchestration/1.1.0/README.md), [1.2.0](../../kits/infrastructure.container-orchestration/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.container-orchestration/1.2.0/assets/integration.md) | `cluster_name` |
| DHCP / IPAM service | [1.0.0](../../kits/infrastructure.dhcp-ipam-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.dhcp-ipam-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.dhcp-ipam-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.dhcp-ipam-service/1.2.0/assets/integration.md) | `address_pool` |
| Firewall / NAT | [1.0.0](../../kits/infrastructure.firewall-nat/1.0.0/README.md), [1.1.0](../../kits/infrastructure.firewall-nat/1.1.0/README.md), [1.2.0](../../kits/infrastructure.firewall-nat/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.firewall-nat/1.2.0/assets/integration.md) | `ruleset_name` |
| Git forge | [1.0.0](../../kits/infrastructure.git-forge/1.0.0/README.md), [1.1.0](../../kits/infrastructure.git-forge/1.1.0/README.md), [1.2.0](../../kits/infrastructure.git-forge/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.git-forge/1.2.0/assets/integration.md) | `organization_name` |
| Image-inference service | [1.0.0](../../kits/infrastructure.image-inference-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.image-inference-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.image-inference-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.image-inference-service/1.2.0/assets/integration.md) | `model_name` |
| Inference API gateway | [1.0.0](../../kits/infrastructure.inference-api-gateway/1.0.0/README.md), [1.1.0](../../kits/infrastructure.inference-api-gateway/1.1.0/README.md), [1.2.0](../../kits/infrastructure.inference-api-gateway/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.inference-api-gateway/1.2.0/assets/integration.md) | `route_name` |
| Isolated Python analysis sandbox | [1.0.0](../../kits/infrastructure.isolated-python-analysis-sandbox/1.0.0/README.md), [1.1.0](../../kits/infrastructure.isolated-python-analysis-sandbox/1.1.0/README.md), [1.2.0](../../kits/infrastructure.isolated-python-analysis-sandbox/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.isolated-python-analysis-sandbox/1.2.0/assets/integration.md) | `workspace_name` |
| Issue tracker | [1.0.0](../../kits/infrastructure.issue-tracker/1.0.0/README.md), [1.1.0](../../kits/infrastructure.issue-tracker/1.1.0/README.md), [1.2.0](../../kits/infrastructure.issue-tracker/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.issue-tracker/1.2.0/assets/integration.md) | `project_key` |
| Lab portal | [1.0.0](../../kits/infrastructure.lab-portal/1.0.0/README.md), [1.1.0](../../kits/infrastructure.lab-portal/1.1.0/README.md), [1.2.0](../../kits/infrastructure.lab-portal/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.lab-portal/1.2.0/assets/integration.md) | `portal_title` |
| LDAP directory | [1.0.0](../../kits/infrastructure.ldap-directory/1.0.0/README.md), [1.1.0](../../kits/infrastructure.ldap-directory/1.1.0/README.md), [1.2.0](../../kits/infrastructure.ldap-directory/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.ldap-directory/1.2.0/assets/integration.md) | `directory_suffix` |
| Linux domain member | [1.0.0](../../kits/infrastructure.linux-domain-member/1.0.0/README.md), [1.1.0](../../kits/infrastructure.linux-domain-member/1.1.0/README.md), [1.2.0](../../kits/infrastructure.linux-domain-member/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.linux-domain-member/1.2.0/assets/integration.md) | `computer_name` |
| Load/rehearsal runner | [1.0.0](../../kits/infrastructure.load-rehearsal-runner/1.0.0/README.md), [1.1.0](../../kits/infrastructure.load-rehearsal-runner/1.1.0/README.md), [1.2.0](../../kits/infrastructure.load-rehearsal-runner/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.load-rehearsal-runner/1.2.0/assets/integration.md) | `workload_profile` |
| Message broker | [1.0.0](../../kits/infrastructure.message-broker/1.0.0/README.md), [1.1.0](../../kits/infrastructure.message-broker/1.1.0/README.md), [1.2.0](../../kits/infrastructure.message-broker/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.message-broker/1.2.0/assets/integration.md) | `virtual_host` |
| Model registry | [1.0.0](../../kits/infrastructure.model-registry/1.0.0/README.md), [1.1.0](../../kits/infrastructure.model-registry/1.1.0/README.md), [1.2.0](../../kits/infrastructure.model-registry/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.model-registry/1.2.0/assets/integration.md) | `registry_namespace` |
| Notebook environment | [1.0.0](../../kits/infrastructure.notebook-environment/1.0.0/README.md), [1.1.0](../../kits/infrastructure.notebook-environment/1.1.0/README.md), [1.2.0](../../kits/infrastructure.notebook-environment/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.notebook-environment/1.2.0/assets/integration.md) | `workspace_name` |
| Observability/evidence store | [1.0.0](../../kits/infrastructure.observability-evidence-store/1.0.0/README.md), [1.1.0](../../kits/infrastructure.observability-evidence-store/1.1.0/README.md), [1.2.0](../../kits/infrastructure.observability-evidence-store/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.observability-evidence-store/1.2.0/assets/integration.md) | `retention_profile` |
| OIDC identity provider | [1.0.0](../../kits/infrastructure.oidc-identity-provider/1.0.0/README.md), [1.1.0](../../kits/infrastructure.oidc-identity-provider/1.1.0/README.md), [1.2.0](../../kits/infrastructure.oidc-identity-provider/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.oidc-identity-provider/1.2.0/assets/integration.md) | `realm_name` |
| Owlbear protected target | [1.0.0](../../kits/infrastructure.owlbear-protected-target/1.0.0/README.md), [1.1.0](../../kits/infrastructure.owlbear-protected-target/1.1.0/README.md) | [1.1.0 integration](../../kits/infrastructure.owlbear-protected-target/1.1.0/assets/integration.md) | `daemon_active_state` |
| Policy engine | [1.0.0](../../kits/infrastructure.policy-engine/1.0.0/README.md), [1.1.0](../../kits/infrastructure.policy-engine/1.1.0/README.md), [1.2.0](../../kits/infrastructure.policy-engine/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.policy-engine/1.2.0/assets/integration.md) | `policy_bundle` |
| PostgreSQL database | [1.0.0](../../kits/infrastructure.postgresql-database/1.0.0/README.md), [1.1.0](../../kits/infrastructure.postgresql-database/1.1.0/README.md), [1.2.0](../../kits/infrastructure.postgresql-database/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.postgresql-database/1.2.0/assets/integration.md) | `database_name` |
| Python evaluation worker | [1.0.0](../../kits/infrastructure.python-evaluation-worker/1.0.0/README.md), [1.1.0](../../kits/infrastructure.python-evaluation-worker/1.1.0/README.md), [1.2.0](../../kits/infrastructure.python-evaluation-worker/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.python-evaluation-worker/1.2.0/assets/integration.md) | `queue_name` |
| Python package resolver | [1.0.0](../../kits/infrastructure.python-package-resolver/1.0.0/README.md), [1.1.0](../../kits/infrastructure.python-package-resolver/1.1.0/README.md), [1.2.0](../../kits/infrastructure.python-package-resolver/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.python-package-resolver/1.2.0/assets/integration.md) | `index_name` |
| RDP-accessible Windows host | [1.0.0](../../kits/infrastructure.rdp-accessible-windows-host/1.0.0/README.md), [1.1.0](../../kits/infrastructure.rdp-accessible-windows-host/1.1.0/README.md) | [1.1.0 integration](../../kits/infrastructure.rdp-accessible-windows-host/1.1.0/assets/integration.md) | `login_name` |
| Reverse proxy/API gateway | [1.0.0](../../kits/infrastructure.reverse-proxy-api-gateway/1.0.0/README.md), [1.1.0](../../kits/infrastructure.reverse-proxy-api-gateway/1.1.0/README.md), [1.2.0](../../kits/infrastructure.reverse-proxy-api-gateway/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.reverse-proxy-api-gateway/1.2.0/assets/integration.md) | `route_prefix` |
| S3-compatible object store | [1.0.0](../../kits/infrastructure.s3-compatible-object-store/1.0.0/README.md), [1.1.0](../../kits/infrastructure.s3-compatible-object-store/1.1.0/README.md), [1.2.0](../../kits/infrastructure.s3-compatible-object-store/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.s3-compatible-object-store/1.2.0/assets/integration.md) | `bucket_name` |
| Samba Active Directory-compatible domain controller | [1.0.0](../../kits/infrastructure.samba-active-directory-domain-controller/1.0.0/README.md), [1.1.0](../../kits/infrastructure.samba-active-directory-domain-controller/1.1.0/README.md), [1.2.0](../../kits/infrastructure.samba-active-directory-domain-controller/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.samba-active-directory-domain-controller/1.2.0/assets/integration.md) | `domain_name` |
| Search/index service | [1.0.0](../../kits/infrastructure.search-index-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.search-index-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.search-index-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.search-index-service/1.2.0/assets/integration.md) | `index_name` |
| Secrets store | [1.0.0](../../kits/infrastructure.secrets-store/1.0.0/README.md), [1.1.0](../../kits/infrastructure.secrets-store/1.1.0/README.md), [1.2.0](../../kits/infrastructure.secrets-store/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.secrets-store/1.2.0/assets/integration.md) | `mount_path` |
| Shuffle automation service | [1.0.0](../../kits/infrastructure.shuffle-automation-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.shuffle-automation-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.shuffle-automation-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.shuffle-automation-service/1.2.0/assets/integration.md) | `tenant_name` |
| SMB file service | [1.0.0](../../kits/infrastructure.smb-file-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.smb-file-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.smb-file-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.smb-file-service/1.2.0/assets/integration.md) | `share_name` |
| SMTP/IMAP mail service | [1.0.0](../../kits/infrastructure.smtp-imap-mail-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.smtp-imap-mail-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.smtp-imap-mail-service/1.2.0/README.md), [1.3.0](../../kits/infrastructure.smtp-imap-mail-service/1.3.0/README.md) | [1.3.0 integration](../../kits/infrastructure.smtp-imap-mail-service/1.3.0/assets/integration.md) | `mail_domain` |
| SSH-accessible Linux host | [1.0.0](../../kits/infrastructure.ssh-accessible-linux-host/1.0.0/README.md), [1.1.0](../../kits/infrastructure.ssh-accessible-linux-host/1.1.0/README.md), [1.2.0](../../kits/infrastructure.ssh-accessible-linux-host/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.ssh-accessible-linux-host/1.2.0/assets/integration.md) | `login_name` |
| Static web service | [1.0.0](../../kits/infrastructure.static-web-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.static-web-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.static-web-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.static-web-service/1.2.0/assets/integration.md) | `site_name` |
| Suricata network intrusion-detection sensor | [1.0.0](../../kits/infrastructure.suricata-network-intrusion-detection-sensor/1.0.0/README.md), [1.1.0](../../kits/infrastructure.suricata-network-intrusion-detection-sensor/1.1.0/README.md), [1.2.0](../../kits/infrastructure.suricata-network-intrusion-detection-sensor/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.suricata-network-intrusion-detection-sensor/1.2.0/assets/integration.md) | `ruleset_name` |
| Telemetry collector | [1.0.0](../../kits/infrastructure.telemetry-collector/1.0.0/README.md), [1.1.0](../../kits/infrastructure.telemetry-collector/1.1.0/README.md), [1.2.0](../../kits/infrastructure.telemetry-collector/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.telemetry-collector/1.2.0/assets/integration.md) | `pipeline_name` |
| Text-model serving | [1.0.0](../../kits/infrastructure.text-model-serving/1.0.0/README.md), [1.1.0](../../kits/infrastructure.text-model-serving/1.1.0/README.md), [1.2.0](../../kits/infrastructure.text-model-serving/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.text-model-serving/1.2.0/assets/integration.md) | `model_name` |
| Wazuh security monitoring stack | [1.0.0](../../kits/infrastructure.wazuh-security-monitoring-stack/1.0.0/README.md), [1.1.0](../../kits/infrastructure.wazuh-security-monitoring-stack/1.1.0/README.md), [1.2.0](../../kits/infrastructure.wazuh-security-monitoring-stack/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.wazuh-security-monitoring-stack/1.2.0/assets/integration.md) | `enrollment_group` |
| Webmail service | [1.0.0](../../kits/infrastructure.webmail-service/1.0.0/README.md), [1.1.0](../../kits/infrastructure.webmail-service/1.1.0/README.md), [1.2.0](../../kits/infrastructure.webmail-service/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.webmail-service/1.2.0/assets/integration.md) | `site_name` |
| Windows Active Directory domain controller | [1.0.0](../../kits/infrastructure.windows-active-directory-domain-controller/1.0.0/README.md), [1.1.0](../../kits/infrastructure.windows-active-directory-domain-controller/1.1.0/README.md) | [1.1.0 integration](../../kits/infrastructure.windows-active-directory-domain-controller/1.1.0/assets/integration.md) | `domain_name` |
| Windows domain member | [1.0.0](../../kits/infrastructure.windows-domain-member/1.0.0/README.md), [1.1.0](../../kits/infrastructure.windows-domain-member/1.1.0/README.md) | [1.1.0 integration](../../kits/infrastructure.windows-domain-member/1.1.0/assets/integration.md) | `computer_name` |
| Workflow orchestrator | [1.0.0](../../kits/infrastructure.workflow-orchestrator/1.0.0/README.md), [1.1.0](../../kits/infrastructure.workflow-orchestrator/1.1.0/README.md), [1.2.0](../../kits/infrastructure.workflow-orchestrator/1.2.0/README.md) | [1.2.0 integration](../../kits/infrastructure.workflow-orchestrator/1.2.0/assets/integration.md) | `workflow_name` |

## Version differences

The release module is the authority for each declaration.
The original integration guide describes that release, including its historical limits.
Do not edit a versioned directory to update current instructions.

Linux releases from `1.1.0` generally leave the compute substrate open.
Earlier `1.0.0` releases generally require virtual machines.
Owlbear `1.0.0` is an exception: it leaves the substrate open and requires independent kernel-capability admission.
Owlbear `1.1.0` also leaves the substrate open.
The three Windows kit families retain virtual-machine requirements.
Open substrate selection does not grant host privileges or establish container compatibility.

Domain parameters change typed declarations.
Copied seed and integration files can still describe the default parameter values.
Inspect the proposal's SDL and copied assets separately.
PostgreSQL `1.2.0` includes inline JSON seed data that follows `database_name`.
SMTP/IMAP `1.3.0` is a separate release; consult its exact module and integration reference before selection.

Owlbear `1.1.0` pins a later Owlbear source revision than `1.0.0`.
Its provenance describes the upstream research-artifact build identity and the local experiment interfaces.

## Static checks and runtime evidence

Each release contains a RAES module, kit manifest, associated-artifact manifest, seed inventory, integration material, and composition cases.
The manifests bind the release files and declare prerequisites, visibility, planning estimates, limitations, and component-inventory inputs.
The composition cases exercise parameter variation and exported declarations.
These files are authoring content.
They do not start services, deliver credentials, or prove backend readiness.

RAES owns module and scenario semantics.
The [integration guide](kit-integration.md) links the existing authoring workflow and its validation boundary.
