package main

import (
	"bytes"
	"flag"
	"os"
	"testing"

	"cloud.google.com/go/civil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Only the command line is tested here; the download is the inlabs package's,
// and is tested there against a real client.
func TestDateFlagTakesOneFormatOnly(t *testing.T) {
	var date civil.Date
	flag := dateFlag{&date}

	require.NoError(t, flag.Set("2026-10-02"))
	assert.Equal(t, "2026-10-02", date.String())
	assert.Equal(t, "2026-10-02", flag.String(), "the flag prints what -h shows as the default")

	// Every spelling someone reaches for by habit, and the near misses.
	for _, raw := range []string{
		"02/10/2026", "10-02-2026", "2026-10-2", "2026-1-02", "20261002",
		"26-10-02", "2026-10-02T00:00:00Z", "2026-10-02 ", " 2026-10-02",
		"2026-02-31", "2026-13-01", "hoje", "",
	} {
		t.Run(raw, func(t *testing.T) {
			err := flag.Set(raw)

			require.Error(t, err)
			assert.Contains(t, err.Error(), "YYYY-MM-DD", "the error should name the one format")
		})
	}
}

// A date the archive cannot have still parses; inlabs is what turns it down.
func TestDateFlagAcceptsAWellSpelledImpossibleDate(t *testing.T) {
	var date civil.Date

	require.NoError(t, dateFlag{&date}.Set("1900-01-01"))
	assert.Equal(t, "1900-01-01", date.String())
}

func TestUsageSaysThereIsNoResume(t *testing.T) {
	var captured bytes.Buffer
	flag.CommandLine.SetOutput(&captured)
	t.Cleanup(func() { flag.CommandLine.SetOutput(os.Stderr) })

	usage()

	assert.Contains(t, captured.String(), "no resume")
}

func TestTheDateIsRequired(t *testing.T) {
	var missing civil.Date

	err := requireDate(missing)

	require.Error(t, err, "a run with no -date must not fall back to a guessed day")
	assert.Contains(t, err.Error(), "required")
}

func TestAGivenDatePassesTheRequirement(t *testing.T) {
	var date civil.Date
	require.NoError(t, dateFlag{&date}.Set("2026-10-02"))

	assert.NoError(t, requireDate(date))
}

func TestUsageSaysTheDateIsRequired(t *testing.T) {
	var captured bytes.Buffer
	flag.CommandLine.SetOutput(&captured)
	t.Cleanup(func() { flag.CommandLine.SetOutput(os.Stderr) })

	usage()

	assert.Contains(t, captured.String(), "-date is required")
}
