// Command extract reads the matérias out of one edition already on disk and
// prints them, one JSON object per line, so a zip can be inspected with no
// database. The reading itself belongs to the article package.
//
// One zip per run: a day's DO1 and DO1E are two runs, and so is a range of
// days. Each run then only has one zip's partial failures to report.
package main

import (
	"archive/zip"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"

	"conselhos-vivos/internal/article"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	withHTML := flag.Bool("html", false, "also print <Texto> as published, HTML and all")
	flag.Usage = usage
	flag.Parse()

	if flag.NArg() != 1 {
		fmt.Fprintf(flag.CommandLine.Output(), "extract: want exactly one zip, got %d\n\n", flag.NArg())
		flag.Usage()
		os.Exit(2)
	}

	summary, err := extract(os.Stdout, logger, flag.Arg(0), *withHTML)
	if err != nil {
		logger.Error("run aborted", "err", err)
		os.Exit(1)
	}

	logger.Info("done",
		"lidas", summary.Read,
		"ignoradas", summary.Skipped,
		"falhou", summary.Failed)

	if summary.Failed > 0 {
		os.Exit(1)
	}
}

// Summary counts the entries of the zip.
type Summary struct {
	// Read is a matéria printed.
	Read int
	// Skipped is an entry that is not XML, like an article's image: expected,
	// logged, not a failure.
	Skipped int
	// Failed is an XML that did not read as a matéria.
	Failed int
}

// extract prints every matéria of the zip to out. A bad entry is logged and
// counted; a zip that does not open, or an out that stops taking lines, ends
// the run.
func extract(out io.Writer, logger *slog.Logger, path string, withHTML bool) (Summary, error) {
	var summary Summary
	encoder := json.NewEncoder(out)
	encoder.SetEscapeHTML(false)

	edition, err := zip.OpenReader(path)
	if err != nil {
		return summary, fmt.Errorf("opening %s: %w", path, err)
	}
	defer edition.Close()

	for item, err := range article.Read(&edition.Reader) {
		switch {
		case errors.Is(err, article.ErrNotXML):
			summary.Skipped++
			logger.Info("ignorada", "zip", path, "erro", err)
			continue
		case err != nil:
			summary.Failed++
			logger.Warn("falhou", "zip", path, "erro", err)
			continue
		}

		if !withHTML {
			item.HTML = ""
		}
		if err := encoder.Encode(item); err != nil {
			return summary, fmt.Errorf("printing %s from %s: %w", item.Entry, path, err)
		}
		summary.Read++
	}
	return summary, nil
}

func usage() {
	out := flag.CommandLine.Output()
	fmt.Fprintf(out, "Usage of %s: [-html] EDITION.zip\n", os.Args[0])
	flag.PrintDefaults()
	fmt.Fprint(out, "\nPrints one JSON object per matéria to stdout; the log and the summary go to\n"+
		"stderr. An entry that is not XML is skipped; one that is XML but not a matéria\n"+
		"is a failure, and the exit code is 1.\n")
}
