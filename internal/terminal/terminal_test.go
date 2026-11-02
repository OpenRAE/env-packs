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

func TestQuote(t *testing.T) {
	// The values are those of repr in Python.
	tests := map[string]string{
		"":                          "''",
		"plain":                     "'plain'",
		"it's":                      "\"it's\"",
		"say \"hi\"":                "'say \"hi\"'",
		"both ' and \"":             "'both \\' and \"'",
		"back\\slash":               "'back\\\\slash'",
		"tab\u0009nl\u000acr\u000d": "'tab\\tnl\\ncr\\r'",
		"esc\u001b del\u007f":       "'esc\\x1b del\\x7f'",
		"nel\u0085 nbsp\u00a0":      "'nel\\x85 nbsp\\xa0'",
		"ar\u061cmark":              "'ar\\u061cmark'",
		"tag\U000e0001":             "'tag\\U000e0001'",
		"caf\u00e9 \U0001f600":      "'caf\u00e9 \U0001f600'",
		"bad\xffbyte":               `'bad\udcffbyte'`,
		"\ufffd\x01":                "'\ufffd\\x01'",
	}
	for s, want := range tests {
		if got := Quote(s); got != want {
			t.Errorf("Quote(%q) = %q, want %q", s, got, want)
		}
	}
}
