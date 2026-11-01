// Package terminal escapes labels from packs, file names, and arguments for a
// terminal (design 0006).
package terminal

import (
	"strconv"
	"strings"
	"unicode"
	"unicode/utf8"
)

// Escape returns s in a form that is safe to write to a terminal, as
// check._terminal_safe of the Python code does. A character that is not
// printable becomes \xNN below U+0100 and \uNNNN above. A byte that is not
// valid UTF-8 becomes \udcNN, the form that Python gives to such a byte in a
// file name or an argument. So a control sequence cannot move the cursor,
// erase the screen, or spoof a line of a report.
func Escape(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); {
		r, size := utf8.DecodeRuneInString(s[i:])
		switch {
		case r == utf8.RuneError && size == 1:
			// Each byte that is not valid UTF-8 is at least 0x80, so it has
			// two digits.
			b.WriteString(`\udc` + strconv.FormatUint(uint64(s[i]), 16))
		case unicode.IsPrint(r):
			b.WriteString(s[i : i+size])
		case r < 0x100:
			b.WriteString(`\x` + hex(r, 2))
		default:
			b.WriteString(`\u` + hex(r, 4))
		}
		i += size
	}
	return b.String()
}

// hex returns r in lower-case hexadecimal, with at least width digits.
func hex(r rune, width int) string {
	digits := strconv.FormatInt(int64(r), 16)
	return strings.Repeat("0", max(0, width-len(digits))) + digits
}
