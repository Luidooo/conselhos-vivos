package inlabs

import (
	"testing"
	"time"

	"cloud.google.com/go/civil"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// The trap this package exists to avoid: the container runs in UTC, and after
// 9pm in Brasília the UTC day is already the next one. Asking INLABS for
// tomorrow is a guaranteed 404, which would be recorded as "no edition" for a
// working day.
func TestTodayUsesTheDOUTimeZone(t *testing.T) {
	location, err := LoadLocation()
	require.NoError(t, err)

	tests := map[string]struct {
		instant string
		want    string
	}{
		"half past midnight in UTC is still the day before in Brasília": {
			instant: "2026-10-02T01:30:00Z",
			want:    "2026-10-01",
		},
		"the same wall clock read in UTC would have said the 2nd": {
			instant: "2026-10-02T12:00:00Z",
			want:    "2026-10-02",
		},
		"right at midnight in Brasília": {
			instant: "2026-10-02T03:00:00Z",
			want:    "2026-10-02",
		},
		"one second before midnight in Brasília": {
			instant: "2026-10-02T02:59:59Z",
			want:    "2026-10-01",
		},
	}

	for name, test := range tests {
		t.Run(name, func(t *testing.T) {
			now, err := time.Parse(time.RFC3339, test.instant)
			require.NoError(t, err)

			assert.Equal(t, test.want, Today(now, location).String())
		})
	}
}

func TestDateOrdering(t *testing.T) {
	second := mustParse(t, "2026-10-02")
	third := mustParse(t, "2026-10-03")
	nextMonth := mustParse(t, "2026-11-01")
	nextYear := mustParse(t, "2027-01-01")

	assert.True(t, second.Before(third))
	assert.True(t, third.After(second))
	assert.True(t, second.Before(nextMonth))
	assert.True(t, nextMonth.Before(nextYear))

	assert.False(t, second.Before(second))
	assert.False(t, second.After(second))
	assert.Zero(t, second.Compare(second))
}

func TestRange(t *testing.T) {
	tests := map[string]struct {
		first, last string
		want        []string
	}{
		"a single day": {
			first: "2026-10-02", last: "2026-10-02",
			want: []string{"2026-10-02"},
		},
		"a few days": {
			first: "2026-10-02", last: "2026-10-05",
			want: []string{"2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05"},
		},
		"across a month": {
			first: "2026-10-30", last: "2026-11-02",
			want: []string{"2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"},
		},
		"across a year": {
			first: "2026-12-31", last: "2027-01-01",
			want: []string{"2026-12-31", "2027-01-01"},
		},
		"across the end of February in a leap year": {
			first: "2024-02-28", last: "2024-03-01",
			want: []string{"2024-02-28", "2024-02-29", "2024-03-01"},
		},
	}

	for name, test := range tests {
		t.Run(name, func(t *testing.T) {
			dates, err := Range(mustParse(t, test.first), mustParse(t, test.last))
			require.NoError(t, err)

			got := make([]string, 0, len(dates))
			for _, date := range dates {
				got = append(got, date.String())
			}
			assert.Equal(t, test.want, got)
		})
	}
}

func TestRangeRejectsAnInvertedInterval(t *testing.T) {
	_, err := Range(mustParse(t, "2026-10-05"), mustParse(t, "2026-10-02"))

	require.Error(t, err)
	assert.Contains(t, err.Error(), "starts after it ends")
}

// A four month backfill is the real use, so the walk has to survive it without
// losing or repeating a day.
func TestRangeOverFourMonths(t *testing.T) {
	dates, err := Range(mustParse(t, "2026-06-01"), mustParse(t, "2026-09-30"))
	require.NoError(t, err)

	assert.Len(t, dates, 30+31+31+30)
	assert.Equal(t, "2026-06-01", dates[0].String())
	assert.Equal(t, "2026-09-30", dates[len(dates)-1].String())

	for i := 1; i < len(dates); i++ {
		require.True(t, dates[i-1].Before(dates[i]), "the dates should come out in order, with no repeats")
	}
}

func mustParse(t *testing.T, value string) Date {
	t.Helper()

	date, err := civil.ParseDate(value)
	require.NoError(t, err)
	return date
}
