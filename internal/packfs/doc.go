// Package packfs reads and writes pack trees through descriptor-anchored,
// no-follow, bounded operations, and it commits staged trees atomically
// (design 0004). It is the only library package that opens pack content.
//
// Each operation returns an [*Error] with a stable [Reason]. The message of
// an error is the message of the Python implementation.
package packfs
