// Command persist writes the matérias of one edition already on disk into the
// curation database. It only orchestrates: the reading belongs to the article
// package and the writing to oltp.
//
// One zip per run, as in extract, and one transaction per zip: an edition is
// in the database whole or not at all. It can be run again: what is already
// there is left alone, and an id that comes twice in the zip counts once.
package main

import (
	"archive/zip"
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"github.com/jackc/pgx/v5"

	"conselhos-vivos/internal/article"
	"conselhos-vivos/internal/oltp"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	flag.Usage = usage
	flag.Parse()

	if flag.NArg() != 1 {
		fmt.Fprintf(flag.CommandLine.Output(), "persist: want exactly one zip, got %d\n\n", flag.NArg())
		flag.Usage()
		os.Exit(2)
	}

	summary, err := run(context.Background(), logger, flag.Arg(0))
	if err != nil {
		logger.Error("run aborted", "err", err)
		os.Exit(1)
	}

	logger.Info("done",
		"gravadas", summary.Saved,
		"versoes-novas", summary.NewVersions,
		"inalteradas", summary.Unchanged,
		"orgao-desconhecido", summary.UnknownOrgan,
		"repetidas", summary.Repeated,
		"ignoradas", summary.Skipped,
		"falhou", summary.Failed)

	// The zip is committed by now: 1 says an entry failed, not that nothing went in.
	if summary.Failed > 0 {
		os.Exit(1)
	}
}

// run is persist inside a transaction of its own, committed only when the
// whole zip went through.
func run(ctx context.Context, logger *slog.Logger, path string) (Summary, error) {
	// The address and the credentials come from the PG* variables, as in psql.
	conn, err := pgx.Connect(ctx, "")
	if err != nil {
		return Summary{}, fmt.Errorf("connecting to the database: %w", err)
	}
	defer conn.Close(ctx)

	tx, err := conn.Begin(ctx)
	if err != nil {
		return Summary{}, fmt.Errorf("opening the transaction: %w", err)
	}
	// A no-op after the commit.
	defer tx.Rollback(ctx)

	summary, err := persist(ctx, tx, logger, path)
	if err != nil {
		return Summary{}, err
	}
	if err := tx.Commit(ctx); err != nil {
		return Summary{}, fmt.Errorf("committing %s: %w", path, err)
	}
	return summary, nil
}

// Summary counts the entries of the zip by what became of them.
type Summary struct {
	// Saved is a matéria written for the first time.
	Saved int
	// NewVersions is a matéria that was there and came back different.
	NewVersions int
	// Unchanged is a matéria that was already there as it is.
	Unchanged int
	// UnknownOrgan is a matéria of an organ that is none of the known ones:
	// left out, with the organ queued for a decision.
	UnknownOrgan int
	// Repeated is a matéria whose id an earlier entry of the zip already had:
	// left out, whatever it says.
	Repeated int
	// Skipped is an entry that is not XML, like an article's image.
	Skipped int
	// Failed is an XML that did not read as a matéria, or one with no <Texto>.
	Failed int
}

// persist saves every matéria of the zip through db. A bad entry is logged and
// counted; a zip that does not open, or a database that refuses a write, ends
// the run.
//
// Of two entries with the same id, the first in the zip is the matéria and the
// other is left out. Saving both would make the second a new version of the
// first, and the next run a new version of the second: the same zip would
// never stop writing.
func persist(ctx context.Context, db oltp.DB, logger *slog.Logger, path string) (Summary, error) {
	var summary Summary

	edition, err := zip.OpenReader(path)
	if err != nil {
		return summary, fmt.Errorf("opening %s: %w", path, err)
	}
	defer edition.Close()

	writer, err := oltp.Open(ctx, db)
	if err != nil {
		return summary, err
	}

	// seen maps an id to the entry that had it first.
	seen := make(map[string]string)

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

		if first, repeated := seen[item.ID]; repeated {
			summary.Repeated++
			logger.Warn("repetida", "zip", path, "entrada", item.Entry, "id", item.ID, "primeira", first)
			continue
		}
		seen[item.ID] = item.Entry

		outcome, err := writer.Save(ctx, item)
		switch {
		case errors.Is(err, oltp.ErrNoContent):
			summary.Failed++
			logger.Warn("falhou", "zip", path, "erro", err)
			continue
		case err != nil:
			return summary, err
		}

		switch outcome {
		case oltp.Saved:
			summary.Saved++
		case oltp.NewVersion:
			summary.NewVersions++
			logger.Info("versao-nova", "zip", path, "entrada", item.Entry, "id", item.ID)
		case oltp.Unchanged:
			summary.Unchanged++
		case oltp.UnknownOrgan:
			summary.UnknownOrgan++
		}
	}
	return summary, nil
}

func usage() {
	out := flag.CommandLine.Output()
	fmt.Fprintf(out, "Usage of %s: EDITION.zip\n", os.Args[0])
	flag.PrintDefaults()
	fmt.Fprint(out, "\nWrites the matérias of the zip into ato, in one transaction; the database is\n"+
		"the one the PG* variables point at. It can be run again: a matéria already\n"+
		"there is left alone, and one that came back different goes in as a new\n"+
		"version. A matéria of an unknown organ is left out and the organ is queued in\n"+
		"orgao_alias. Of two entries with the same id, only the first is saved. An XML\n"+
		"that is not a matéria is a failure, and the exit code is 1 even though the\n"+
		"rest of the zip was written and committed.\n")
}
