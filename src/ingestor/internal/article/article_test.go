package article

import (
	"archive/zip"
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"cloud.google.com/go/civil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// entry is one file to put in a test edition: a name and its bytes.
type entry struct {
	name     string
	contents []byte
}

func sample(t *testing.T, name string) entry {
	t.Helper()

	contents, err := os.ReadFile(filepath.Join("testdata", name))
	require.NoError(t, err)
	return entry{name: name, contents: contents}
}

// edition builds a real zip in memory, so Read is exercised on the same
// archive/zip structures a downloaded edition gives it.
func edition(t *testing.T, entries ...entry) *zip.Reader {
	t.Helper()

	var buffer bytes.Buffer
	writer := zip.NewWriter(&buffer)
	for _, e := range entries {
		file, err := writer.Create(e.name)
		require.NoError(t, err)
		_, err = file.Write(e.contents)
		require.NoError(t, err)
	}
	require.NoError(t, writer.Close())

	reader, err := zip.NewReader(bytes.NewReader(buffer.Bytes()), int64(buffer.Len()))
	require.NoError(t, err)
	return reader
}

// collect drains Read, keeping the articles and the errors apart.
func collect(edition *zip.Reader) ([]Article, []error) {
	var articles []Article
	var errs []error
	for article, err := range Read(edition) {
		if err != nil {
			errs = append(errs, err)
			continue
		}
		articles = append(articles, article)
	}
	return articles, errs
}

// The real sample, BOM and CRLF included, field by field.
func TestParseRealArticle(t *testing.T) {
	articles, errs := collect(edition(t, sample(t, "515_20190507_11615606.xml")))
	require.Empty(t, errs)
	require.Len(t, articles, 1)
	got := articles[0]

	assert.Equal(t, "515_20190507_11615606.xml", got.Entry)
	assert.Equal(t, "8724946", got.ID)
	assert.Equal(t, "11615606", got.IDMateria)
	assert.Equal(t, "DO1", got.PubName)
	assert.Equal(t, "Alvará", got.ArtType)
	assert.Equal(t, civil.Date{Year: 2019, Month: time.May, Day: 7}, got.PubDate)
	assert.Equal(t, "25", got.NumberPage)
	assert.Equal(t, "86", got.EditionNumber)
	assert.Equal(t, "00018:00027:00002:00107:00000:00000:00000:00000:00000:00000:00004:00001", got.ArtClass)
	assert.Equal(t, []string{
		"Ministério da Justiça e Segurança Pública",
		"Polícia Federal",
		"Diretoria Executiva",
		"Coordenação-Geral de Controle de Serviços e Produtos",
	}, got.Category)
	assert.Equal(t, "Coordenação-Geral de Controle de Serviços e Produtos", got.Organ())
	assert.Equal(t, "ALVARÁ Nº 2.282, DE 15 DE ABRIL DE 2019", got.Identifica)
	assert.Empty(t, got.Ementa)
	assert.Empty(t, got.Titulo)
	assert.Empty(t, got.SubTitulo)

	assert.True(t, strings.HasPrefix(got.HTML, `<p></p><p class="identifica">`), "the HTML is kept as published")
	assert.Contains(t, got.HTML, `<p class="assina">LICINIO NUNES DE MORAES NETTO</p>`)
	assert.True(t, strings.HasPrefix(got.Text, "ALVARÁ Nº 2.282, DE 15 DE ABRIL DE 2019\nO(A) COORDENADOR(A)-GERAL"))
	assert.True(t, strings.HasSuffix(got.Text, "\nLICINIO NUNES DE MORAES NETTO"))
}

func TestParseConselho(t *testing.T) {
	articles, errs := collect(edition(t, sample(t, "conselho-construido.xml")))
	require.Empty(t, errs)
	require.Len(t, articles, 1)
	got := articles[0]

	assert.Equal(t, []string{"Ministério do Meio Ambiente e Mudança do Clima", "Conselho Nacional do Meio Ambiente"}, got.Category)
	assert.Equal(t, "Conselho Nacional do Meio Ambiente", got.Organ())
	assert.Equal(t, "187-A", got.EditionNumber, "an extra edition's number is not an integer")
	assert.Equal(t, "Matéria construída para teste: não foi publicada.", got.Ementa)
	assert.Equal(t, strings.Join([]string{
		"RESOLUÇÃO Nº 0, DE 1º DE OUTUBRO DE 2026",
		"O CONSELHO NACIONAL DO MEIO AMBIENTE & seus membros, resolve:",
		"Art. | Prazo",
		"1º | 30 dias",
		"Art. 2º Esta Resolução entra em vigor",
		"na data de sua publicação.",
		"FULANO DE TAL",
	}, "\n"), got.Text)
}

// The edition goes on past what it cannot read, and says which file it was.
func TestReadSurvivesBadEntries(t *testing.T) {
	articles, errs := collect(edition(t,
		sample(t, "515_20190507_11615606.xml"),
		sample(t, "malformado.xml"),
		entry{name: "imagens/figura.jpg", contents: []byte{0xff, 0xd8, 0xff}},
		sample(t, "529_20210601_13490090.xml"),
	))

	require.Len(t, articles, 2, "the entries around the bad ones are still read")
	assert.Equal(t, "8724946", articles[0].ID)
	assert.Equal(t, "20001323", articles[1].ID)

	require.Len(t, errs, 2)

	var malformed *EntryError
	require.ErrorAs(t, errs[0], &malformed)
	assert.Equal(t, "malformado.xml", malformed.Entry)
	assert.ErrorIs(t, errs[0], ErrMalformed)
	assert.Contains(t, errs[0].Error(), "malformado.xml")

	var image *EntryError
	require.ErrorAs(t, errs[1], &image)
	assert.Equal(t, "imagens/figura.jpg", image.Entry)
	assert.ErrorIs(t, errs[1], ErrNotXML)
}

func TestReadFindsXMLAtAnyDepth(t *testing.T) {
	nested := sample(t, "529_20210601_13490090.xml")
	nested.name = "2021-06-01-DO2/" + nested.name

	articles, errs := collect(edition(t, nested))
	require.Empty(t, errs)
	require.Len(t, articles, 1)
	assert.Equal(t, "2021-06-01-DO2/529_20210601_13490090.xml", articles[0].Entry)
}

func TestReadStopsWhenTheCallerDoes(t *testing.T) {
	zipped := edition(t,
		sample(t, "515_20190507_11615606.xml"),
		sample(t, "529_20210601_13490090.xml"),
	)

	seen := 0
	for range Read(zipped) {
		seen++
		break
	}
	assert.Equal(t, 1, seen)
}

// What the persistence could not key or attribute is refused, not passed on
// with blanks.
func TestParseRefusesIncompleteArticles(t *testing.T) {
	cases := map[string]string{
		"no id":               `<xml><article pubDate="02/10/2026" artCategory="A/B"/></xml>`,
		"no artCategory":      `<xml><article id="1" pubDate="02/10/2026"/></xml>`,
		"only slashes":        `<xml><article id="1" pubDate="02/10/2026" artCategory=" / "/></xml>`,
		"pubDate month first": `<xml><article id="1" pubDate="10/31/2026" artCategory="A/B"/></xml>`,
		"two articles":        `<xml><article id="1" pubDate="02/10/2026" artCategory="A"/><article id="2" pubDate="02/10/2026" artCategory="A"/></xml>`,
		"no article":          `<xml></xml>`,
	}
	for name, xml := range cases {
		t.Run(name, func(t *testing.T) {
			_, err := Parse(strings.NewReader(xml))
			assert.ErrorIs(t, err, ErrMalformed)
		})
	}
}

func TestSplitCategoryDropsEmptyLevels(t *testing.T) {
	assert.Equal(t, []string{"Ministério", "Conselho"}, splitCategory(" Ministério // Conselho/ "))
}

func TestOrganOfNoCategory(t *testing.T) {
	assert.Empty(t, Article{}.Organ())
}

func TestEntryErrorUnwraps(t *testing.T) {
	err := &EntryError{Entry: "a.xml", Err: ErrMalformed}
	assert.True(t, errors.Is(err, ErrMalformed))
	assert.Equal(t, "a.xml: not a DOU article", err.Error())
}
