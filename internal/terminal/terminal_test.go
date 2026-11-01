package terminal

import "testing"

func TestEscape(t *testing.T) {
	tests := map[string]string{
		"":                            "",
		"plain name-1.0":              "plain name-1.0",
		"caf\u00e9 \U0001F600 \u2260": "caf\u00e9 \U0001F600 \u2260",
		"a\x1b[2Jb":                   `a\x1b[2Jb`,
		"line\nnext\r\t":              `line\x0anext\x0d\x09`,
		"\x00\x7f\u0085\u00a0":        `\x00\x7f\x85\xa0`,
		"a\u2028b\u2029c":             `a\u2028b\u2029c`,
		"arabic\u061cmark":            `arabic\u061cmark`,
		"\u200bzero\ufeff":            `\u200bzero\ufeff`,
		"tag\U000e0001":               `tag\ue0001`,
		"\ufffd stays":                "\ufffd stays",
		"bad\xffbyte\xc3":             `bad\udcffbyte\udcc3`,
		"\xed\xa0\x80surrogate":       `\udced\udca0\udc80surrogate`,
	}
	for s, want := range tests {
		if got := Escape(s); got != want {
			t.Errorf("Escape(%q) = %q, want %q", s, got, want)
		}
	}
}
