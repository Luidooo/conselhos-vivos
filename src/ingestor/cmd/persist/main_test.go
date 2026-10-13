package main

import (
	"archive/zip"
	"context"
	"io"
	"log/slog"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"conselhos-vivos/internal/dbtest"
)

func sample(t *testing.T, name string) string {
	t.Helper()
	contents, err := os.ReadFile(filepath.Join("..", "..", "internal", "article", "testdata", name))
	require.NoError(t, err)
	return string(contents)
}

// writeEdition puts a zip on disk with the given entries, the way fetch leaves
// one. They go in by name, so a test knows which comes first.
func writeEdition(t *testing.T, entries map[string]string) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), "2026-10-02-DO1.zip")
	file, err := os.Create(path)
	require.NoError(t, err)
	defer file.Close()

	writer := zip.NewWriter(file)
	for _, name := range slices.Sorted(maps.Keys(entries)) {
		contents := entries[name]
		entry, err := writer.Create(name)
		require.NoError(t, err)
		_, err = io.WriteString(entry, contents)
		require.NoError(t, err)
	}
	require.NoError(t, writer.Close())
	return path
}

// anEdition is a day in small: a matéria of a known conselho, a real one of an
// organ that is not a conselho, a broken XML and an image.
func anEdition(t *testing.T) map[string]string {
	t.Helper()
	return map[string]string{
		"conselho-construido.xml":   sample(t, "conselho-construido.xml"),
		"515_20190507_11615606.xml": sample(t, "515_20190507_11615606.xml"),
		"malformado.xml":            sample(t, "malformado.xml"),
		"figura.jpg":                "not an article",
	}
}

func quiet() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

// state is everything persist can write, row by row and in order, so two of
// them are compared as text: by count and by diff, not by eye. The row ids and
// criado_em are in it on purpose: a row rewritten in place would change them.
func state(t *testing.T, tx pgx.Tx) []string {
	t.Helper()

	rows, err := tx.Query(context.Background(), `
		SELECT 'ato ' || row_to_json(a)::text FROM ato a
		UNION ALL
		SELECT 'orgao_alias ' || row_to_json(o)::text FROM orgao_alias o
		ORDER BY 1`)
	require.NoError(t, err)
	lines, err := pgx.CollectRows(rows, pgx.RowTo[string])
	require.NoError(t, err)
	return lines
}

func TestPersistSavesTheEdition(t *testing.T) {
	tx := dbtest.Begin(t)
	before := state(t, tx)

	// The organ that is not a conselho may be queued already: a real ingestion
	// into this database (make ingest-mensal) meets it too, and the queue takes a
	// name once.
	const organ = "Coordenação-Geral de Controle de Serviços e Produtos"
	var queuedBefore bool
	require.NoError(t, tx.QueryRow(context.Background(),
		`SELECT EXISTS (SELECT 1 FROM orgao_alias WHERE nome = $1)`, organ).Scan(&queuedBefore))

	summary, err := persist(context.Background(), tx, quiet(), writeEdition(t, anEdition(t)))
	require.NoError(t, err)

	assert.Equal(t, Summary{Saved: 1, UnknownOrgan: 1, Skipped: 1, Failed: 1}, summary)
	// One row in ato, for the conselho, and one in orgao_alias, for the organ
	// that is not one, unless it was in the queue already.
	added := 2
	if queuedBefore {
		added = 1
	}
	assert.Len(t, state(t, tx), len(before)+added)
}

// The acceptance of issue #24: the same day twice leaves the database
// identical.
func TestPersistTwiceLeavesTheDatabaseIdentical(t *testing.T) {
	tx := dbtest.Begin(t)
	ctx := context.Background()
	path := writeEdition(t, anEdition(t))

	_, err := persist(ctx, tx, quiet(), path)
	require.NoError(t, err)
	afterFirst := state(t, tx)

	summary, err := persist(ctx, tx, quiet(), path)
	require.NoError(t, err)

	assert.Equal(t, Summary{Unchanged: 1, UnknownOrgan: 1, Skipped: 1, Failed: 1}, summary)
	assert.Equal(t, afterFirst, state(t, tx))
}

func TestPersistKeepsARepublishedEditionAsNewVersions(t *testing.T) {
	tx := dbtest.Begin(t)
	ctx := context.Background()

	_, err := persist(ctx, tx, quiet(), writeEdition(t, anEdition(t)))
	require.NoError(t, err)
	afterFirst := state(t, tx)

	republished := anEdition(t)
	republished["conselho-construido.xml"] = strings.Replace(republished["conselho-construido.xml"],
		"30 dias", "60 dias", 1)
	summary, err := persist(ctx, tx, quiet(), writeEdition(t, republished))
	require.NoError(t, err)

	assert.Equal(t, Summary{NewVersions: 1, UnknownOrgan: 1, Skipped: 1, Failed: 1}, summary)

	after := state(t, tx)
	require.Len(t, after, len(afterFirst)+1)
	assert.Subset(t, after, afterFirst, "every row of the first run is still there, untouched")

	var versions string
	require.NoError(t, tx.QueryRow(ctx, `
		SELECT string_agg(versao || ':' || (conteudo LIKE '%60 dias%'), ',' ORDER BY versao)
		  FROM ato WHERE id_dou = '900000001'`).Scan(&versions))
	assert.Equal(t, "1:false,2:true", versions)
}

// The same id twice in a zip, saying different things: the first is the
// matéria, the other is left out, and the rest of the zip goes on. Run again,
// nothing is written — saving both would add two versions on every run.
func TestPersistSavesOnlyTheFirstOfARepeatedID(t *testing.T) {
	tx := dbtest.Begin(t)
	ctx := context.Background()

	edition := anEdition(t)
	edition["repetida.xml"] = strings.Replace(edition["conselho-construido.xml"], "30 dias", "60 dias", 1)
	path := writeEdition(t, edition)

	summary, err := persist(ctx, tx, quiet(), path)
	require.NoError(t, err)
	assert.Equal(t, Summary{Saved: 1, UnknownOrgan: 1, Repeated: 1, Skipped: 1, Failed: 1}, summary)
	afterFirst := state(t, tx)

	var versions string
	require.NoError(t, tx.QueryRow(ctx, `
		SELECT string_agg(versao || ':' || (conteudo LIKE '%30 dias%'), ',' ORDER BY versao)
		  FROM ato WHERE id_dou = '900000001'`).Scan(&versions))
	assert.Equal(t, "1:true", versions, "the entry that comes first in the zip is the one saved")

	summary, err = persist(ctx, tx, quiet(), path)
	require.NoError(t, err)
	assert.Equal(t, Summary{Unchanged: 1, UnknownOrgan: 1, Repeated: 1, Skipped: 1, Failed: 1}, summary)
	assert.Equal(t, afterFirst, state(t, tx))
}

// Late data: the edition of a day already saved comes back with a matéria it
// did not have. Running that day again takes the new one and leaves the rest
// alone, and the new one is filed under the day it was published, not the day
// it arrived.
func TestPersistTakesAMateriaThatArrivedLate(t *testing.T) {
	tx := dbtest.Begin(t)
	ctx := context.Background()

	_, err := persist(ctx, tx, quiet(), writeEdition(t, anEdition(t)))
	require.NoError(t, err)
	afterFirst := state(t, tx)

	later := anEdition(t)
	later["conselho-atrasada.xml"] = strings.Replace(later["conselho-construido.xml"],
		`id="900000001"`, `id="900000777"`, 1)
	require.NotEqual(t, later["conselho-construido.xml"], later["conselho-atrasada.xml"])

	summary, err := persist(ctx, tx, quiet(), writeEdition(t, later))
	require.NoError(t, err)
	assert.Equal(t, Summary{Saved: 1, Unchanged: 1, UnknownOrgan: 1, Skipped: 1, Failed: 1}, summary)

	after := state(t, tx)
	require.Len(t, after, len(afterFirst)+1)
	assert.Subset(t, after, afterFirst, "what was there is untouched")

	var published string
	require.NoError(t, tx.QueryRow(ctx,
		`SELECT data_publicacao::text FROM ato WHERE id_dou = '900000777'`).Scan(&published))
	assert.Equal(t, "2026-10-02", published)
}

// A zip that does not open is not a bad entry: there is nothing to go on with.
// It is refused before the database is asked anything.
func TestPersistStopsOnAZipThatDoesNotOpen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "login.zip")
	require.NoError(t, os.WriteFile(path, []byte("<html>faca login</html>"), 0o644))

	_, err := persist(context.Background(), nil, quiet(), path)

	require.Error(t, err)
	assert.Contains(t, err.Error(), path)
}
