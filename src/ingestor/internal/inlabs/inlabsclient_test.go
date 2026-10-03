package inlabs

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// The credentials every test logs in with. The password is distinctive on
// purpose: the rejection tests look for it inside error messages.
const (
	testEmail    = "fulano@exemplo.com"
	testPassword = "s3nha-que-nao-pode-vazar"
)

// newTestClient points a real client at a test server. Only the base URL
// changes, so what the tests exercise — form, headers, cookie handling — is
// the same code that talks to inlabs.in.gov.br.
//
// A note for every handler below: assert is allowed inside them, require is
// not. require calls t.FailNow, which only works on the test's own goroutine.
func newTestClient(t *testing.T, handler http.HandlerFunc) *Client {
	t.Helper()

	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)

	client, err := New()
	require.NoError(t, err)
	client.baseURL = server.URL

	return client
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

	require.NoError(t, client.Login(context.Background(), testEmail, testPassword))
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

	require.NoError(t, client.Login(context.Background(), testEmail, testPassword))

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

			err := client.Login(context.Background(), testEmail, testPassword)
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

	err := client.Login(context.Background(), testEmail, testPassword)
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

	err := client.Login(ctx, testEmail, testPassword)
	require.ErrorIs(t, err, context.Canceled)
}
