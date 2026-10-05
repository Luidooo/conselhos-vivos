package inlabs

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"sync/atomic"
	"testing"
	"time"

	"cloud.google.com/go/civil"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"conselhos-vivos/internal/store"
)

// The credentials every test logs in with. The password is distinctive on
// purpose: the rejection tests look for it inside error messages.
const (
	testEmail    = "fulano@exemplo.com"
	testPassword = "s3nha-que-nao-pode-vazar"
)

// testNow pins the clock, so the date window does not change overnight.
const testNow = "2026-10-02T12:00:00Z"

// newTestClient points a real client at a test server. Only the base URL and
// the clock change, so what the tests exercise is the same code that talks to
// inlabs.in.gov.br. It comes back logged out, as a real run starts.
//
// A note for every handler below: assert is allowed inside them, require is
// not. require calls t.FailNow, which only works on the test's own goroutine.
func newTestClient(t *testing.T, handler http.HandlerFunc) *Client {
	t.Helper()

	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)

	client, err := New(Credentials{Email: testEmail, Password: testPassword}, nil)
	require.NoError(t, err)
	client.baseURL = server.URL

	now, err := time.Parse(time.RFC3339, testNow)
	require.NoError(t, err)
	client.clock = func() time.Time { return now }

	return client
}

// newSignedInClient has a session already in the jar, for the tests that are
// about a download and not about how it got a session.
func newSignedInClient(t *testing.T, handler http.HandlerFunc) *Client {
	t.Helper()

	client := newTestClient(t, handler)
	client.http.Jar.SetCookies(mustURL(t, client.baseURL), []*http.Cookie{
		{Name: inlabsSessionCookie, Value: "sessao-de-teste", Path: "/"},
	})

	return client
}

// fakeStore stands in for the disk, including the failure a real one only
// shows when it is full.
type fakeStore struct {
	saved []string
	err   error
}

func (s *fakeStore) Save(name string, body io.Reader) (store.Receipt, error) {
	size, _ := io.Copy(io.Discard, body)
	s.saved = append(s.saved, name)
	if s.err != nil {
		return store.Receipt{}, s.err
	}
	return store.Receipt{Path: name, Size: size}, nil
}

func TestLoginSpeaksTheProtocol(t *testing.T) {
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, http.MethodPost, r.Method)
		assert.Equal(t, "/logar.php", r.URL.Path)
		assert.Equal(t, "application/x-www-form-urlencoded", r.Header.Get("Content-Type"))
		assert.Equal(t, origem, r.Header.Get("origem"))

		if assert.NoError(t, r.ParseForm()) {
			assert.Equal(t, testEmail, r.PostForm.Get("email"))
			assert.Equal(t, testPassword, r.PostForm.Get("password"))
		}

		http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "abc123", Path: "/"})
	})

	require.NoError(t, client.login(context.Background()))
}

func TestLoginKeepsTheSessionForTheRequestsThatFollow(t *testing.T) {
	const session = "k8c3f9a1"

	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/logar.php" {
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: session, Path: "/"})
			return
		}

		// What the downloads will depend on: the jar replaying the session on
		// its own, with nobody passing the cookie around by hand.
		cookie, err := r.Cookie(inlabsSessionCookie)
		if assert.NoError(t, err) {
			assert.Equal(t, session, cookie.Value)
		}
	})

	require.NoError(t, client.login(context.Background()))

	resp, err := client.http.Get(client.baseURL + "/index.php")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode, "the second request should have reached the handler")
}

func TestLoginWithoutSessionCookieIsRejected(t *testing.T) {
	// Each case answers something the reference script would read as a
	// success. The session cookie is what decides, never the status.
	handlers := map[string]http.HandlerFunc{
		"200 with the login page": func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/html; charset=UTF-8")
			io.WriteString(w, "<html><body>credenciais invalidas</body></html>")
		},
		"200 with some other cookie": func(w http.ResponseWriter, r *http.Request) {
			http.SetCookie(w, &http.Cookie{Name: "PHPSESSID", Value: "irrelevante", Path: "/"})
		},
		"302 to the login page": func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path == "/logar.php" {
				w.Header().Set("Location", "/acessar.php")
				w.WriteHeader(http.StatusFound)
				return
			}
			io.WriteString(w, "<html><body>faca login</body></html>")
		},
		"500": func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
		},
	}

	for name, handler := range handlers {
		t.Run(name, func(t *testing.T) {
			client := newTestClient(t, handler)

			err := client.login(context.Background())
			require.Error(t, err, "no session cookie must never pass as a login")
		})
	}
}

func TestLoginErrorCarriesNoSecret(t *testing.T) {
	// The server echoes the credentials back, so this test is what fails the
	// day someone attaches the response body to the error.
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, "<html>senha "+testPassword+" invalida para "+testEmail+"</html>")
	})

	err := client.login(context.Background())
	require.Error(t, err)
	assert.NotContains(t, err.Error(), testPassword)
	assert.NotContains(t, err.Error(), testEmail)
}

func TestLoginRespectsTheContext(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// The handler stalls on a channel of our own, not on r.Context(): the
	// server only learns the client hung up through a background read it does
	// not start while the request body sits unread, and this handler never
	// reads the form. Waiting on r.Context() here deadlocks server.Close.
	released := make(chan struct{})
	// A defer here runs before any t.Cleanup, so the stalled handler returns
	// before the test server is closed. A t.Cleanup would deadlock: cleanups
	// run last in, first out, and server.Close was registered after ours.
	defer close(released)

	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		cancel() // the caller gives up while the server is still thinking
		<-released
	})

	err := client.login(ctx)
	require.ErrorIs(t, err, context.Canceled)
}

// --- Fetch -------------------------------------------------------------------

// zipBody is the smallest valid zip archive: the end-of-central-directory
// record alone, which archive/zip accepts as an empty archive. Enough to prove
// Fetch hands back the body untouched.
func zipBody() []byte {
	return []byte("PK\x05\x06" + "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
}

func TestFetchReturnsTheEditionBody(t *testing.T) {
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/index.php", r.URL.Path)
		assert.Equal(t, "2026-10-02", r.URL.Query().Get("p"))
		assert.Equal(t, "2026-10-02-DO1.zip", r.URL.Query().Get("dl"))
		assert.Equal(t, origem, r.Header.Get("origem"))
		assert.Contains(t, r.Header.Get("User-Agent"), "conselhos-vivos")

		w.Write(zipBody())
	})

	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)
	require.NoError(t, err)
	defer body.Close()

	got, err := io.ReadAll(body)
	require.NoError(t, err)
	assert.Equal(t, zipBody(), got)
}

func TestFetchAsksForTheExtraEdition(t *testing.T) {
	var asked string
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		asked = r.URL.Query().Get("dl")
		w.Write(zipBody())
	})

	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1E)
	require.NoError(t, err)
	require.NoError(t, body.Close())

	assert.Equal(t, "2026-10-02-DO1E.zip", asked)
}

// The two cases the reference implementation gets wrong: a 302 it follows into
// a 200, and a 200 whose body is the login page. Both go through request, the
// single GET, so what is under test is the classification alone.
func TestARedirectToTheLoginPageIsSeenAsAnExpiredSession(t *testing.T) {
	var calls int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		if r.URL.Path == "/acessar.php" {
			assert.Fail(t, "the redirect was followed; the login page must never be read as content")
			return
		}
		// Relative Location and text/html on the redirect itself, as the real
		// endpoint answers (see the plan's Sources).
		w.Header().Set("Location", "acessar.php")
		w.Header().Set("Content-Type", "text/html; charset=UTF-8")
		w.WriteHeader(http.StatusFound)
	})

	_, err := client.request(context.Background(), testDate(t), SectionDO1)

	require.ErrorIs(t, err, ErrSessionExpired)
	assert.Equal(t, int32(1), atomic.LoadInt32(&calls), "the request itself must not retry a redirect")
}

func TestAnHTMLBodyIsSeenAsAnExpiredSession(t *testing.T) {
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=UTF-8")
		io.WriteString(w, "<html><body>faca login</body></html>")
	})

	_, err := client.request(context.Background(), testDate(t), SectionDO1)

	require.ErrorIs(t, err, ErrSessionExpired)
}

func TestFetchTreatsNotFoundAsNoEdition(t *testing.T) {
	var calls int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(http.StatusNotFound)
	})

	_, err := client.fetchSection(context.Background(), testDate(t), SectionDO1E)

	require.ErrorIs(t, err, ErrNoEdition)
	assert.Equal(t, int32(1), atomic.LoadInt32(&calls), "a missing edition is not retried")
}

func TestFetchRetriesAServerError(t *testing.T) {
	var calls int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		if atomic.AddInt32(&calls, 1) == 1 {
			w.WriteHeader(http.StatusInternalServerError)
			return
		}
		w.Write(zipBody())
	})

	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)
	require.NoError(t, err)
	require.NoError(t, body.Close())

	assert.Equal(t, int32(2), atomic.LoadInt32(&calls), "the second attempt should succeed")
}

func TestFetchGivesUpOnAPersistentServerError(t *testing.T) {
	var calls int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(http.StatusBadGateway)
	})

	_, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)

	require.ErrorIs(t, err, ErrTransient)
	assert.Equal(t, int32(maxAttempts), atomic.LoadInt32(&calls), "it should stop at the cap, not recurse")
}

func TestFetchWaitsTheRetryAfterHeader(t *testing.T) {
	var calls int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		if atomic.AddInt32(&calls, 1) == 1 {
			w.Header().Set("Retry-After", "1")
			w.WriteHeader(http.StatusTooManyRequests)
			return
		}
		w.Write(zipBody())
	})

	start := time.Now()
	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)
	require.NoError(t, err)
	require.NoError(t, body.Close())

	assert.GreaterOrEqual(t, time.Since(start), 900*time.Millisecond,
		"the header asked for a second; backoff must respect it instead of its own curve")
}

func TestFetchStopsWhenTheContextIsCancelled(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		cancel() // the caller gives up while the server is answering 500
		w.WriteHeader(http.StatusInternalServerError)
	})

	start := time.Now()
	_, err := client.fetchSection(ctx, testDate(t), SectionDO1)

	require.ErrorIs(t, err, context.Canceled)
	assert.Less(t, time.Since(start), 5*time.Second, "cancelling must cut the backoff wait short")
}

func TestFetchErrorsCarryNoSecret(t *testing.T) {
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, "<html>senha "+testPassword+" para "+testEmail+"</html>")
	})
	client.http.Jar.SetCookies(mustURL(t, client.baseURL), []*http.Cookie{
		{Name: inlabsSessionCookie, Value: testPassword},
	})

	_, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)

	require.Error(t, err)
	assert.NotContains(t, err.Error(), testPassword)
	assert.NotContains(t, err.Error(), testEmail)
}

func testDate(t *testing.T) Date {
	t.Helper()

	date, err := civil.ParseDate("2026-10-02")
	require.NoError(t, err)
	return date
}

func mustURL(t *testing.T, raw string) *url.URL {
	t.Helper()

	parsed, err := url.Parse(raw)
	require.NoError(t, err)
	return parsed
}

// A refused re-login used to pass, because the cookie from the first session was
// still in the jar and the check found it there. Credentials rotated mid-run
// would have looked like a live session.
func TestSecondLoginIsProvedByItsOwnResponse(t *testing.T) {
	var calls int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		if atomic.AddInt32(&calls, 1) == 1 {
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "first", Path: "/"})
			return
		}
		// The credentials stopped working: 200, a page, and no cookie.
		w.Header().Set("Content-Type", "text/html; charset=UTF-8")
		io.WriteString(w, "<html><body>credenciais invalidas</body></html>")
	})

	require.NoError(t, client.login(context.Background()))
	require.Error(t, client.login(context.Background()),
		"the second login must fail on its own answer, not inherit the first session")
}

// --- the session, as fetchSection keeps it -----------------------------------

func TestNewRefusesIncompleteCredentials(t *testing.T) {
	for name, creds := range map[string]Credentials{
		"no e-mail":   {Password: testPassword},
		"no password": {Email: testEmail},
		"neither":     {},
	} {
		t.Run(name, func(t *testing.T) {
			_, err := New(creds, nil)

			require.ErrorIs(t, err, ErrLoginRejected,
				"missing credentials should fail at construction, not at the first download")
		})
	}
}

func TestTheFirstEditionOfARunLogsItselfIn(t *testing.T) {
	var paths []string
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		paths = append(paths, r.URL.Path)
		if r.URL.Path == "/logar.php" {
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "nova", Path: "/"})
			return
		}
		w.Write(zipBody())
	})

	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)
	require.NoError(t, err, "nobody logged in from outside; the client has to do it")
	require.NoError(t, body.Close())

	assert.Equal(t, []string{"/logar.php", "/index.php"}, paths, "the login comes first, once")
}

func TestASessionAlreadyInHandIsNotLoggedInAgain(t *testing.T) {
	var logins int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/logar.php" {
			atomic.AddInt32(&logins, 1)
		}
		w.Write(zipBody())
	})

	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)
	require.NoError(t, err)
	require.NoError(t, body.Close())

	assert.Zero(t, atomic.LoadInt32(&logins), "a live session must not be renewed for nothing")
}

func TestAnExpiredSessionIsRenewedOnceAndTheEditionRetried(t *testing.T) {
	var logins, editions int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/logar.php" {
			atomic.AddInt32(&logins, 1)
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "renovada", Path: "/"})
			return
		}
		// The session the test seeded is stale; the renewed one works.
		if atomic.AddInt32(&editions, 1) == 1 {
			w.Header().Set("Content-Type", "text/html; charset=UTF-8")
			io.WriteString(w, "<html><body>faca login</body></html>")
			return
		}
		w.Write(zipBody())
	})

	body, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)
	require.NoError(t, err, "an expired session is the client's problem to solve, not the caller's")
	require.NoError(t, body.Close())

	assert.Equal(t, int32(1), atomic.LoadInt32(&logins), "exactly one renewal")
	assert.Equal(t, int32(2), atomic.LoadInt32(&editions))
}

func TestASessionRefusedTwiceGivesUp(t *testing.T) {
	var logins, editions int32
	client := newSignedInClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/logar.php" {
			atomic.AddInt32(&logins, 1)
			http.SetCookie(w, &http.Cookie{Name: inlabsSessionCookie, Value: "renovada", Path: "/"})
			return
		}
		atomic.AddInt32(&editions, 1)
		w.Header().Set("Location", "acessar.php")
		w.WriteHeader(http.StatusFound)
	})

	_, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)

	require.ErrorIs(t, err, ErrSessionExpired)
	assert.Contains(t, err.Error(), "expired again")
	assert.Equal(t, int32(1), atomic.LoadInt32(&logins), "it must not loop logging in forever")
	assert.Equal(t, int32(2), atomic.LoadInt32(&editions), "one try, one renewal, one more try")
}

func TestRejectedCredentialsStopBeforeTheEdition(t *testing.T) {
	var editions int32
	client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/logar.php" {
			atomic.AddInt32(&editions, 1)
		}
		// 200, a page, no cookie: what INLABS answers a wrong password with.
		w.Header().Set("Content-Type", "text/html; charset=UTF-8")
		io.WriteString(w, "<html><body>credenciais invalidas</body></html>")
	})

	_, err := client.fetchSection(context.Background(), testDate(t), SectionDO1)

	require.ErrorIs(t, err, ErrLoginRejected)
	assert.Zero(t, atomic.LoadInt32(&editions), "there is no point asking for an edition unlogged")
}
