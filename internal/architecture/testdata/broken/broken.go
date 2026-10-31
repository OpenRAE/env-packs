// Package broken does not compile.
package broken

// Value uses a missing name.
func Value() int { return missing }
