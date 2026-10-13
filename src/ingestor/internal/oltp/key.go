package oltp

import (
	"regexp"
	"strings"

	"golang.org/x/text/cases"
	"golang.org/x/text/unicode/norm"
)

var (
	trailingParens  = regexp.MustCompile(`\s*\([^)]*\)\s*$`)
	trailingAcronym = regexp.MustCompile(`-[A-Z]{2,}$`)
)

// squeeze reduces every run of spaces and line breaks to one space, which is
// how orgao_alias.nome keeps a name.
func squeeze(name string) string {
	return strings.Join(strings.Fields(name), " ")
}

// Key is the name without what does not change the identity: case, accents,
// repeated spaces and a trailing acronym, in parentheses or after a hyphen
// (ADR 0004, B). Two names with the same key are the same organ.
//
// It has to give what chave() in src/conselhos/identidade.py gives, since both
// write orgao_alias.chave. TestKeyAgreesWithThePythonKey holds it to a file of
// names and keys the Python is held to as well.
func Key(name string) string {
	bare := trailingAcronym.ReplaceAllString(trailingParens.ReplaceAllString(squeeze(name), ""), "")
	// What goes is what Python's unicodedata.combining() says is a combining
	// character: a canonical combining class other than zero. It is not the
	// category Mn: a variation selector is Mn with class zero, and stays.
	var unaccented strings.Builder
	decomposed := norm.NFKD.String(bare)
	for i := 0; i < len(decomposed); {
		properties := norm.NFKD.PropertiesString(decomposed[i:])
		size := properties.Size()
		if properties.CCC() == 0 {
			unaccented.WriteString(decomposed[i : i+size])
		}
		i += size
	}
	return cases.Fold().String(unaccented.String())
}
