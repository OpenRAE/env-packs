package testgate

import (
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
)

// errorContract reports whether a mutant only changes a number in a result
// other than the last of a return statement that returns a non-nil error.
// The function of the statement must have the last result type error. Go
// leaves the other results unspecified when the error is not nil, so a test
// that checks them would rely on unspecified behavior.
func errorContract(m mutant, line int) bool {
	if m.Mutator.Name != "numbers/incrementer" && m.Mutator.Name != "numbers/decrementer" {
		return false
	}
	before, _ := errorResult(m.Mutator.Original, line)
	after, ok := errorResult(m.Mutator.Mutated, line)
	return ok && after == before
}

// errorResult returns the text of the last result of the return statement at
// line. It returns false when no such statement returns two or more results
// with a last result other than nil, in a function whose last result has the
// type error.
func errorResult(src string, line int) (string, bool) {
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, "", src, parser.SkipObjectResolution)
	if err != nil {
		return "", false
	}
	result, found := "", false
	ast.Inspect(f, func(n ast.Node) bool {
		var t *ast.FuncType
		var body *ast.BlockStmt
		switch fn := n.(type) {
		case *ast.FuncDecl:
			t, body = fn.Type, fn.Body
		case *ast.FuncLit:
			t, body = fn.Type, fn.Body
		}
		ret := returnAt(fset, body, line)
		if ret == nil || len(ret.Results) < 2 || !lastIsError(t) {
			return true
		}
		last := ret.Results[len(ret.Results)-1]
		if id, ok := last.(*ast.Ident); !ok || id.Name != "nil" {
			result, found = types.ExprString(last), true
		}
		return true
	})
	return result, found
}

// returnAt returns the return statement at line in body, outside the function
// literals of body, or nil. A nil body, such as the body of a node that is
// not a function, has no statement.
func returnAt(fset *token.FileSet, body *ast.BlockStmt, line int) *ast.ReturnStmt {
	var ret *ast.ReturnStmt
	if body == nil {
		return nil
	}
	ast.Inspect(body, func(n ast.Node) bool {
		switch x := n.(type) {
		case *ast.FuncLit:
			return false
		case *ast.ReturnStmt:
			if fset.Position(x.Pos()).Line == line {
				ret = x
			}
		}
		return true
	})
	return ret
}

// lastIsError reports whether the last result of the function type has the
// type name error.
func lastIsError(t *ast.FuncType) bool {
	if t.Results == nil {
		return false
	}
	id, ok := t.Results.List[len(t.Results.List)-1].Type.(*ast.Ident)
	return ok && id.Name == "error"
}
