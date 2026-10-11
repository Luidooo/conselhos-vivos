// Package article reads the matérias out of an INLABS edition: a zip in, one
// Article per XML out. It talks to neither the network nor the database, so it
// can be tested with sample files and no credential.
package article

import (
	"archive/zip"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"iter"
	"path"
	"strings"
	"time"

	"cloud.google.com/go/civil"
)

var (
	// ErrNotXML marks a zip entry that is not a matéria. INLABS ships each
	// article's images in the same zip, so this is routine: count it, log it,
	// move on. A directory entry gets it too: it should not happen, and this
	// way the caller logs it instead of the walk hiding it.
	ErrNotXML = errors.New("not an XML file")
	// ErrMalformed marks an XML that does not read as one DOU article.
	ErrMalformed = errors.New("not a DOU article")
)

// Article is one matéria, with the attributes of <article> and the fields of
// its <body>, under their XML names.
//
// The identifiers stay strings: ato.id_dou is a VARCHAR, and it is id that the
// persistence writes there (package oltp).
// editionNumber is a string because extra editions are numbered like "185-A".
type Article struct {
	// Entry is the file inside the zip, so any problem downstream can point at it.
	Entry string `json:"entry"`

	ID            string     `json:"id"`
	IDMateria     string     `json:"idMateria"`
	PubName       string     `json:"pubName"`
	ArtType       string     `json:"artType"`
	PubDate       civil.Date `json:"pubDate"`
	NumberPage    string     `json:"numberPage"`
	EditionNumber string     `json:"editionNumber"`
	ArtClass      string     `json:"artClass"`

	// Category is artCategory split on "/": the organ's hierarchy, from the
	// ministry down. The conselho, when there is one, is the last level.
	Category []string `json:"artCategory"`

	Identifica string `json:"identifica"`
	Ementa     string `json:"ementa"`
	Titulo     string `json:"titulo"`
	SubTitulo  string `json:"subTitulo"`

	// HTML is <Texto> as published, the source of truth: the <p class="assina">
	// and <p class="identifica"> markers only survive here. Text is the same
	// content as plain text, derived from it by PlainText.
	HTML string `json:"html,omitempty"`
	Text string `json:"texto"`
}

// Organ is the last level of the hierarchy: the body that published the
// matéria. Matching it to a conselho is the persistence's job.
func (a Article) Organ() string {
	if len(a.Category) == 0 {
		return ""
	}
	return a.Category[len(a.Category)-1]
}

// EntryError is a failure confined to one zip entry. It names the entry, so a
// bad file is found without unzipping the edition by hand.
type EntryError struct {
	Entry string
	Err   error
}

func (e *EntryError) Error() string { return fmt.Sprintf("%s: %v", e.Entry, e.Err) }
func (e *EntryError) Unwrap() error { return e.Err }

// Read walks the edition and yields one Article per XML entry, opening one
// entry at a time: a day is ~300 of them, and the pipeline runs over many days.
//
// A failure in one entry is yielded as an *EntryError and the walk goes on, so
// one bad file never costs the rest of the edition.
func Read(edition *zip.Reader) iter.Seq2[Article, error] {
	return func(yield func(Article, error) bool) {
		for _, file := range edition.File {
			article, err := readEntry(file)
			if err != nil {
				err = &EntryError{Entry: file.Name, Err: err}
			}
			if !yield(article, err) {
				return
			}
		}
	}
}

func readEntry(file *zip.File) (Article, error) {
	// At any depth, as Ro-dou reads them: nothing promises a flat zip.
	if !strings.EqualFold(path.Ext(file.Name), ".xml") {
		return Article{}, ErrNotXML
	}

	contents, err := file.Open()
	if err != nil {
		return Article{}, fmt.Errorf("opening: %w", err)
	}
	defer contents.Close()

	article, err := parse(contents)
	if err != nil {
		return Article{}, err
	}
	article.Entry = file.Name
	return article, nil
}

// document is the file as INLABS writes it: <xml><article ...>. The root's name
// is not checked; there has to be exactly one <article> under it.
type document struct {
	Articles []rawArticle `xml:"article"`
}

type rawArticle struct {
	ID            string `xml:"id,attr"`
	IDMateria     string `xml:"idMateria,attr"`
	PubName       string `xml:"pubName,attr"`
	ArtType       string `xml:"artType,attr"`
	PubDate       string `xml:"pubDate,attr"`
	NumberPage    string `xml:"numberPage,attr"`
	EditionNumber string `xml:"editionNumber,attr"`
	ArtClass      string `xml:"artClass,attr"`
	ArtCategory   string `xml:"artCategory,attr"`
	Identifica    string `xml:"body>Identifica"`
	Ementa        string `xml:"body>Ementa"`
	Titulo        string `xml:"body>Titulo"`
	SubTitulo     string `xml:"body>SubTitulo"`
	Texto         string `xml:"body>Texto"`
}

// pubDateLayout is pubDate as INLABS writes it: day first.
const pubDateLayout = "02/01/2006"

// parse reads one article's XML. It refuses what the persistence could not key
// or attribute: no id, no publication date, no artCategory.
func parse(r io.Reader) (Article, error) {
	var doc document
	if err := xml.NewDecoder(r).Decode(&doc); err != nil {
		return Article{}, fmt.Errorf("%w: %w", ErrMalformed, err)
	}
	if len(doc.Articles) != 1 {
		return Article{}, fmt.Errorf("%w: want one <article>, found %d", ErrMalformed, len(doc.Articles))
	}
	raw := doc.Articles[0]

	if strings.TrimSpace(raw.ID) == "" {
		return Article{}, fmt.Errorf("%w: <article> has no id", ErrMalformed)
	}
	published, err := time.Parse(pubDateLayout, strings.TrimSpace(raw.PubDate))
	if err != nil {
		return Article{}, fmt.Errorf("%w: pubDate %q is not DD/MM/YYYY", ErrMalformed, raw.PubDate)
	}
	category := splitCategory(raw.ArtCategory)
	if len(category) == 0 {
		return Article{}, fmt.Errorf("%w: <article> has no artCategory", ErrMalformed)
	}

	return Article{
		ID:            strings.TrimSpace(raw.ID),
		IDMateria:     strings.TrimSpace(raw.IDMateria),
		PubName:       strings.TrimSpace(raw.PubName),
		ArtType:       strings.TrimSpace(raw.ArtType),
		PubDate:       civil.DateOf(published),
		NumberPage:    strings.TrimSpace(raw.NumberPage),
		EditionNumber: strings.TrimSpace(raw.EditionNumber),
		ArtClass:      strings.TrimSpace(raw.ArtClass),
		Category:      category,
		Identifica:    strings.TrimSpace(raw.Identifica),
		Ementa:        strings.TrimSpace(raw.Ementa),
		Titulo:        strings.TrimSpace(raw.Titulo),
		SubTitulo:     strings.TrimSpace(raw.SubTitulo),
		HTML:          raw.Texto,
		Text:          PlainText(raw.Texto),
	}, nil
}

// splitCategory is the whole of the organ resolution here: split on "/", no
// NLP. Empty levels — a doubled or trailing slash — are dropped.
func splitCategory(raw string) []string {
	var levels []string
	for _, level := range strings.Split(raw, "/") {
		if level = strings.TrimSpace(level); level != "" {
			levels = append(levels, level)
		}
	}
	return levels
}
