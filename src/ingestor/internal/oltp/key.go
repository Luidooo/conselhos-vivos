package oltp

import (
	"regexp"
	"strings"
	"unicode"

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
// write orgao_alias.chave. TestKeyAgreesWithTheLoadedAliases checks it against
// every alias the Python loaded.
func Key(name string) string {
	bare := trailingAcronym.ReplaceAllString(trailingParens.ReplaceAllString(squeeze(name), ""), "")
	unaccented := strings.Map(func(r rune) rune {
		if unicode.Is(unicode.Mn, r) {
			return -1
		}
		return r
	}, norm.NFKD.String(bare))
	return cases.Fold().String(unaccented)
}
