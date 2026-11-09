// Package raesadapter implements RAES interfaces with the public RAES Go module.
// Only this package imports RAES. It currently supplies vocabulary access.
package raesadapter

import (
	"github.com/OpenRAE/env-packs/internal/raes"
	"github.com/OpenRAE/rae/implementations/go/contract/concept"
	"github.com/OpenRAE/rae/implementations/go/contract/validation"
)

// NewVocabularies loads the immutable catalog from the pinned RAES module.
// A damaged corpus returns a structured error without authored values.
func NewVocabularies() (raes.Vocabularies, error) {
	schemas, err := validation.New(nil)
	if err != nil {
		return nil, &raes.Error{Code: "concept-catalog-unavailable"}
	}
	authority, err := concept.Load(schemas)
	if err != nil {
		return nil, &raes.Error{Code: "concept-catalog-unavailable"}
	}
	return vocabularies{authority: authority}, nil
}

type vocabularies struct {
	authority *concept.Authority
}

// VocabularyTerms returns an independent copy of the upstream governed terms.
func (v vocabularies) VocabularyTerms(id string) ([]string, bool) {
	record, ok := v.authority.Vocabulary(id)
	return record.Terms, ok
}
