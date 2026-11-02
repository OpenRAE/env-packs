package packfs

// A Reason is the stable code of an [Error].
type Reason string

// The reasons of the errors.
const (
	// ReasonRootEmpty marks an empty pack root path.
	ReasonRootEmpty Reason = "root-empty"
	// ReasonRootSymlink marks a pack root that is a symlink.
	ReasonRootSymlink Reason = "root-symlink"
	// ReasonRootInaccessible marks a pack root that is not an accessible
	// directory.
	ReasonRootInaccessible Reason = "root-inaccessible"
	// ReasonPathNotCanonical marks a member path that is empty, absolute, or
	// has a backslash.
	ReasonPathNotCanonical Reason = "path-not-canonical"
	// ReasonNameNotCanonical marks a name that is empty, ".", "..", not NFC,
	// or has a slash or a backslash.
	ReasonNameNotCanonical Reason = "name-not-canonical"
	// ReasonNameNotUTF8 marks a name that is not valid UTF-8.
	ReasonNameNotUTF8 Reason = "name-not-utf8"
	// ReasonMemberBudget marks a tree with more directory entries than the
	// budget.
	ReasonMemberBudget Reason = "member-budget"
	// ReasonUntraversable marks a directory whose entries cannot be read.
	ReasonUntraversable Reason = "directory-not-traversable"
	// ReasonCaseCollision marks two paths that are equal after case folding.
	ReasonCaseCollision Reason = "case-collision"
	// ReasonUninspectable marks a member that cannot be inspected.
	ReasonUninspectable Reason = "member-not-inspectable"
	// ReasonDirectoryUnopenable marks a directory that cannot be opened.
	ReasonDirectoryUnopenable Reason = "directory-not-openable"
	// ReasonSymlink marks a symlink in a tree.
	ReasonSymlink Reason = "symlink"
	// ReasonSpecialFile marks a member that is not a directory or a regular
	// file.
	ReasonSpecialFile Reason = "special-file"
	// ReasonHardlink marks a regular file with more than one link.
	ReasonHardlink Reason = "hardlink"
	// ReasonMemberUnopenable marks a member that cannot be opened.
	ReasonMemberUnopenable Reason = "member-not-openable"
	// ReasonNotSingleRegular marks an opened member that is not a regular
	// file with one link.
	ReasonNotSingleRegular Reason = "not-single-regular-file"
	// ReasonByteBudget marks a member with more bytes than the budget.
	ReasonByteBudget Reason = "byte-budget"
	// ReasonUnreadable marks a member whose bytes cannot be read.
	ReasonUnreadable Reason = "member-not-readable"
	// ReasonWriteFailed marks a staged member that cannot be written.
	ReasonWriteFailed Reason = "write-failed"
	// ReasonTargetExists marks a create-only publish to an existing target.
	ReasonTargetExists Reason = "target-exists"
	// ReasonPublishFailed marks a publish that failed for another reason.
	ReasonPublishFailed Reason = "publish-failed"
	// ReasonExchangeFailed marks an exchange that failed.
	ReasonExchangeFailed Reason = "exchange-failed"
	// ReasonRecovery marks a replacement whose rollback failed. The original
	// tree is at the path of the error.
	ReasonRecovery Reason = "recovery"
	// ReasonUnsupportedPlatform marks a transaction on a platform without
	// renameat2.
	ReasonUnsupportedPlatform Reason = "unsupported-platform"
	// ReasonTrustPolicy marks an authoring input with a RAES trust policy
	// file.
	ReasonTrustPolicy Reason = "trust-policy"
)

// An Error is a failure of the pack filesystem boundary.
type Error struct {
	// Reason is the stable code of the failure.
	Reason Reason
	// Path keeps the original tree after a failed rollback, for the reason
	// ReasonRecovery. It is empty for the other reasons.
	Path string
	msg  string
	err  error
}

// Error returns the message of the failure.
func (e *Error) Error() string {
	return e.msg
}

// Unwrap returns the cause of the failure, or nil.
func (e *Error) Unwrap() error {
	return e.err
}

// fail returns an error with a reason, a message, and an optional cause.
func fail(reason Reason, msg string, cause error) *Error {
	return &Error{Reason: reason, msg: msg, err: cause}
}
