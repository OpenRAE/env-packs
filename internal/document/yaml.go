package document

import (
	"bytes"
	"errors"
	"io"
	"math"
	"slices"
	"unicode/utf8"

	"go.yaml.in/yaml/v3"
)

// quotedStyles are the styles of a YAML scalar that is a string in each
// reader.
const quotedStyles = yaml.DoubleQuotedStyle | yaml.SingleQuotedStyle | yaml.LiteralStyle | yaml.FoldedStyle

// DecodeYAML decodes one pack-owned YAML document. It rejects a document over
// the limits, invalid UTF-8, more than one document, a null document, a
// duplicate or non-string key, an explicit tag, a number that is not finite,
// and a plain scalar that the Python reader reads as another value. Mappings
// decode to map[string]any and sequences to []any.
func DecodeYAML(data []byte, limits Limits) (any, error) {
	if len(data) > limits.MaxBytes {
		return nil, fail(CodeSizeLimit, 0)
	}
	if !utf8.Valid(data) {
		return nil, fail(CodeInvalidUTF8, 0)
	}
	dec := yaml.NewDecoder(bytes.NewReader(data))
	var root yaml.Node
	if err := dec.Decode(&root); err != nil {
		if errors.Is(err, io.EOF) {
			return nil, fail(CodeNull, 0)
		}
		return nil, fail(CodeSyntax, 0)
	}
	var next yaml.Node
	if err := dec.Decode(&next); !errors.Is(err, io.EOF) {
		return nil, fail(CodeMultipleDocuments, next.Line)
	}
	w := yamlWalker{limits: limits}
	if err := w.visit(&root, 0); err != nil {
		return nil, err
	}
	// A decode copies the anchored node for each alias, so nested aliases
	// can expand far past the counts above. PyYAML shares the anchored value
	// instead, so it does not need this bound.
	if expandedSize(&root, limits.MaxNodes) > limits.MaxNodes {
		return nil, fail(CodeNodeLimit, 0)
	}
	var value any
	// After the walk, the decode fails only by its own alias rule: more than
	// 99 percent of the nodes that it makes come from aliases.
	if err := root.Decode(&value); err != nil {
		return nil, fail(CodeAliasLimit, 0)
	}
	if value == nil {
		return nil, fail(CodeNull, root.Line)
	}
	return value, nil
}

// yamlWalker checks the node tree of one document before the decode, so that
// aliases cannot expand past the limits.
type yamlWalker struct {
	limits  Limits
	nodes   int
	aliases int
	// open holds the collections that hold the node of the walk.
	open []*yaml.Node
}

// visit checks node n at nesting depth, and the nodes below it. It counts the
// nodes and the aliases as the event stream of PyYAML does, and it does not
// follow an alias.
func (w *yamlWalker) visit(n *yaml.Node, depth int) error {
	switch n.Kind {
	case yaml.ScalarNode:
		_, err := w.scalar(n)
		return err
	case yaml.AliasNode:
		if slices.Contains(w.open, n.Alias) {
			return fail(CodeAliasCycle, n.Line)
		}
		w.aliases++
		return w.checkCounts(n.Line)
	case yaml.MappingNode, yaml.SequenceNode:
		if n.Style&yaml.TaggedStyle != 0 {
			return fail(CodeExplicitTag, n.Line)
		}
		w.nodes++
		depth++
		if depth > w.limits.MaxDepth {
			return fail(CodeDepthLimit, n.Line)
		}
		if err := w.checkCounts(n.Line); err != nil {
			return err
		}
		w.open = append(w.open, n)
		defer func() { w.open = w.open[:len(w.open)-1] }()
		if n.Kind == yaml.MappingNode {
			return w.visitMapping(n, depth)
		}
	case yaml.DocumentNode:
	}
	for _, child := range n.Content {
		if err := w.visit(child, depth); err != nil {
			return err
		}
	}
	return nil
}

// visitMapping checks the keys and the values of mapping n. Each key must
// be a scalar with a string value, and no key may repeat.
func (w *yamlWalker) visitMapping(n *yaml.Node, depth int) error {
	keys := make(map[string]bool)
	for pair := range slices.Chunk(n.Content, 2) {
		key, value := pair[0], pair[1]
		if key.Kind != yaml.ScalarNode {
			return fail(CodeKeyType, key.Line)
		}
		keyValue, err := w.scalar(key)
		if err != nil {
			return err
		}
		name, ok := keyValue.(string)
		if !ok {
			return fail(CodeKeyType, key.Line)
		}
		if keys[name] {
			return fail(CodeDuplicateKey, key.Line)
		}
		keys[name] = true
		if err := w.visit(value, depth); err != nil {
			return err
		}
	}
	return nil
}

// scalar counts scalar n, checks it, and returns its value.
func (w *yamlWalker) scalar(n *yaml.Node) (any, error) {
	if n.Style&yaml.TaggedStyle != 0 {
		return nil, fail(CodeExplicitTag, n.Line)
	}
	w.nodes++
	if err := w.checkCounts(n.Line); err != nil {
		return nil, err
	}
	return checkScalar(n)
}

// checkCounts applies the alias limit, and the node limit to the expansion
// bound of the Python code: the nodes times the aliases plus one.
func (w *yamlWalker) checkCounts(line int) error {
	switch {
	case w.aliases > w.limits.MaxAliases:
		return fail(CodeAliasLimit, line)
	case w.nodes*(w.aliases+1) > w.limits.MaxNodes:
		return fail(CodeNodeLimit, line)
	}
	return nil
}

// checkScalar returns the value of scalar n. It rejects a plain scalar that
// the readers read as different values, and a number that is not finite.
func checkScalar(n *yaml.Node) (any, error) {
	var value any
	if err := n.Decode(&value); err != nil {
		return nil, fail(CodeSyntax, n.Line)
	}
	if n.Style&quotedStyles == 0 && !sameValue(n.Value, value) {
		return nil, fail(CodeAmbiguousScalar, n.Line)
	}
	if f, ok := value.(float64); ok && (math.IsInf(f, 0) || math.IsNaN(f)) {
		return nil, fail(CodeNonFinite, n.Line)
	}
	return value, nil
}

// expandedSize returns the number of nodes of n after each alias expands to a
// copy of its anchored node. It stops counting when the size passes limit.
// The walk rejects an alias inside its own anchor, so the recursion ends.
func expandedSize(n *yaml.Node, limit int) int {
	size := 1
	switch n.Kind {
	case yaml.AliasNode:
		return expandedSize(n.Alias, limit)
	case yaml.DocumentNode:
		size = 0
	case yaml.ScalarNode, yaml.MappingNode, yaml.SequenceNode:
	}
	for _, child := range n.Content {
		size += expandedSize(child, limit)
		if size > limit {
			return size
		}
	}
	return size
}
