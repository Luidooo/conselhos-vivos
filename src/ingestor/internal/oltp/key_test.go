package oltp

import (
	"testing"

	"github.com/stretchr/testify/assert"
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
