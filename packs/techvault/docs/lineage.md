# Lineage

The full TechVault SDL and its tracked content were migrated from the APTL-era
`origin/dev` at commit `3db5171f3e4add842efd1d81fa0d4fe078511b7e`.
APTL is being renamed to LilRAE; they are one backend project, not separate
products or layers. LilRAE remains a backend consumer, while TechVault is only a
scenario pack and this repository is the editable authority for its
distributable content.

Directory-valued sources were captured as deterministic uncompressed tar
artifacts. Generated SSH keys and SOC certificates were deliberately not copied
from runtime state: RAES generated-artifact declarations retain that lifecycle
and keep producer-private material outside consumer projections.

The APTL-era tracked workstation fixture omitted
`projects/techvault-portal/.env` even though its SDL, archived TechVault
specification, and live smoke test all require it. The deterministic workstation
archive restores the specification's two synthetic loot values
(`DB_PASSWORD=techvault_db_pass` and `JWT_SECRET=techvault-jwt-weak`) rather than
copying an ignored local environment file.
