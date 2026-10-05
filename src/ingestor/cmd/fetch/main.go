// Command fetch downloads a day's Diário Oficial da União editions from INLABS.
// It only orchestrates: arguments, configuration, log, exit code. The download
// itself belongs to the inlabs package.
package main

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"cloud.google.com/go/civil"

	"conselhos-vivos/internal/config"
	"conselhos-vivos/internal/inlabs"
	"conselhos-vivos/internal/store"
)

func main() {
	// TODO: use a lib to validate those args so we don't have to it ourselves
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	// No default day: the container runs in UTC, where "today" turns over three
	// hours early.
	var date inlabs.Date
	flag.Var(dateFlag{&date}, "date", "day to download (`YYYY-MM-DD`); required")
	envFile := flag.String("env", "", "path to a .env file with the INLABS credentials; the environment wins over it")
	flag.Usage = usage
	flag.Parse()

	if err := requireDate(date); err != nil {
		fmt.Fprintf(flag.CommandLine.Output(), "fetch: %v\n\n", err)
		flag.Usage()
		os.Exit(2)
	}

	summary, err := run(logger, *envFile, date)
	if err != nil {
		logger.Error("run aborted", "err", err)
		os.Exit(1)
	}

	logger.Info("done",
		"baixadas", summary.Downloaded,
		"sem-edicao", summary.NoEdition,
		"falhou", summary.Failed)

	if summary.Failed > 0 {
		os.Exit(1)
	}
}

func run(logger *slog.Logger, envFile string, date inlabs.Date) (inlabs.Summary, error) {
	var cfg config.Fetch
	if err := config.Load(envFile, &cfg); err != nil {
		return inlabs.Summary{}, err
	}

	client, err := inlabs.New(inlabs.Credentials{Email: cfg.Email, Password: cfg.Password}, logger)
	if err != nil {
		return inlabs.Summary{}, err
	}

	dest, err := store.New(cfg.OutputDir)
	if err != nil {
		return inlabs.Summary{}, err
	}

	logger.Info("iniciando", "data", date.String(), "destino", cfg.OutputDir)

	// TODO: mabye start the context inside the fetch itself, if it don't make test
	// harder to maintain.
	return client.FetchDay(context.Background(), date, dest)
}

// requireDate refuses a run with no -date; the zero Date is how its absence
// shows.
func requireDate(date inlabs.Date) error {
	if !date.IsValid() {
		return fmt.Errorf("-date is required, as YYYY-MM-DD, like 2026-10-02")
	}
	return nil
}

func usage() {
	out := flag.CommandLine.Output()
	fmt.Fprintf(out, "Usage of %s:\n", os.Args[0])
	flag.PrintDefaults()
	fmt.Fprint(out, "\n-date is required: this command never guesses the day. A caller that wants\n"+
		"today asks its own clock for it, in the time zone it means.\n\n"+
		"There is no resume: every run downloads the day again, overwriting what is\n"+
		"already on disk. Backfill is a shell loop over -date.\n")
}

// dateFlag accepts one spelling of a date and no other: YYYY-MM-DD.
//
// civil.ParseDate is already this strict; what this type adds is the message.
// flag.TextVar would report the failure in time.Parse's own words ("cannot
// parse \"02/10/2026\" as \"2006\""), a layout string the caller never saw.
type dateFlag struct{ date *inlabs.Date }

// String is empty until a date is set, so -h prints no default under a flag
// that says it is required.
func (f dateFlag) String() string {
	if f.date == nil || !f.date.IsValid() {
		return ""
	}
	return f.date.String()
}

func (f dateFlag) Set(raw string) error {
	date, err := civil.ParseDate(raw)
	if err != nil {
		return fmt.Errorf("want a date as YYYY-MM-DD, like 2026-10-02")
	}
	*f.date = date
	return nil
}
