package envpacks

import "embed"

// Schemas holds the JSON Schemas of the pack contracts, as the Python
// implementation packages them. Each file is a schema written in YAML, named
// NAME.schema.yaml.
//
//go:embed src/raes_env_packs/resources/schemas/*.schema.yaml
var Schemas embed.FS

// SchemaDir is the directory of the schemas in Schemas.
const SchemaDir = "src/raes_env_packs/resources/schemas"
