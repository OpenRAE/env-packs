package a

import "testing"

func TestA(t *testing.T) {
	if A() == "" {
		t.Log("empty")
	}
}
