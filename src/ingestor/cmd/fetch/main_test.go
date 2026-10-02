package main

import (
	"testing"

	"cloud.google.com/go/civil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDatesToFetch(t *testing.T) {
	today := mustParse(t, "2026-10-02")

	t.Run("no flags means today alone", func(t *testing.T) {
		dates, err := datesToFetch(today, today, today)
		require.NoError(t, err)

		require.Len(t, dates, 1)
		assert.Equal(t, "2026-10-02", dates[0].String())
	})

	t.Run("an interval ending today", func(t *testing.T) {
		dates, err := datesToFetch(mustParse(t, "2026-09-30"), today, today)
		require.NoError(t, err)

		assert.Len(t, dates, 3)
		assert.Equal(t, "2026-09-30", dates[0].String())
		assert.Equal(t, "2026-10-02", dates[2].String())
	})

	t.Run("an inverted interval is a usage error", func(t *testing.T) {
		_, err := datesToFetch(today, mustParse(t, "2026-09-30"), today)

		require.Error(t, err)
		assert.Contains(t, err.Error(), "starts after it ends")
	})

	t.Run("a day after today is a usage error", func(t *testing.T) {
		_, err := datesToFetch(today, mustParse(t, "2026-10-03"), today)

		require.Error(t, err)
		assert.Contains(t, err.Error(), "after today")
	})

	t.Run("a whole interval in the future is a usage error", func(t *testing.T) {
		_, err := datesToFetch(mustParse(t, "2026-10-05"), mustParse(t, "2026-10-07"), today)

		require.Error(t, err)
		assert.Contains(t, err.Error(), "-from is 2026-10-05")
	})
}

func mustParse(t *testing.T, value string) civil.Date {
	t.Helper()

	date, err := civil.ParseDate(value)
	require.NoError(t, err)
	return date
}

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
