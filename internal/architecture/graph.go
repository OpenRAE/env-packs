package architecture

// A Graph is the Go code of the module, as the checks see it.
type Graph struct {
	// Module is the path of the module.
	Module string
	// Packages are the packages of the module, each with its test files.
	Packages []Package
}

// A Package is one package of the module.
type Package struct {
	// Path is the import path. The files of an external test package belong
	// to the package that they test.
	Path string
	// Dir is the directory of the package, relative to the module root.
	Dir string
	// Main reports whether the package is a main package.
	Main bool
	// Files are the Go files of the package, with its test files.
	Files []File
}

// A File is one Go file of a package.
type File struct {
	// Name is the path of the file, relative to the module root, with
	// forward slashes.
	Name string
	// Test reports whether the file is a test file.
	Test bool
	// Imports are the import declarations of the file.
	Imports []Import
	// Symbols are the uses of symbols from other packages.
	Symbols []Symbol
}

// An Import is one import declaration of a file.
type Import struct {
	// Path is the import path.
	Path string
	// Module is the path of the module of the imported package. It is empty
	// for a package of the standard library.
	Module string
	// Line is the line of the declaration.
	Line int
}

// A Symbol is one use of a package-level function or variable of another
// package, or of a builtin function.
type Symbol struct {
	// Name is "importpath.Name", or the name of a builtin function.
	Name string
	// Line is the line of the use.
	Line int
}
