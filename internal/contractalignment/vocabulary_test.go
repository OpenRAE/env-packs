package contractalignment

// vocabulary visits schema declarations, not prose or example payloads.
// Tactic checks omit property names; provenance checks include them.
func vocabulary(value any, properties bool) []string {
	var terms []string
	switch node := value.(type) {
	case map[string]any:
		terms = declarations(node, properties)
		for _, child := range node {
			terms = append(terms, vocabulary(child, properties)...)
		}
	case []any:
		for _, child := range node {
			terms = append(terms, vocabulary(child, properties)...)
		}
	}
	return terms
}

func declarations(node map[string]any, properties bool) []string {
	var terms []string
	if properties {
		if names, ok := node["properties"].(map[string]any); ok {
			for name := range names {
				terms = append(terms, name)
			}
		}
	}
	if values, ok := node["enum"].([]any); ok {
		terms = append(terms, stringTerms(values)...)
	}
	if term, ok := node["const"].(string); ok {
		terms = append(terms, term)
	}
	return terms
}

func stringTerms(values []any) []string {
	var terms []string
	for _, v := range values {
		if term, ok := v.(string); ok {
			terms = append(terms, term)
		}
	}
	return terms
}
