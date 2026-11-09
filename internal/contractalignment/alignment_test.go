package contractalignment

import (
	"io/fs"
	"os"
	"regexp"
	"slices"
	"strings"
	"testing"

	envpacks "github.com/OpenRAE/env-packs"
	"github.com/OpenRAE/env-packs/internal/document"
	"github.com/OpenRAE/env-packs/internal/raesadapter"
	"github.com/OpenRAE/env-packs/internal/schema"
)

func TestSchemaVocabularyTraversal(t *testing.T) {
	for _, tc := range []struct {
		name       string
		value      any
		properties bool
		want       []string
	}{
		{"enum", map[string]any{"enum": []any{"a", 1}, "description": "not vocabulary"}, false, []string{"a"}},
		{"nested const", map[string]any{"items": []any{map[string]any{"const": "b"}}}, false, []string{"b"}},
		{"tactic homograph", map[string]any{"properties": map[string]any{"assets": map[string]any{"const": "c"}}}, false, []string{"c"}},
		{"evidence property", map[string]any{"properties": map[string]any{"integrity_digest": map[string]any{"const": "d"}}}, true, []string{"d", "integrity_digest"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got := vocabulary(tc.value, tc.properties)
			slices.Sort(got)
			if !slices.Equal(got, tc.want) {
				t.Errorf("vocabulary() = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestSchemasDeferToLiveConceptAuthority(t *testing.T) {
	catalog, err := raesadapter.NewVocabularies()
	if err != nil {
		t.Fatalf("NewVocabularies() error = %v", err)
	}
	var governed []string
	for _, id := range []string{"participant-offensive-behavior-activities", "participant-ai-offensive-behavior-activities"} {
		terms, ok := catalog.VocabularyTerms(id)
		if !ok || len(terms) == 0 {
			t.Fatalf("VocabularyTerms(%q) has no upstream terms", id)
		}
		governed = append(governed, terms...)
	}
	paths, err := fs.Glob(envpacks.Schemas, envpacks.SchemaDir+"/*.schema.yaml")
	if err != nil || len(paths) == 0 {
		t.Fatalf("schema discovery = %v, %v, want packaged schemas", paths, err)
	}
	for _, path := range paths {
		for _, term := range vocabulary(readDocument(t, envpacks.Schemas, path), false) {
			if forbiddenTactic(term, governed) {
				t.Errorf("%s declares governed vocabulary %q", path, term)
			}
		}
	}

}

func TestProvenanceAuthority(t *testing.T) {
	repo := repository(t)
	name := envpacks.SchemaDir + "/provenance.schema.yaml"
	value := readDocument(t, repo, name)
	text := readText(t, repo, name)
	for _, marker := range []string{"reusable-asset-trust-policy", "adr-071", "concept-authority"} {
		if !strings.Contains(strings.ToLower(text), marker) {
			t.Errorf("provenance schema lacks authority %q", marker)
		}
	}
	comment := stringAt(t, value, "$comment")
	for _, block := range []string{"sources", "artifacts", "content_safety", "review", "overlays"} {
		if !strings.Contains(comment, block) {
			t.Errorf("schema field-disposition comment lacks %q", block)
		}
	}
}

func TestProvenanceVocabulary(t *testing.T) {
	repo := repository(t)
	value := readDocument(t, repo, envpacks.SchemaDir+"/provenance.schema.yaml")
	evidence := []string{"integrity_digest", "authenticity_signature", "provenance_lock_record", "governance_source", "artifact_checksum"}
	for _, term := range vocabulary(value, true) {
		if slices.Contains(evidence, term) {
			t.Errorf("provenance declares RAES evidence class %q", term)
		}
	}
	item := valueAt(t, value, "properties", "sources", "items")
	properties := objectAt(t, item, "properties")
	if _, exists := properties["kind"]; exists {
		t.Error("sources[].kind must not be a pack classification")
	}
	if closed, ok := valueAt(t, item, "additionalProperties").(bool); !ok || closed {
		t.Errorf("sources[].additionalProperties = %v, want false", closed)
	}
	if required, ok := valueAt(t, item, "required").([]any); !ok || slices.Contains(required, any("kind")) {
		t.Error("sources[] must declare requirements without kind")
	}
}

func TestProvenanceExample(t *testing.T) {
	repo := repository(t)
	set, err := schema.Compile()
	if err != nil {
		t.Fatal(err)
	}
	example := readDocument(t, repo, "src/raes_env_packs/resources/template/docs/provenance-ledger.example.yaml")
	problems, err := set.Validate("provenance", example)
	if err != nil || len(problems) != 0 {
		t.Fatalf("Validate(provenance example) = %v, %v, want no problems", problems, err)
	}
	sources, ok := valueAt(t, example, "sources").([]any)
	if !ok || len(sources) == 0 {
		t.Fatal("example needs a nonempty sources array")
	}
	objectAt(t, sources[0])["kind"] = "local-classification"
	problems, err = set.Validate("provenance", example)
	if err != nil || len(problems) == 0 {
		t.Fatalf("Validate(unknown source kind) = %v, %v, want schema rejection", problems, err)
	}
}

func TestForbiddenTactic(t *testing.T) {
	for _, tc := range []struct {
		term      string
		forbidden bool
	}{
		{"T0001", false}, {"TA0001", true}, {"T1003.001", false}, {"AML.TA0000", true},
		{"defense-evasion", true}, {"assets", false}, {"TAKE", false}, {"T1", false},
	} {
		if got := forbiddenTactic(tc.term, []string{"defense-evasion"}); got != tc.forbidden {
			t.Errorf("forbiddenTactic(%q) = %t, want %t", tc.term, got, tc.forbidden)
		}
	}
}

func TestAuthorityReferences(t *testing.T) {
	repo := repository(t)
	name := envpacks.SchemaDir + "/provenance.schema.yaml"
	for _, file := range []string{"src/raes_env_packs/resources/contract/pack-layout.md", "docs/public/environment-packs.md"} {
		if !strings.Contains(readText(t, repo, file), "reusable-asset-trust-policy") {
			t.Errorf("%s lacks the RAES trust authority", file)
		}
	}
	for _, file := range []string{name, "src/raes_env_packs/resources/contract/pack-layout.md", "docs/public/environment-packs.md", "docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md"} {
		if !strings.Contains(strings.ToLower(readText(t, repo, file)), "concept-authority") {
			t.Errorf("%s lacks the RAES concept authority", file)
		}
	}
	template := "src/raes_env_packs/resources/template/docs/provenance-ledger.yaml"
	if _, ok := readDocument(t, repo, template).(map[string]any); !ok || !strings.Contains(readText(t, repo, template), "reusable-asset-trust-policy") {
		t.Error("provenance template must parse and name RAES trust authority")
	}

}

func TestChallengeTemplate(t *testing.T) {
	challenges := readDocument(t, repository(t), "src/raes_env_packs/resources/template/challenges/challenges.yaml")
	entries, ok := valueAt(t, challenges, "challenges").([]any)
	if !ok {
		t.Fatal("challenges must be an array")
	}
	for _, entry := range entries {
		if _, exists := objectAt(t, entry)["category"]; exists {
			t.Error("challenge template declares category")
		}
	}

}

func repository(t *testing.T) fs.FS {
	t.Helper()
	root, err := os.OpenRoot("../..")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := root.Close(); err != nil {
			t.Error(err)
		}
	})
	return root.FS()
}

func readText(t *testing.T, repo fs.FS, name string) string {
	t.Helper()
	data, err := fs.ReadFile(repo, name)
	if err != nil {
		t.Fatal(err)
	}
	return string(data)
}

func readDocument(t *testing.T, repo fs.FS, name string) any {
	t.Helper()
	value, err := document.DecodeYAML([]byte(readText(t, repo, name)), document.DefaultLimits())
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func valueAt(t *testing.T, value any, keys ...string) any {
	t.Helper()
	for _, key := range keys {
		object, ok := value.(map[string]any)
		if !ok {
			t.Fatalf("valueAt(%v) encountered a non-object", keys)
		}
		var found bool
		value, found = object[key]
		if !found {
			t.Fatalf("valueAt(%v) missing %q", keys, key)
		}
	}
	return value
}

func objectAt(t *testing.T, value any, keys ...string) map[string]any {
	t.Helper()
	got, ok := valueAt(t, value, keys...).(map[string]any)
	if !ok {
		t.Fatalf("objectAt(%v) is not an object", keys)
	}
	return got
}

func stringAt(t *testing.T, value any, keys ...string) string {
	t.Helper()
	got, ok := valueAt(t, value, keys...).(string)
	if !ok {
		t.Fatalf("stringAt(%v) is not a string", keys)
	}
	return got
}

func forbiddenTactic(term string, governed []string) bool {
	return slices.Contains(governed, term) || regexp.MustCompile(`^(?:AML\.)?TA\d{4}$`).MatchString(term)
}
