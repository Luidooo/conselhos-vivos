package oltp

import (
	"archive/zip"
	"bytes"
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"cloud.google.com/go/civil"
	"github.com/jackc/pgx/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"conselhos-vivos/internal/article"
)

// begin opens a transaction on the compose Postgres that is never committed,
// as tests/db does: the test leaves the database as it found it.
//
// The connection comes from the PG* variables, which the ingestor-db-test
// service sets. Without them the test is skipped, so `go test ./...` stays
// runnable with no database; `make test-db-go` is what runs it.
func begin(t *testing.T) pgx.Tx {
	t.Helper()
	if os.Getenv("PGHOST") == "" {
		t.Skip("no PGHOST: run make test-db-go, with the database up and migrated")
	}

	ctx := context.Background()
	conn, err := pgx.Connect(ctx, "")
	require.NoError(t, err)
	tx, err := conn.Begin(ctx)
	require.NoError(t, err)
	t.Cleanup(func() {
		_ = tx.Rollback(ctx)
		_ = conn.Close(ctx)
	})
	return tx
}

// handmade is a matéria built by hand: the persistence is exercised with no
// zip and no extraction. Its id starts at 900000000, like the built sample, so
// it cannot collide with one from the DOU.
func handmade(id string, category ...string) article.Article {
	return article.Article{
		Entry:    id + ".xml",
		ID:       id,
		PubDate:  civil.Date{Year: 2026, Month: time.October, Day: 2},
		Category: category,
		HTML:     "<p>Matéria construída para teste: não foi publicada.</p>",
	}
}

// builtSample reads testdata/conselho-construido.xml of the article package
// through article.Read, the way a matéria reaches Save in the pipeline.
func builtSample(t *testing.T) article.Article {
	t.Helper()
	const name = "conselho-construido.xml"

	contents, err := os.ReadFile(filepath.Join("..", "article", "testdata", name))
	require.NoError(t, err)

	var buffer bytes.Buffer
	writer := zip.NewWriter(&buffer)
	file, err := writer.Create(name)
	require.NoError(t, err)
	_, err = file.Write(contents)
	require.NoError(t, err)
	require.NoError(t, writer.Close())

	edition, err := zip.NewReader(bytes.NewReader(buffer.Bytes()), int64(buffer.Len()))
	require.NoError(t, err)
	for item, err := range article.Read(edition) {
		require.NoError(t, err)
		return item
	}
	t.Fatal("the sample edition is empty")
	return article.Article{}
}

// newOrgan inserts an organ with one current name and returns its id.
func newOrgan(t *testing.T, tx pgx.Tx, name string) int32 {
	t.Helper()
	ctx := context.Background()

	var id int32
	require.NoError(t, tx.QueryRow(ctx, `INSERT INTO orgao DEFAULT VALUES RETURNING id`).Scan(&id))
	_, err := tx.Exec(ctx, `INSERT INTO orgao_nome (orgao_id, nome) VALUES ($1, $2)`, id, name)
	require.NoError(t, err)
	return id
}

func count(t *testing.T, tx pgx.Tx, sql string, args ...any) int {
	t.Helper()
	var n int
	require.NoError(t, tx.QueryRow(context.Background(), sql, args...).Scan(&n))
	return n
}

func TestSaveWritesAMateriaOfAKnownConselho(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	item := builtSample(t)

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	outcome, err := writer.Save(ctx, item)
	require.NoError(t, err)
	assert.Equal(t, Saved, outcome)

	var (
		origem, organ, conteudo string
		versao                  int
		published               time.Time
		ementa                  *string
	)
	// The CONAMA is one of the 5 conselhos of sql/004, so it is there with the
	// migrations alone.
	require.NoError(t, tx.QueryRow(ctx, `
		SELECT a.origem, a.versao, a.data_publicacao, a.ementa, a.conteudo, n.nome
		  FROM ato a JOIN orgao_nome n ON n.orgao_id = a.orgao_id AND n.data_fim IS NULL
		 WHERE a.id_dou = $1`, "900000001").
		Scan(&origem, &versao, &published, &ementa, &conteudo, &organ))

	assert.Equal(t, "DOU", origem)
	assert.Equal(t, 1, versao)
	assert.Equal(t, "2026-10-02", published.Format(time.DateOnly))
	assert.Equal(t, "Conselho Nacional do Meio Ambiente", organ)
	require.NotNil(t, ementa)
	assert.Equal(t, "Matéria construída para teste: não foi publicada.", *ementa)
	// <Texto> as published, markers and all: the plain text is derived from it.
	assert.Equal(t, item.HTML, conteudo)
	assert.Contains(t, conteudo, `<p class="assina">`)
}

func TestSaveLeavesAnEmptyEmentaNull(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	newOrgan(t, tx, "Conselho Nacional de Teste da Persistência")

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	outcome, err := writer.Save(ctx, handmade("900000010", "Ministério de Teste", "Conselho Nacional de Teste da Persistência"))
	require.NoError(t, err)
	assert.Equal(t, Saved, outcome)

	assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = '900000010' AND ementa IS NULL`))
}

func TestSaveFindsTheOrgan(t *testing.T) {
	const published = "CONSELHO  NACIONAL DE TESTE DA PERSISTÊNCIA (CNTP)"

	cases := []struct {
		name  string
		setup func(t *testing.T, tx pgx.Tx) int32
	}{
		{"by its current name, whatever the spelling", func(t *testing.T, tx pgx.Tx) int32 {
			return newOrgan(t, tx, "Conselho Nacional de Teste da Persistência")
		}},
		{"by a name it had before", func(t *testing.T, tx pgx.Tx) int32 {
			id := newOrgan(t, tx, "Conselho Nacional de Outro Nome")
			_, err := tx.Exec(context.Background(), `
				INSERT INTO orgao_nome (orgao_id, nome, data_inicio, data_fim)
				VALUES ($1, 'Conselho Nacional de Teste da Persistência', '2000-01-01', '2010-01-01')`, id)
			require.NoError(t, err)
			return id
		}},
		{"by a resolved alias", func(t *testing.T, tx pgx.Tx) int32 {
			id := newOrgan(t, tx, "Conselho Nacional de Outro Nome")
			_, err := tx.Exec(context.Background(), `
				INSERT INTO orgao_alias (nome, chave, fonte, orgao_id, status)
				VALUES ('Conselho Nacional de Teste da Persistencia', 'x', 'PLANILHA', $1, 'RESOLVIDO')`, id)
			require.NoError(t, err)
			return id
		}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			tx := begin(t)
			ctx := context.Background()
			want := c.setup(t, tx)

			writer, err := Open(ctx, tx)
			require.NoError(t, err)
			outcome, err := writer.Save(ctx, handmade("900000011", "Ministério de Teste", published))
			require.NoError(t, err)
			require.Equal(t, Saved, outcome)

			var got int32
			require.NoError(t, tx.QueryRow(ctx, `SELECT orgao_id FROM ato WHERE id_dou = '900000011'`).Scan(&got))
			assert.Equal(t, want, got)
		})
	}
}

func TestSaveQueuesAnUnknownOrgan(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	const organ = "Coordenação de Teste Que Não Existe"

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	atos := count(t, tx, `SELECT count(*) FROM ato`)

	// Two matérias of the same organ, the second with the name spaced apart.
	for id, name := range map[string]string{"900000020": organ, "900000021": "Coordenação de Teste  Que Não Existe"} {
		outcome, err := writer.Save(ctx, handmade(id, "Ministério de Teste", name))
		require.NoError(t, err)
		assert.Equal(t, UnknownOrgan, outcome)
	}

	assert.Equal(t, atos, count(t, tx, `SELECT count(*) FROM ato`), "nothing goes into ato")

	var (
		key, status, reason string
		organID             *int32
	)
	// One row for the two: Scan fails on more than one.
	require.NoError(t, tx.QueryRow(ctx, `
		SELECT chave, status, motivo, orgao_id FROM orgao_alias WHERE fonte = 'DOU' AND nome = $1`, organ).
		Scan(&key, &status, &reason, &organID))
	assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM orgao_alias WHERE fonte = 'DOU' AND chave = $1`, key))
	assert.Equal(t, Key(organ), key)
	assert.Equal(t, "INDEFINIDO", status)
	assert.Nil(t, organID)
	assert.Contains(t, reason, "Ministério de Teste/"+organ)
}

func TestSaveDoesNotChooseBetweenTwoOrgans(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	newOrgan(t, tx, "Conselho de Teste Repetido")
	newOrgan(t, tx, "CONSELHO DE TESTE REPETIDO (CTR)")

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	outcome, err := writer.Save(ctx, handmade("900000030", "Ministério de Teste", "Conselho de Teste Repetido"))
	require.NoError(t, err)
	assert.Equal(t, UnknownOrgan, outcome)

	assert.Equal(t, 0, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = '900000030'`))
	assert.Equal(t, 1, count(t, tx, `
		SELECT count(*) FROM orgao_alias
		 WHERE fonte = 'DOU' AND nome = 'Conselho de Teste Repetido' AND status = 'AMBIGUO' AND orgao_id IS NULL`))
}

func TestSaveRefusesAMateriaWithNoContent(t *testing.T) {
	item := handmade("900000040", "Ministério de Teste", "Conselho de Teste")
	item.HTML = " \n"

	// No database: it is refused before anything is asked of one.
	_, err := (&Writer{}).Save(context.Background(), item)
	assert.ErrorIs(t, err, ErrNoContent)
}

// Key and chave() of src/conselhos both write orgao_alias.chave. Every alias
// the Python loaded has to get the same key here.
func TestKeyAgreesWithTheLoadedAliases(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()

	rows, err := tx.Query(ctx, `SELECT nome, chave FROM orgao_alias WHERE fonte = 'PLANILHA'`)
	require.NoError(t, err)
	defer rows.Close()

	checked := 0
	for rows.Next() {
		var name, key string
		require.NoError(t, rows.Scan(&name, &key))
		assert.Equal(t, key, Key(name), name)
		checked++
	}
	require.NoError(t, rows.Err())
	if checked == 0 {
		t.Skip("no alias of the spreadsheet in the database: run make carga")
	}
}
