package article

import (
	"strings"

	"golang.org/x/net/html"
	"golang.org/x/net/html/atom"
)

// PlainText turns <Texto>'s HTML into text: one line per paragraph, entities
// decoded, runs of whitespace collapsed. A table row stays on one line, its
// cells separated by " | ".
//
// It never fails: HTML that is not well formed still yields its words.
func PlainText(fragment string) string {
	var lines []string
	var line strings.Builder

	breakLine := func() {
		if text := strings.Join(strings.Fields(line.String()), " "); text != "" {
			lines = append(lines, text)
		}
		line.Reset()
	}

	tokens := html.NewTokenizer(strings.NewReader(fragment))
	for {
		kind := tokens.Next()
		switch kind {
		case html.ErrorToken:
			// The end of the input; the tokenizer has no other error to report
			// on a strings.Reader.
			breakLine()
			return strings.Join(lines, "\n")
		case html.TextToken:
			line.Write(tokens.Text())
		case html.StartTagToken, html.EndTagToken, html.SelfClosingTagToken:
			name, _ := tokens.TagName()
			switch atom.Lookup(name) {
			case atom.P, atom.Br, atom.Div, atom.Tr, atom.Li, atom.Table,
				atom.H1, atom.H2, atom.H3, atom.H4, atom.H5, atom.H6:
				breakLine()
			case atom.Td, atom.Th:
				if kind == html.StartTagToken && strings.TrimSpace(line.String()) != "" {
					line.WriteString(" | ")
				}
			}
		}
	}
}
