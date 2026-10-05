package inlabs

import (
	"archive/zip"
	"bytes"
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"sync/atomic"
	"syscall"
	"testing"
	"time"

	"cloud.google.com/go/civil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// douServer answers the login, then routes each edition request to the handler
// registered for that section. A section with none gets a 404, which is how
// INLABS says there is no such edition.
func douServer(t *testing.T, editions map[Section]http.HandlerFunc) *Client {
	t.Helper()

	return newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/logar.php" {
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "sessao", Path: "/"})
			return
		}

		for section, handler := range editions {
			if r.URL.Query().Get("dl") == ZipName(testDate(t), section) {
				handler(w, r)
				return
			}
		}
		w.WriteHeader(http.StatusNotFound)
	})
}

func servesAZip(w http.ResponseWriter, _ *http.Request) {
	w.Write(zipBody())
}

func TestZipNameCarriesTheSection(t *testing.T) {
	date, err := civil.ParseDate("2026-10-02")
	require.NoError(t, err)

	assert.Equal(t, "2026-10-02-DO1.zip", ZipName(date, SectionDO1))
	assert.Equal(t, "2026-10-02-DO1E.zip", ZipName(date, SectionDO1E))
}

func TestSectionsAreOrdered(t *testing.T) {
	assert.Equal(t, []Section{SectionDO1, SectionDO1E}, sections,
		"DO1 comes first: it is the edition that exists every working day")
}

func TestFetchDaySavesEverySection(t *testing.T) {
	client := douServer(t, map[Section]http.HandlerFunc{
		SectionDO1:  servesAZip,
		SectionDO1E: servesAZip,
	})
	dest := &fakeStore{}

	summary, err := client.FetchDay(context.Background(), testDate(t), dest)
	require.NoError(t, err)

	assert.Equal(t, Summary{Downloaded: 2}, summary)
	assert.Equal(t, []string{"2026-10-02-DO1.zip", "2026-10-02-DO1E.zip"}, dest.saved,
		"DO1 comes first, and both land under the name the URL asked for")
}

// The ordinary working day: one section published, no extra edition.
func TestFetchDayCountsAMissingEdition(t *testing.T) {
	client := douServer(t, map[Section]http.HandlerFunc{SectionDO1: servesAZip})
	dest := &fakeStore{}

	summary, err := client.FetchDay(context.Background(), testDate(t), dest)
	require.NoError(t, err)

	assert.Equal(t, Summary{Downloaded: 1, NoEdition: 1}, summary)
	assert.Equal(t, []string{"2026-10-02-DO1.zip"}, dest.saved, "a missing edition writes nothing")
}

func TestFetchDayKeepsGoingAfterASectionFails(t *testing.T) {
	client := douServer(t, map[Section]http.HandlerFunc{
		SectionDO1: func(w http.ResponseWriter, _ *http.Request) {
			w.WriteHeader(http.StatusBadGateway)
		},
		SectionDO1E: servesAZip,
	})
	dest := &fakeStore{}

	summary, err := client.FetchDay(context.Background(), testDate(t), dest)
	require.NoError(t, err, "a failed section is counted, not an aborted day")

	assert.Equal(t, Summary{Downloaded: 1, Failed: 1}, summary)
	assert.Equal(t, []string{"2026-10-02-DO1E.zip"}, dest.saved)
}

func TestFetchDayStopsWhenTheDiskIsFull(t *testing.T) {
	var editions int32
	client := douServer(t, map[Section]http.HandlerFunc{
		SectionDO1: func(w http.ResponseWriter, r *http.Request) {
			atomic.AddInt32(&editions, 1)
			servesAZip(w, r)
		},
		SectionDO1E: func(w http.ResponseWriter, r *http.Request) {
			atomic.AddInt32(&editions, 1)
			servesAZip(w, r)
		},
	})
	dest := &fakeStore{err: fmt.Errorf("writing the edition: %w", syscall.ENOSPC)}

	_, err := client.FetchDay(context.Background(), testDate(t), dest)

	require.ErrorIs(t, err, syscall.ENOSPC)
	assert.Equal(t, int32(1), atomic.LoadInt32(&editions),
		"the second section would hit the same full disk")
}

// The point of the allowlist: a way of failing nobody enumerated stops the day
// instead of being filed as one failed edition. EDQUOT is the same "nowhere to
// write" as ENOSPC, under a name the old blocklist did not carry.
func TestFetchDayStopsOnAFailureNobodyForesaw(t *testing.T) {
	var editions int32
	client := douServer(t, map[Section]http.HandlerFunc{
		SectionDO1: func(w http.ResponseWriter, r *http.Request) {
			atomic.AddInt32(&editions, 1)
			servesAZip(w, r)
		},
		SectionDO1E: func(w http.ResponseWriter, r *http.Request) {
			atomic.AddInt32(&editions, 1)
			servesAZip(w, r)
		},
	})
	dest := &fakeStore{err: fmt.Errorf("writing the edition: %w", syscall.EDQUOT)}

	_, err := client.FetchDay(context.Background(), testDate(t), dest)

	require.ErrorIs(t, err, syscall.EDQUOT)
	assert.Equal(t, int32(1), atomic.LoadInt32(&editions),
		"an unrecognised failure must not be assumed harmless")
}

// The run's deadline and a section's are the same error value, so only the
// parent context says which clock ran out. Here it is the run's: the remaining
// section cannot finish either, and asking is pointless.
func TestFetchDayStopsWhenTheRunIsOutOfTime(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	var editions int32
	client := douServer(t, map[Section]http.HandlerFunc{
		SectionDO1: func(w http.ResponseWriter, r *http.Request) {
			atomic.AddInt32(&editions, 1)
			<-ctx.Done() // outlast the run's deadline, without touching r.Context
		},
		SectionDO1E: func(w http.ResponseWriter, r *http.Request) {
			atomic.AddInt32(&editions, 1)
			servesAZip(w, r)
		},
	})

	_, err := client.FetchDay(ctx, testDate(t), &fakeStore{})

	require.ErrorIs(t, err, context.DeadlineExceeded)
	assert.Equal(t, int32(1), atomic.LoadInt32(&editions),
		"the second section would hit the same expired deadline")
}

func TestSurvivableIsTheClosedSet(t *testing.T) {
	// Wrapped, as the day actually receives them.
	for name, err := range map[string]error{
		"a transient INLABS failure": fmt.Errorf("fetching: %w", ErrTransient),
		"this section's deadline":    fmt.Errorf("streaming: %w", context.DeadlineExceeded),
		"a body that is not a zip":   fmt.Errorf("not a zip: %w", zip.ErrFormat),
	} {
		t.Run(name, func(t *testing.T) {
			assert.True(t, survivable(err), "the next section is a different URL and file")
		})
	}

	for name, err := range map[string]error{
		"a full disk":          syscall.ENOSPC,
		"a disk quota":         syscall.EDQUOT,
		"a read-only mount":    syscall.EROFS,
		"an I/O error":         syscall.EIO,
		"a dead session":       ErrSessionExpired,
		"rejected credentials": ErrLoginRejected,
		"something unforeseen": errors.New("a failure mode nobody wrote down"),
	} {
		t.Run(name, func(t *testing.T) {
			assert.False(t, survivable(err), "an unknown failure is not assumed harmless")
		})
	}
}

func TestFetchDayStopsWhenTheSessionCannotBeRenewed(t *testing.T) {
	var editions int32
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/logar.php" {
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "sessao", Path: "/"})
			return
		}
		// A session that is refused however often it is renewed.
		atomic.AddInt32(&editions, 1)
		w.Header().Set("Location", "acessar.php")
		w.WriteHeader(http.StatusFound)
	})

	_, err := client.FetchDay(context.Background(), testDate(t), &fakeStore{})

	require.ErrorIs(t, err, ErrSessionExpired)
	assert.Equal(t, int32(2), atomic.LoadInt32(&editions),
		"the first section tries twice and the day stops; DO1E would answer the same")
}

func TestFetchDayRefusesADateOutsideTheWindow(t *testing.T) {
	// Today is pinned to 2026-10-02 by newTestClient.
	for name, day := range map[string]string{
		"tomorrow":              "2026-10-03",
		"before INLABS existed": "1900-01-01",
	} {
		t.Run(name, func(t *testing.T) {
			var requests int32
			client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
				atomic.AddInt32(&requests, 1)
			})
			dest := &fakeStore{}

			summary, err := client.FetchDay(context.Background(), mustParse(t, day), dest)

			require.ErrorIs(t, err, ErrDateOutOfRange)
			assert.Zero(t, atomic.LoadInt32(&requests),
				"a day INLABS cannot serve costs no request, not even a login")
			assert.Empty(t, dest.saved)
			assert.Equal(t, Summary{}, summary)
		})
	}
}

func TestTheLogRecordsEverySectionAndNoCredential(t *testing.T) {
	var captured bytes.Buffer

	client := douServer(t, map[Section]http.HandlerFunc{
		SectionDO1: func(w http.ResponseWriter, _ *http.Request) {
			w.WriteHeader(http.StatusBadGateway)
		},
		SectionDO1E: servesAZip,
	})
	client.logger = slog.New(slog.NewTextHandler(&captured, nil))

	_, err := client.FetchDay(context.Background(), testDate(t), &fakeStore{})
	require.NoError(t, err)

	log := captured.String()
	assert.Contains(t, log, "desfecho=falhou", "the outcome per section is what the log is for")
	assert.Contains(t, log, "desfecho=baixada")
	assert.Contains(t, log, "secao=DO1E")
	assert.Contains(t, log, "erro=", "a counted failure still has to say why")

	// The client is what holds the credentials, so it is what could leak them.
	assert.NotContains(t, log, testPassword)
	assert.NotContains(t, log, testEmail)
}

func TestSummaryCountsEachOutcome(t *testing.T) {
	var summary Summary
	summary.add(Downloaded)
	summary.add(NoEdition)
	summary.add(Failed)
	summary.add(Failed)

	assert.Equal(t, Summary{Downloaded: 1, NoEdition: 1, Failed: 2}, summary)
}

func TestANilLoggerIsAccepted(t *testing.T) {
	client, err := New(Credentials{Email: testEmail, Password: testPassword}, nil)
	require.NoError(t, err)

	require.NotNil(t, client.logger)
	client.logger.Info("this must not panic")
}

var _ Saver = (*fakeStore)(nil)
