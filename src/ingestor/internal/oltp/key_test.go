package oltp

import (
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// The cases of tests/conselhos/test_conselhos.py, so the two keys are held to
// the same examples.
func TestKey(t *testing.T) {
	same := []struct{ name, a, b string }{
		{"case, accent and acronym in parentheses",
			"CONSELHO NACIONAL DE ASSISTÊNCIA SOCIAL",
			"Conselho Nacional de Assistência Social (CNAS)"},
		{"line break and doubled space",
			"Conselho Nacional de Política \nCriminal e  Penitenciária (CNPCP)",
			"Conselho Nacional de Política Criminal e Penitenciária"},
		{"acronym after a hyphen",
			"CONSELHO NACIONAL DAS ZONAS DE PROCESSAMENTO DE EXPORTAÇÃO-CZPE",
			"Conselho Nacional das Zonas de Processamento de Exportação"},
	}
	for _, c := range same {
		t.Run(c.name, func(t *testing.T) {
			assert.Equal(t, Key(c.a), Key(c.b))
		})
	}

	t.Run("it is the name folded, not a hash", func(t *testing.T) {
		assert.Equal(t, "conselho nacional de assistencia social", Key("Conselho Nacional de  Assistência Social (CNAS)"))
	})

	// The key does not guess: "de Meio Ambiente" only reaches the CONAMA
	// through a recorded decision.
	t.Run("de and do are not the same key", func(t *testing.T) {
		assert.NotEqual(t, Key("Conselho Nacional de Meio Ambiente"), Key("Conselho Nacional do Meio Ambiente"))
	})
}

// testdata/chaves.tsv has a name and the key chave() gives it, one pair per
// line: every name of orgao_nome and of the spreadsheet's aliases, and a few
// made to pull the two languages apart. tests/conselhos holds the Python to the
// same file, so the two cannot drift without one of the suites failing.
func TestKeyAgreesWithThePythonKey(t *testing.T) {
	contents, err := os.ReadFile("testdata/chaves.tsv")
	require.NoError(t, err)

	lines := strings.Split(strings.TrimRight(string(contents), "\n"), "\n")
	require.Greater(t, len(lines), 150, "the file lost its names")
	for _, line := range lines {
		name, key, found := strings.Cut(line, "\t")
		require.True(t, found, line)
		assert.Equal(t, key, Key(name), name)
	}
}
