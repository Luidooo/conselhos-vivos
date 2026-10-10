package main

import (
	"archive/zip"
	"bufio"
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// writeEdition puts a zip on disk, with the article package's samples and any
// extra entries, the way fetch leaves one.
func writeEdition(t *testing.T, samples []string, extra map[string]string) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), "2026-10-02-DO1.zip")
	file, err := os.Create(path)
	require.NoError(t, err)
	defer file.Close()

	writer := zip.NewWriter(file)
	for _, name := range samples {
		contents, err := os.ReadFile(filepath.Join("..", "..", "internal", "article", "testdata", name))
		require.NoError(t, err)
		entry, err := writer.Create(name)
		require.NoError(t, err)
		_, err = entry.Write(contents)
		require.NoError(t, err)
	}
	for name, contents := range extra {
		entry, err := writer.Create(name)
		require.NoError(t, err)
		_, err = io.WriteString(entry, contents)
		require.NoError(t, err)
	}
	require.NoError(t, writer.Close())

	return path
}

func quiet() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

func lines(t *testing.T, out *bytes.Buffer) []map[string]any {
	t.Helper()

	var decoded []map[string]any
	scanner := bufio.NewScanner(out)
	scanner.Buffer(nil, 1<<20)
	for scanner.Scan() {
		var line map[string]any
		require.NoError(t, json.Unmarshal(scanner.Bytes(), &line))
		decoded = append(decoded, line)
	}
	require.NoError(t, scanner.Err())
	return decoded
}

func TestExtractPrintsOneLinePerArticle(t *testing.T) {
	path := writeEdition(t,
		[]string{"515_20190507_11615606.xml", "malformado.xml", "conselho-construido.xml"},
		map[string]string{"figura.jpg": "not an article"})

	var out bytes.Buffer
	summary, err := extract(&out, quiet(), path, false)
	require.NoError(t, err)

	assert.Equal(t, Summary{Read: 2, Skipped: 1, Failed: 1}, summary)

	printed := lines(t, &out)
	require.Len(t, printed, 2)
	assert.Equal(t, "8724946", printed[0]["id"])
	assert.Equal(t, "2019-05-07", printed[0]["pubDate"])
	assert.NotContains(t, printed[0], "html", "the HTML is left out unless asked for")
	assert.Equal(t, []any{"Ministério do Meio Ambiente e Mudança do Clima", "Conselho Nacional do Meio Ambiente"},
		printed[1]["artCategory"])
}

func TestExtractPrintsTheHTMLWhenAsked(t *testing.T) {
	path := writeEdition(t, []string{"conselho-construido.xml"}, nil)

	var out bytes.Buffer
	_, err := extract(&out, quiet(), path, true)
	require.NoError(t, err)

	printed := lines(t, &out)
	require.Len(t, printed, 1)
	assert.Contains(t, printed[0]["html"], `<p class="assina">FULANO DE TAL</p>`, "printed as is, not escaped")
}

// A zip that does not open is not a bad entry: there is nothing to go on with.
func TestExtractStopsOnAZipThatDoesNotOpen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "login.zip")
	require.NoError(t, os.WriteFile(path, []byte("<html>faca login</html>"), 0o644))

	_, err := extract(io.Discard, quiet(), path, false)

	require.Error(t, err)
	assert.Contains(t, err.Error(), path)
}
