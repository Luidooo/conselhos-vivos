package inlabs

import (
	"fmt"
	"time"
	_ "time/tzdata" // the zone database, embedded; see TimeZone

	"cloud.google.com/go/civil"
)

// TimeZone is where the DOU's day begins and ends. Containers run in UTC, so
// between 9pm and midnight in Brasília "today" there is already tomorrow — a
// guaranteed 404 that would read as "there was no edition".
//
// There is no America/Brasilia in the tz database, and a fixed -03:00 would be
// wrong before 2019, when the country still had DST.
const TimeZone = "America/Sao_Paulo"

func LoadLocation() (*time.Location, error) {
	location, err := time.LoadLocation(TimeZone)
	if err != nil {
		return nil, fmt.Errorf("loading the time zone %q: %w", TimeZone, err)
	}
	return location, nil
}

// Date is a calendar day, with no time of day inside: editions are keyed by day,
// and hours would make two days compare equal or not depending on when the
// program ran. An alias, so civil's own API comes with it.
type Date = civil.Date

// Today is the current day in loc; the instant is an argument so a test can pin
// it.
func Today(now time.Time, loc *time.Location) Date {
	return civil.DateOf(now.In(loc))
}

// firstServed is the oldest day INLABS serves, per issue #6.
var firstServed = Date{Year: 2020, Month: time.January, Day: 1}

// checkDate refuses the days that cannot have an edition: letting one through
// would record its 404 as "no edition", indistinguishable from a holiday.
func checkDate(date, today Date) error {
	if date.After(today) {
		return fmt.Errorf("%w: %s is after today (%s), so that edition cannot exist yet",
			ErrDateOutOfRange, date, today)
	}
	if date.Before(firstServed) {
		return fmt.Errorf("%w: %s is before %s, the oldest day it serves",
			ErrDateOutOfRange, date, firstServed)
	}
	return nil
}
