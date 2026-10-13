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
	"conselhos-vivos/internal/dbtest"
)

func begin(t *testing.T) pgx.Tx { return dbtest.Begin(t) }

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

// An <Ementa> with only spaces or line breaks is as empty as no <Ementa>: the
// same rule <Texto> follows (TrimSpace) before ErrNoContent.
func TestSaveLeavesABlankEmentaNull(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	newOrgan(t, tx, "Conselho Nacional de Teste da Persistência")

	item := handmade("900000012", "Ministério de Teste", "Conselho Nacional de Teste da Persistência")
	item.Ementa = " \n\t "

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	outcome, err := writer.Save(ctx, item)
	require.NoError(t, err)
	assert.Equal(t, Saved, outcome)

	assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = '900000012' AND ementa IS NULL`))
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
	for _, m := range []struct{ id, name string }{
		{"900000020", organ},
		{"900000021", "Coordenação de Teste  Que Não Existe"},
	} {
		outcome, err := writer.Save(ctx, handmade(m.id, "Ministério de Teste", m.name))
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

// A name the spreadsheet left waiting for a decision comes up in the DOU: it
// is still left out of ato, and the decision that is waiting stays the only
// one, with its own status and reason.
func TestSaveLeavesANameAlreadyWaitingAlone(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	const waiting = "Conselho de Teste à Espera de Decisão"
	_, err := tx.Exec(ctx, `
		INSERT INTO orgao_alias (nome, chave, fonte, status, motivo)
		VALUES ($1, $2, 'PLANILHA', 'AMBIGUO', 'dois conselhos possíveis: perguntar à pesquisadora')`,
		waiting, Key(waiting))
	require.NoError(t, err)

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	atos := count(t, tx, `SELECT count(*) FROM ato`)

	outcome, err := writer.Save(ctx, handmade("900000030", "Ministério de Teste", "CONSELHO DE TESTE À ESPERA DE DECISÃO (CTED)"))
	require.NoError(t, err)
	assert.Equal(t, UnknownOrgan, outcome)

	assert.Equal(t, atos, count(t, tx, `SELECT count(*) FROM ato`), "nothing goes into ato")
	assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM orgao_alias WHERE chave = $1`, Key(waiting)),
		"no second row beside the spreadsheet's")
	assert.Equal(t, 1, count(t, tx, `
		SELECT count(*) FROM orgao_alias WHERE chave = $1 AND fonte = 'PLANILHA' AND status = 'AMBIGUO'`, Key(waiting)))
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

func TestSaveAgainWritesNothing(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	item := builtSample(t)

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	first, err := writer.Save(ctx, item)
	require.NoError(t, err)
	require.Equal(t, Saved, first)

	again, err := writer.Save(ctx, item)
	require.NoError(t, err)
	assert.Equal(t, Unchanged, again)
	assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = $1`, item.ID))
}

// The same id with two texts, coming from two zips (the DO1 and the DO1E of a
// day, or two days of the reprocessing window): once both are in, running again
// writes nothing. Comparing with the latest version only would swap between the
// two and add two versions on every run.
func TestSaveDoesNotSwapBetweenTwoKnownVersions(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	a := builtSample(t)
	b := a
	b.HTML += "<p>Texto da outra edição.</p>"

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	for i, want := range []Outcome{Saved, NewVersion, Unchanged, Unchanged} {
		item := a
		if i%2 == 1 {
			item = b
		}
		outcome, err := writer.Save(ctx, item)
		require.NoError(t, err)
		assert.Equal(t, want, outcome, "save %d", i+1)
	}
	assert.Equal(t, 2, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = $1`, a.ID))
}

// The organ is the identity decision (ADR 0004), not something the DOU
// published: resolving a name to another organ is not a republication.
func TestSaveDoesNotVersionAChangeOfOrgan(t *testing.T) {
	tx := begin(t)
	ctx := context.Background()
	const name = "Conselho Nacional de Teste da Persistência"
	first := newOrgan(t, tx, name)
	item := handmade("900000050", "Ministério de Teste", name)

	writer, err := Open(ctx, tx)
	require.NoError(t, err)
	outcome, err := writer.Save(ctx, item)
	require.NoError(t, err)
	require.Equal(t, Saved, outcome)

	// The name now belongs to another organ.
	_, err = tx.Exec(ctx, `UPDATE orgao_nome SET nome = 'Conselho de Outro Nome' WHERE orgao_id = $1`, first)
	require.NoError(t, err)
	newOrgan(t, tx, name)

	writer, err = Open(ctx, tx)
	require.NoError(t, err)
	outcome, err = writer.Save(ctx, item)
	require.NoError(t, err)
	assert.Equal(t, Unchanged, outcome)
	assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = '900000050'`))
}

func TestSaveKeepsARepublishedMateriaAsANewVersion(t *testing.T) {
	changes := map[string]func(*article.Article){
		"the text":   func(a *article.Article) { a.HTML += "<p>Republicada por incorreção.</p>" },
		"the ementa": func(a *article.Article) { a.Ementa = "Ementa republicada." },
		"the date":   func(a *article.Article) { a.PubDate = a.PubDate.AddDays(1) },
	}
	for name, change := range changes {
		t.Run(name, func(t *testing.T) {
			tx := begin(t)
			ctx := context.Background()
			original := builtSample(t)

			writer, err := Open(ctx, tx)
			require.NoError(t, err)
			_, err = writer.Save(ctx, original)
			require.NoError(t, err)

			republished := original
			change(&republished)
			outcome, err := writer.Save(ctx, republished)
			require.NoError(t, err)
			assert.Equal(t, NewVersion, outcome)

			// And once more: the republished one is now the latest, so it is unchanged.
			outcome, err = writer.Save(ctx, republished)
			require.NoError(t, err)
			assert.Equal(t, Unchanged, outcome)

			var versions string
			require.NoError(t, tx.QueryRow(ctx, `
				SELECT string_agg(versao::text, ',' ORDER BY versao) FROM ato WHERE id_dou = $1`, original.ID).
				Scan(&versions))
			assert.Equal(t, "1,2", versions)
			assert.Equal(t, 1, count(t, tx, `SELECT count(*) FROM ato WHERE id_dou = $1 AND versao = 1 AND conteudo = $2`,
				original.ID, original.HTML), "the first version stays as it was")
		})
	}
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
