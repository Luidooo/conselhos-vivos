// Command fetch downloads the Diário Oficial da União editions from INLABS.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"time"
	_ "time/tzdata" // a distroless image carries no zoneinfo; see inlabs.TimeZone

	"cloud.google.com/go/civil"

	"conselhos-vivos/internal/config"
	"conselhos-vivos/internal/inlabs"
)

// loginTimeout covers connecting and the login round trip, nothing else: the
// downloads get their own deadlines, sized by the edition.
const loginTimeout = 30 * time.Second

func main() {
	log.SetFlags(0)
	log.SetPrefix("fetch: ")

	location, err := inlabs.LoadLocation()
	if err != nil {
		log.Fatal(err)
	}
	today := inlabs.Today(time.Now(), location)

	// A misspelled date fails here, as a usage error, before any request.
	from, to := today, today
	flag.Var(dateFlag{&from}, "from", "first day to download (`YYYY-MM-DD`)")
	flag.Var(dateFlag{&to}, "to", "last day to download (`YYYY-MM-DD`)")
	envFile := flag.String("env", "", "path to a .env file with the INLABS credentials; the environment wins over it")
	flag.Parse()

	dates, err := datesToFetch(from, to, today)
	if err != nil {
		fmt.Fprintf(flag.CommandLine.Output(), "fetch: %v\n\n", err)
		flag.Usage()
		os.Exit(2)
	}

	if err := run(*envFile, dates); err != nil {
		log.Fatal(err)
	}
}

// dateFlag accepts one spelling of a date and no other: YYYY-MM-DD.
//
// civil.ParseDate is already this strict — it turns down 2026-10-2, 02/10/2026,
// 20261002 and a trailing space alike. What this type adds is the message:
// flag.TextVar would report the failure in time.Parse's own words ("cannot
// parse \"02/10/2026\" as \"2006\""), which describes a layout string the person
// running the command has never seen.
type dateFlag struct{ date *inlabs.Date }

func (f dateFlag) String() string {
	if f.date == nil {
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

// datesToFetch turns the interval the flags asked for into the days to
// download. A day after today cannot have an edition yet, and asking for it
// would record a 404 for a date that does not exist — so it is a usage error,
// not a day that simply comes back empty.
func datesToFetch(from, to, today inlabs.Date) ([]inlabs.Date, error) {
	if from.After(today) {
		return nil, fmt.Errorf("-from is %s, after today (%s)", from, today)
	}
	if to.After(today) {
		return nil, fmt.Errorf("-to is %s, after today (%s)", to, today)
	}
	return inlabs.Range(from, to)
}

func run(envFile string, dates []inlabs.Date) error {
	var cfg config.Fetch
	if err := config.Load(envFile, &cfg); err != nil {
		return err
	}

	if err := os.MkdirAll(cfg.OutputDir, 0o755); err != nil {
		return fmt.Errorf("preparing the output directory: %w", err)
	}

	client, err := inlabs.New()
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(context.Background(), loginTimeout)
	defer cancel()

	if err := client.Login(ctx, cfg.Email, cfg.Password); err != nil {
		return err
	}

	log.Printf("logged in as %s, writing to %s", cfg.Email, cfg.OutputDir)
	log.Printf("%d day(s) to download, from %s to %s", len(dates), dates[0], dates[len(dates)-1])

	for _, date := range dates {
		log.Printf("%s: pending", date)
		// TODO: Fetch the edition and hand the body to the store.
	}

	return nil
}
