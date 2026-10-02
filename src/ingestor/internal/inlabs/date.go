package inlabs

import (
	"fmt"
	"time"

	"cloud.google.com/go/civil"
)

// TimeZone is where the DOU's day begins and ends. It is not a preference: the
// official images run in UTC and the compose file sets no TZ, so between 9pm
// and midnight in Brasília "today" inside a container is already tomorrow —
// and tomorrow is a guaranteed 404 that would read as "there was no edition".
//
// It is America/Sao_Paulo because that is the name the tz database gives the
// zone Brasília sits in; there is no America/Brasilia. A fixed -03:00 offset
// would be wrong for any date before 2019, when the country still had DST.
//
// The command that loads it must also import _ "time/tzdata": a distroless
// image carries no zoneinfo, so LoadLocation would pass in a local test and
// fail in production.
const TimeZone = "America/Sao_Paulo"

// LoadLocation returns the DOU's time zone.
func LoadLocation() (*time.Location, error) {
	location, err := time.LoadLocation(TimeZone)
	if err != nil {
		return nil, fmt.Errorf("loading the time zone %q: %w", TimeZone, err)
	}
	return location, nil
}

type Date = civil.Date

// Today is the current day in loc. The instant comes in as an argument so the
// time zone is something the tests can exercise instead of something only
// production finds out about.
func Today(now time.Time, loc *time.Location) Date {
	return civil.DateOf(now.In(loc))
}

// Range lists every day from first to last, both included.
func Range(first, last Date) ([]Date, error) {
	if first.After(last) {
		return nil, fmt.Errorf("the range starts after it ends: %s to %s", first, last)
	}

	// AddDays walks in UTC, which is what keeps this honest: a day that starts
	// on a DST transition has no midnight, and adding days in a zone that has
	// one can repeat or skip a day.
	var dates []Date
	for date := first; !date.After(last); date = date.AddDays(1) {
		dates = append(dates, date)
	}
	return dates, nil
}
