package document

import "strconv"

// A Code is the stable code of an [Error].
type Code string

// The codes of the errors.
const (
	// CodeSizeLimit marks a document with more bytes than the limit.
	CodeSizeLimit Code = "document.size-limit"
	// CodeInvalidUTF8 marks a document that is not valid UTF-8.
	CodeInvalidUTF8 Code = "document.invalid-utf8"
	// CodeSyntax marks a document that does not parse.
	CodeSyntax Code = "document.syntax"
	// CodeMultipleDocuments marks a stream with more than one document.
	CodeMultipleDocuments Code = "document.multiple-documents"
	// CodeNull marks an empty or null document. No pack document is null.
	CodeNull Code = "document.null"
	// CodeDuplicateKey marks a mapping with the same key twice.
	CodeDuplicateKey Code = "document.duplicate-key"
	// CodeKeyType marks a mapping key that is not a string.
	CodeKeyType Code = "document.key-type"
	// CodeExplicitTag marks a YAML node with an explicit tag.
	CodeExplicitTag Code = "document.explicit-tag"
	// CodeAmbiguousScalar marks a plain YAML scalar that the Python reader
	// and the Go reader read as different values.
	CodeAmbiguousScalar Code = "document.ambiguous-scalar"
	// CodeNodeLimit marks a document with more nodes than the limit, or with
	// more nodes times aliases than the limit.
	CodeNodeLimit Code = "document.node-limit"
	// CodeAliasLimit marks a YAML document with more aliases than the limit,
	// or with too many nodes that come from aliases for the Go reader.
	CodeAliasLimit Code = "document.alias-limit"
	// CodeAliasCycle marks a YAML alias inside its own anchor, which makes a
	// value that holds itself. JSON has no such value.
	CodeAliasCycle Code = "document.alias-cycle"
	// CodeDepthLimit marks a document nested deeper than the limit.
	CodeDepthLimit Code = "document.depth-limit"
	// CodeNonFinite marks a number that is infinite or not a number. JSON
	// has no such number.
	CodeNonFinite Code = "document.non-finite-number"
)

// An Error is a document that the decoder rejects.
type Error struct {
	// Code is the stable code of the failure.
	Code Code
	// Line is the line of the YAML node of the failure, or 0.
	Line int
}

// Error returns the code, and the line when it is known.
func (e *Error) Error() string {
	if e.Line == 0 {
		return string(e.Code)
	}
	return string(e.Code) + " at line " + strconv.Itoa(e.Line)
}

func fail(code Code, line int) *Error {
	return &Error{Code: code, Line: line}
}
