//go:build !linux

package packfs

// Renameat2 fails: only Linux has renameat2.
func (unixSystem) Renameat2(string, string, uint) error {
	return errUnsupported
}
