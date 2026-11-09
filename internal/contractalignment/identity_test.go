package contractalignment

import (
	"context"
	"encoding/json"
	"errors"
	"io/fs"
	"os/exec"
	"slices"
	"strings"
	"testing"
	"time"
	"unicode/utf8"
)

func TestIdentityContracts(t *testing.T) {
	repo := repository(t)
	if !strings.Contains(readText(t, repo, "go.mod"), "module github.com/OpenRAE/env-packs\n") {
		t.Error("Go module must keep the canonical env-packs identity")
	}
	for _, tc := range []struct{ file, id, version string }{
		{"pack-compatibility", "https://raes.dev/schemas/environment-pack-compatibility-v2.json", "environment-pack-compatibility/v2"},
		{"provenance", "https://raes.dev/schemas/environment-pack-provenance-v3.json", "environment-pack-provenance/v3"},
	} {
		value := readDocument(t, repo, "src/raes_env_packs/resources/schemas/"+tc.file+".schema.yaml")
		if got := stringAt(t, value, "$id"); got != tc.id {
			t.Errorf("%s $id = %q, want %q", tc.file, got, tc.id)
		}
		if got := stringAt(t, value, "properties", "schema_version", "const"); got != tc.version {
			t.Errorf("%s schema_version = %q, want %q", tc.file, got, tc.version)
		}
	}
	layout := readText(t, repo, "src/raes_env_packs/resources/contract/pack-layout.md")
	if !strings.Contains(layout, "Environment-pack contract version:** `8`") {
		t.Error("pack layout must keep contract version 8")
	}
	// The locator is an external contract; its command implementations port separately.
	if !strings.Contains(readText(t, repo, "src/raes_env_packs/digest.py"), `_PACK_URI_SCHEME = "raes-environment-pack"`) {
		t.Error("pack locator scheme changed")
	}
	for _, name := range []string{"docs/public/environment-packs.md", "docs/public/raes-migration.md", "src/raes_env_packs/resources/contract/pack-layout.md", "src/raes_env_packs/resources/schemas/provenance.schema.yaml"} {
		text := readText(t, repo, name)
		if !strings.Contains(text, "raes.lock.json") || strings.Contains(text, "a"+"ces.lock.json") {
			t.Errorf("%s must use the RAES lock filename", name)
		}
	}
	var config map[string]any
	if err := json.Unmarshal([]byte(readText(t, repo, "release-please-config.json")), &config); err != nil {
		t.Fatal(err)
	}
	if got := stringAt(t, config, "packages", ".", "package-name"); got != "raes-env-packs" {
		t.Errorf("release package = %q, want raes-env-packs", got)
	}
}

func TestBoundProjectIdentities(t *testing.T) {
	repo := repository(t)
	ground := readDocument(t, repo, ".ground-control.yaml")
	for _, tc := range []struct {
		keys []string
		want string
	}{
		{[]string{"project"}, "a" + "ces-scenario-packs"},
		{[]string{"short_code"}, "ASP"},
		{[]string{"docs", "workflow_reference"}, "docs/public/environment-packs.md"},
		{[]string{"example_paths", "source"}, "src/raes_env_packs/"},
		{[]string{"sonarcloud", "project_key"}, "OpenRAE_env-packs"},
		{[]string{"sonarcloud", "organization"}, "raesystem"},
	} {
		if got := stringAt(t, ground, tc.keys...); got != tc.want {
			t.Errorf("identity %v = %q, want %q", tc.keys, got, tc.want)
		}
	}
	sonar := readText(t, repo, "sonar-project.properties")
	for _, line := range []string{"sonar.projectKey=OpenRAE_env-packs", "sonar.organization=raesystem"} {
		if !strings.Contains(sonar, line) {
			t.Errorf("Sonar identity lacks %q", line)
		}
	}
}

func TestTrackedFilesDoNotReviveRetiredIdentity(t *testing.T) {
	ctx, cancel := context.WithTimeout(t.Context(), 10*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", "ls-files", "-z")
	cmd.Dir = "../.."
	cmd.Env = []string{"PATH=/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=/dev/null"}
	output, err := cmd.Output()
	if err != nil {
		t.Fatalf("git ls-files failed: %v", err)
	}
	repo := repository(t)
	for name := range strings.SplitSeq(string(output), "\x00") {
		checkTrackedIdentity(t, repo, name)
	}
}

func checkTrackedIdentity(t *testing.T, repo fs.FS, name string) {
	t.Helper()
	if name == "" || historical(name) {
		return
	}
	data, err := fs.ReadFile(repo, name)
	if errors.Is(err, fs.ErrNotExist) {
		return
	}
	if err != nil {
		t.Fatal(err)
	}
	if !utf8.Valid(data) {
		return
	}
	text := string(data)
	for _, line := range boundLines(name) {
		if strings.Count(text, line) != 1 {
			t.Errorf("%s must retain exactly one bound identity %q", name, line)
		}
		text = strings.Replace(text, line, "", 1)
	}
	if retiredIdentity(text) {
		t.Errorf("%s revives a retired identity", name)
	}
}

func TestRetiredIdentityRule(t *testing.T) {
	retired := "a" + "ces"
	for _, tc := range []struct {
		text string
		want bool
	}{
		{"raes-env-packs", false}, {retired + "-sdl", true}, {retired + "_sdl", true},
		{retired + "-scenario-packs", true}, {retired + "_scenario_packs", true}, {"Brad-Edwards/" + retired, true},
	} {
		if got := retiredIdentity(tc.text); got != tc.want {
			t.Errorf("retiredIdentity(%q) = %t, want %t", tc.text, got, tc.want)
		}
	}
	if !historical("CHANGELOG.md") || historical("docs/public/new-guide.md") {
		t.Error("historical exceptions must stay narrow")
	}
}

func retiredIdentity(text string) bool {
	retired := "a" + "ces"
	for _, term := range []string{retired + "-sdl", retired + "_sdl", retired + "-scenario-packs", retired + "_scenario_packs", "Brad-Edwards/" + retired} {
		if strings.Contains(text, term) {
			return true
		}
	}
	return false
}

func boundLines(name string) []string {
	switch name {
	case ".ground-control.yaml":
		return []string{"project: " + "a" + "ces-scenario-packs", "project_key: OpenRAE_env-packs"}
	case "sonar-project.properties":
		return []string{"https://sonarcloud.io/project/overview?id=OpenRAE_env-packs", "sonar.projectKey=OpenRAE_env-packs"}
	default:
		return nil
	}
}

func historical(name string) bool {
	if slices.Contains([]string{
		"CHANGELOG.md", "SECURITY.md", "docs/decisions/adrs/README.md", "docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md", "docs/public/raes-migration.md",
		"packs/techvault/assets/content/misp-sync-src.tar", "packs/techvault-participant-study/assets/content/misp-sync-src.tar",
	}, name) {
		return true
	}
	for _, file := range []string{
		"0001-repository-purpose-and-boundary.md", "0002-distribute-as-installable-package.md", "0003-build-and-release-model.md", "0004-sbom-and-supply-chain.md", "0005-automatic-release-on-merge-to-main.md", "0006-conventional-commit-releases.md", "0007-changelog-driven-versioning.md", "0008-adopt-release-please.md", "0009-scenario-packs-subordinate-to-aces.md", "0010-consume-aces-reusable-asset-trust-policy.md", "0011-require-pinned-" + "a" + "ces-sdl-validation.md", "0012-pack-content-identity-and-trust-boundary.md", "0013-separate-consumer-static-validation-from-author-ci.md", "0014-consume-aces-concept-authority.md", "0015-attest-python-distribution-build-provenance.md", "0016-automate-dependency-updates.md", "0017-sign-release-tags-with-keyless-sigstore.md", "0018-openssf-scorecard-posture.md", "0019-preserve-history-in-dev-main-promotions.md", "0020-no-auto-merge.md", "0031-compose-beginner-safe-pack-checks-from-existing-authorities.md", "0034-compose-progressive-scaffolding-from-pack-and-raes-authorities.md",
	} {
		if name == "docs/decisions/adrs/"+file {
			return true
		}
	}
	return false
}
