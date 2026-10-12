// Command fetch-mensal downloads a whole month of the Diário Oficial's Section 1
// from the Imprensa Nacional's open data, with no sign-in. It only
// orchestrates: arguments, configuration, log, exit code. The download itself
// belongs to the dadosabertos package.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"conselhos-vivos/internal/config"
	"conselhos-vivos/internal/dadosabertos"
	"conselhos-vivos/internal/store"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	month := flag.String("month", "", "month to download (`YYYY-MM`); required")
	flag.Usage = usage
	flag.Parse()

	m, err := dadosabertos.ParseMonth(*month)
	if err != nil {
		fmt.Fprintf(flag.CommandLine.Output(), "fetch-mensal: -month: %v\n\n", err)
		flag.Usage()
		os.Exit(2)
	}

	if err := run(logger, m); err != nil {
		if errors.Is(err, dadosabertos.ErrNotPublished) {
			logger.Error("mes ainda nao publicado", "mes", m.String(), "err", err)
		} else {
			logger.Error("run aborted", "err", err)
		}
		os.Exit(1)
	}
}

func run(logger *slog.Logger, m dadosabertos.Month) error {
	var cfg config.FetchMensal
	if err := config.Load("", &cfg); err != nil {
		return err
	}

	dest, err := store.New(cfg.OutputDir)
	if err != nil {
		return err
	}

	logger.Info("iniciando", "mes", m.String(), "destino", cfg.OutputDir)

	_, err = dadosabertos.New(logger).FetchMonth(context.Background(), m, dest)
	return err
}

func usage() {
	out := flag.CommandLine.Output()
	fmt.Fprintf(out, "Usage of %s:\n", os.Args[0])
	flag.PrintDefaults()
	fmt.Fprint(out, "\nDownloads Section 1 of the month as the Imprensa Nacional publishes it, one\n"+
		"zip with every day's DO1 and DO1E, into DADOS_ABERTOS_OUTPUT_DIR under its\n"+
		"published name (S01MMYYYY.zip). A month already on disk is not asked for\n"+
		"again. A month is published about two weeks after it ends; one that is not\n"+
		"out yet exits with 1 and writes nothing.\n")
}
