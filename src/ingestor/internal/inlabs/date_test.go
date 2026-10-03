package inlabs

import (
	"testing"
	"time"

	"cloud.google.com/go/civil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// The trap this file exists to avoid: the container runs in UTC, and after 9pm
// in Brasília the UTC day is already the next one. Asking INLABS for tomorrow
// is a guaranteed 404, which would be recorded as "no edition" for a working
// day.
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
		"one second before midnight in Brasília": {
			instant: "2026-10-02T02:59:59Z",
			want:    "2026-10-01",
		},
		"right at midnight in Brasília": {
			instant: "2026-10-02T03:00:00Z",
			want:    "2026-10-02",
		},
		"midday leaves no room for doubt": {
			instant: "2026-10-02T12:00:00Z",
			want:    "2026-10-02",
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

func TestTheServedDateWindow(t *testing.T) {
	today := mustParse(t, "2026-10-02")

	t.Run("today is accepted", func(t *testing.T) {
		require.NoError(t, checkDate(today, today))
	})

	t.Run("a past day inside the served window is accepted", func(t *testing.T) {
		require.NoError(t, checkDate(mustParse(t, "2024-06-15"), today))
	})

	t.Run("the floor itself is accepted", func(t *testing.T) {
		require.NoError(t, checkDate(mustParse(t, "2020-01-01"), today))
	})

	t.Run("the day before the floor is refused", func(t *testing.T) {
		err := checkDate(mustParse(t, "2019-12-31"), today)

		require.Error(t, err)
		assert.Contains(t, err.Error(), "2020-01-01", "the message should name the limit")
	})

	t.Run("tomorrow is refused", func(t *testing.T) {
		err := checkDate(mustParse(t, "2026-10-03"), today)

		require.Error(t, err)
		assert.Contains(t, err.Error(), "after today")
	})

	t.Run("a far past typo is refused, not silently fetched", func(t *testing.T) {
		err := checkDate(mustParse(t, "1900-01-01"), today)

		require.ErrorIs(t, err, ErrDateOutOfRange)
		assert.Contains(t, err.Error(), "1900-01-01", "the message should name the date it refused")
	})
}

func mustParse(t *testing.T, value string) Date {
	t.Helper()

	date, err := civil.ParseDate(value)
	require.NoError(t, err)
	return date
}
