package packfs

import (
	"path"

	"golang.org/x/text/cases"
)

// trustPolicy is the name of the RAES trust policy file, after case folding.
const trustPolicy = "raes-trust.yaml"

// AdmitMembers checks the member paths of an authoring input before a read.
// It fails with ReasonTrustPolicy when a member is a RAES trust policy file,
// raes-trust.yaml in any letter case. Thus the RAES resolver keeps its empty
// registry policy and refuses remote imports. AdmitMembers does not open a
// member.
func AdmitMembers(members []string) error {
	fold := cases.Fold()
	for _, m := range members {
		if fold.String(path.Base(m)) == trustPolicy {
			return fail(ReasonTrustPolicy, "operator files are not admitted to local authoring", nil)
		}
	}
	return nil
}
