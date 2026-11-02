package packfs

import "testing"

func TestAdmitMembers(t *testing.T) {
	tests := []struct {
		name    string
		members []string
		want    Reason
	}{
		{name: "no member"},
		{name: "pack files", members: []string{"pack.yaml", "docs/raes-trust.yaml.md", "raes-trust.yml"}},
		{name: "scenario content with secret-like names", members: []string{".env", "keys/id_rsa", "tls/server.pem"}},
		{name: "trust policy", members: []string{"pack.yaml", "raes-trust.yaml"}, want: ReasonTrustPolicy},
		{name: "nested trust policy in another case", members: []string{"policy/RAES-Trust.YAML"}, want: ReasonTrustPolicy},
	}
	for _, tt := range tests {
		err := AdmitMembers(tt.members)
		if reasonOf(err) != tt.want {
			t.Errorf("AdmitMembers(%q) error = %v, want reason %q", tt.members, err, tt.want)
		}
	}
	err := AdmitMembers([]string{"raes-trust.yaml"})
	if err == nil || err.Error() != "operator files are not admitted to local authoring" {
		t.Errorf("AdmitMembers() error = %v, want the message of the Python implementation", err)
	}
}
