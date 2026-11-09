package raesadapter_test

import (
	"slices"
	"testing"

	"github.com/OpenRAE/env-packs/internal/raesadapter"
)

func TestVocabularyTermsFromRealRAES(t *testing.T) {
	catalog, err := raesadapter.NewVocabularies()
	if err != nil {
		t.Fatalf("NewVocabularies() error = %v", err)
	}
	for _, tc := range []struct {
		id, term string
	}{
		{"participant-offensive-behavior-activities", "defense-impairment"},
		{"participant-ai-offensive-behavior-activities", "defense-evasion"},
	} {
		terms, ok := catalog.VocabularyTerms(tc.id)
		if !ok || len(terms) == 0 || !slices.Contains(terms, tc.term) {
			t.Fatalf("VocabularyTerms(%q) = %v, %t; want upstream term %q", tc.id, terms, ok, tc.term)
		}
		terms[0] = "changed"
		again, _ := catalog.VocabularyTerms(tc.id)
		if slices.Contains(again, "changed") {
			t.Error("VocabularyTerms() shares mutable state with its caller")
		}
	}
	if terms, ok := catalog.VocabularyTerms("missing-vocabulary"); ok || len(terms) != 0 {
		t.Errorf("VocabularyTerms(missing) = %v, %t, want no terms and false", terms, ok)
	}
}
