package inlabs

import (
	"archive/zip"
	"context"
	"errors"
	"fmt"
	"io"
	"time"

	"conselhos-vivos/internal/store"
)

// sectionTimeout covers one edition end to end, body included. A global
// http.Client.Timeout would abort a legitimate large download instead.
const sectionTimeout = 10 * time.Minute

// Section is one of the Diário Oficial's sections. DO1E is the same day's extra
// edition, published as a file of its own.
type Section string

const (
	SectionDO1  Section = "DO1"
	SectionDO1E Section = "DO1E"
)

// sections is a day, in download order. A slice cannot be a const.
var sections = []Section{SectionDO1, SectionDO1E}

// ZipName is the edition's file name, in the download URL and on disk alike, so
// the two cannot drift apart.
func ZipName(d Date, s Section) string {
	return fmt.Sprintf("%s-%s.zip", d, s)
}

// Saver is where a downloaded edition lands, under the name ZipName gives it.
type Saver interface {
	Save(name string, body io.Reader) (store.Receipt, error)
}

// Outcome is what happened to one (date, section).
type Outcome string

const (
	Downloaded Outcome = "baixada"
	NoEdition  Outcome = "sem-edicao"
	Failed     Outcome = "falhou"
)

// Summary is a day's outcomes, counted: what the command reports and exits on.
type Summary struct {
	Downloaded int
	NoEdition  int
	Failed     int
}

func (s *Summary) add(result Outcome) {
	switch result {
	case Downloaded:
		s.Downloaded++
	case NoEdition:
		s.NoEdition++
	case Failed:
		s.Failed++
	}
}

// FetchDay downloads one day of the Diário Oficial into dest: it checks the
// date, logs in when there is no session, and walks the day's sections.
//
// A failure the next section would not inherit is counted and the day goes on;
// any other stops it. See survivable.
func (c *Client) FetchDay(ctx context.Context, date Date, dest Saver) (Summary, error) {
	var summary Summary

	if err := checkDate(date, Today(c.clock(), c.location)); err != nil {
		return summary, err
	}

	for _, section := range sections {
		// Per section, not per day: each edition gets the full allowance.
		sectionCtx, cancel := context.WithTimeout(ctx, sectionTimeout)
		result, err := c.downloadSection(sectionCtx, dest, date, section)
		cancel()

		if err != nil {
			if ctx.Err() != nil {
				return summary, ctx.Err()
			}
			if !survivable(err) {
				return summary, err
			}
		}

		summary.add(result)

		// A counted failure still has to say why.
		attrs := []any{"data", date.String(), "secao", string(section), "desfecho", string(result)}
		if err != nil {
			attrs = append(attrs, "erro", err)
		}
		c.logger.Info("edicao", attrs...)
	}

	return summary, nil
}

// TODO: no fucking reason for it to be a method ??
// downloadSection is one edition: ask, classify, stream to dest. A missing one
// is an outcome, not an error — most days have no extra edition.
func (c *Client) downloadSection(ctx context.Context, dest Saver,
	date Date, section Section) (Outcome, error) {
	body, err := c.fetchSection(ctx, date, section)
	switch {
	case errors.Is(err, ErrNoEdition):
		return NoEdition, nil
	case err != nil:
		return Failed, err
	}
	defer body.Close()

	if _, err := dest.Save(ZipName(date, section), body); err != nil {
		return Failed, err
	}
	return Downloaded, nil
}

func survivable(err error) bool {
	return errors.Is(err, ErrTransient) ||
		errors.Is(err, context.DeadlineExceeded) ||
		errors.Is(err, zip.ErrFormat)
}
