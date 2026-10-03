package inlabs

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"math"
	"math/rand/v2"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/hashicorp/go-retryablehttp"
)

const (
	defaultBaseURL      = "https://inlabs.in.gov.br"
	origem              = "736372697074"
	inlabsSessionCookie = "inlabs_session_cookie"
	userAgent           = "conselhos-vivos-fetch/0.1"

	// loginPage is where INLABS redirects a request with no live session. The
	// Location it sends is relative, so the comparison is on the path only.
	loginPage = "acessar.php"

	// maxAttempts counts the first try, so the retry cap is maxAttempts-1. The
	// script this replaces recurses without a cap; a number here is the fix.
	maxAttempts = 3

	retryWaitMin = 200 * time.Millisecond
	retryWaitMax = 10 * time.Second

	// loginTimeout covers connecting and the login round trip, nothing else.
	loginTimeout = 30 * time.Second
)

// What a request can mean other than success. None of them is a program error:
// a missing edition is an ordinary answer.
var (
	ErrNoEdition = errors.New("no edition published for this date and section")

	// ErrDateOutOfRange is a day INLABS cannot have published: after today, or
	// before the archive begins. It costs no request.
	ErrDateOutOfRange = errors.New("INLABS serves no edition for this date")

	// ErrSessionExpired escapes only after a re-login failed to restore the
	// session, so the next edition would be answered the same way.
	ErrSessionExpired = errors.New("the INLABS session is no longer valid")

	// ErrLoginRejected is a dead end of the same kind: wrong or expired
	// credentials, or a blocked account.
	ErrLoginRejected = errors.New("INLABS refused the credentials")

	ErrTransient = errors.New("INLABS failed in a way worth retrying")
)

// Credentials are the INLABS sign-in (free, at https://inlabs.in.gov.br/). They
// are given once, to New, and never travel through a call.
type Credentials struct {
	Email    string
	Password string
}

// Client talks to INLABS, session included: it logs in when it has none and
// renews one that is refused, so no caller ever logs in itself.
//
// One Client serves one run at a time — nothing here guards the session against
// two concurrent renewals.
type Client struct {
	http  *http.Client
	retry *retryablehttp.Client
	creds Credentials

	// clock and location decide which day it is in Brasília, and so which dates
	// can have an edition yet. Fields, so a test can pin the day.
	clock    func() time.Time
	location *time.Location

	// logger reports each edition as the day is walked: a run lasts minutes, so
	// the progress has to show before the summary does.
	logger *slog.Logger

	// baseURL is a field, and not the const, so the tests can point a real
	// client at a test server without reaching the network.
	baseURL string
}

// New builds a client for these credentials, logging its progress to logger; a
// nil logger discards it. Empty credentials are refused here, where the error is
// still a configuration error rather than a failed download.
func New(creds Credentials, logger *slog.Logger) (*Client, error) {
	if creds.Email == "" || creds.Password == "" {
		return nil, fmt.Errorf("the INLABS credentials are incomplete: %w", ErrLoginRejected)
	}
	if logger == nil {
		logger = slog.New(slog.DiscardHandler)
	}

	location, err := LoadLocation()
	if err != nil {
		return nil, err
	}

	jar, err := cookiejar.New(nil)
	if err != nil {
		return nil, err
	}

	inner := &http.Client{
		Jar: jar,
		// Do not follow the 302 to the login page: followed, an expired session
		// becomes a 200 whose body is HTML, which would be written out as a
		// corrupt zip. This is what lets Fetch see the redirect itself.
		CheckRedirect: func(*http.Request, []*http.Request) error {
			return http.ErrUseLastResponse
		},
		// Phase deadlines only. A global Client.Timeout would abort a
		// legitimate download of a large edition partway through.
		Transport: &http.Transport{
			Proxy:                 http.ProxyFromEnvironment,
			DialContext:           (&net.Dialer{Timeout: 10 * time.Second}).DialContext,
			TLSHandshakeTimeout:   10 * time.Second,
			ResponseHeaderTimeout: 30 * time.Second,
			IdleConnTimeout:       90 * time.Second,
		},
	}

	return &Client{
		http:     inner,
		creds:    creds,
		clock:    time.Now,
		location: location,
		logger:   logger,
		retry: &retryablehttp.Client{
			HTTPClient:   inner,
			RetryMax:     maxAttempts - 1,
			RetryWaitMin: retryWaitMin,
			RetryWaitMax: retryWaitMax,
			CheckRetry:   retryablehttp.DefaultRetryPolicy,
			Backoff:      backoff,
			// The library's logger writes to stderr outside the structured log.
			Logger: nil,
		},
		baseURL: defaultBaseURL,
	}, nil
}

// backoff is ours because neither of the library's ready-made ones satisfies
// the requirement on its own: DefaultBackoff honours Retry-After but has no
// jitter, and LinearJitterBackoff has jitter and ignores the header.
func backoff(min, max time.Duration, attempt int, resp *http.Response) time.Duration {
	if wait, ok := retryAfter(resp); ok {
		if wait > max {
			return max
		}
		return wait
	}

	exponential := float64(min) * math.Pow(2, float64(attempt))
	if exponential > float64(max) {
		exponential = float64(max)
	}
	// Jitter between half and all of the computed wait, so retries from several
	// runs do not line up on the same instant.
	return time.Duration(exponential * (0.5 + 0.5*rand.Float64()))
}

// retryAfter reads the header for the statuses that carry it. Only the
// delay-seconds form is honoured; an HTTP-date falls through to the curve.
func retryAfter(resp *http.Response) (time.Duration, bool) {
	if resp == nil {
		return 0, false
	}
	if resp.StatusCode != http.StatusTooManyRequests && resp.StatusCode != http.StatusServiceUnavailable {
		return 0, false
	}
	seconds, err := strconv.Atoi(strings.TrimSpace(resp.Header.Get("Retry-After")))
	if err != nil || seconds < 0 {
		return 0, false
	}
	return time.Duration(seconds) * time.Second, true
}

// TODO: may remove this is okay to fail after the request anyway
// hasSession reports whether the jar holds a session cookie — the same proof
// login accepts, asked before a request instead of after one.
func (c *Client) hasSession() bool {
	site, err := url.Parse(c.baseURL)
	if err != nil {
		return false
	}
	for _, cookie := range c.http.Jar.Cookies(site) {
		if cookie.Name == inlabsSessionCookie {
			return true
		}
	}
	return false
}

// login authenticates and leaves the session cookie in the jar. It is
// unexported: the session is this package's to keep.
//
// It carves its own deadline out of ctx, so one unanswered POST cannot stall a
// run for as long as a legitimate download may take.
func (c *Client) login(ctx context.Context) error {
	site, err := url.Parse(c.baseURL)
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(ctx, loginTimeout)
	defer cancel()

	// Drop the previous session before asking for a new one. Without this, a
	// refused re-login would look like a success: the old cookie is still in
	// the jar, and the check below would find it.
	c.http.Jar.SetCookies(site, []*http.Cookie{
		{Name: inlabsSessionCookie, Value: "", Path: "/", MaxAge: -1},
	})

	form := url.Values{"email": {c.creds.Email}, "password": {c.creds.Password}}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+"/logar.php", strings.NewReader(form.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("origem", origem)
	req.Header.Set("User-Agent", userAgent)

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("logging in: %w", err)
	}
	// Drain before closing: the transport only reuses a connection whose body
	// reached EOF.
	defer resp.Body.Close()
	_, _ = io.Copy(io.Discard, resp.Body)

	// The cookie is the only proof of a login: with wrong credentials INLABS
	// still answers 200, with an HTML page. No body and no e-mail in the error,
	// which goes to the log.
	for _, cookie := range c.http.Jar.Cookies(resp.Request.URL) {
		if cookie.Name == inlabsSessionCookie {
			return nil
		}
	}
	return fmt.Errorf("%w: no session cookie came back", ErrLoginRejected)
}

// fetchSection asks for one edition and returns its body for the caller to
// stream; it writes nothing.
//
// The session is handled here: it logs in when the jar is empty, and when INLABS
// answers that the session is gone it logs in again and asks once more.
func (c *Client) fetchSection(ctx context.Context, date Date, section Section) (io.ReadCloser, error) {
	if !c.hasSession() {
		if err := c.login(ctx); err != nil {
			return nil, err
		}
	}

	body, err := c.request(ctx, date, section)
	if !errors.Is(err, ErrSessionExpired) {
		return body, err
	}

	// One renewal, never a loop: a session minted seconds ago being refused too
	// means the session is not what is wrong.
	if err := c.login(ctx); err != nil {
		return nil, err
	}

	body, err = c.request(ctx, date, section)
	if errors.Is(err, ErrSessionExpired) {
		return nil, fmt.Errorf("the session expired again right after logging in: %w", err)
	}
	return body, err
}

func (c *Client) request(ctx context.Context, date Date, section Section) (io.ReadCloser, error) {
	// TODO: Zip name should not be handled here
	name := ZipName(date, section)
	query := url.Values{"p": {date.String()}, "dl": {name}}

	req, err := retryablehttp.NewRequestWithContext(ctx, http.MethodGet,
		c.baseURL+"/index.php?"+query.Encode(), nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("origem", origem)
	req.Header.Set("User-Agent", userAgent)

	resp, err := c.retry.Do(req)
	if err != nil {
		// A cancelled context is the caller's decision, not a server failure.
		if ctxErr := ctx.Err(); ctxErr != nil {
			return nil, ctxErr
		}
		return nil, fmt.Errorf("fetching %s: %w", name, ErrTransient)
	}

	// Status before Content-Type: the redirect itself carries text/html, so
	// reading the type first would classify it as a page body.
	switch {
	case resp.StatusCode == http.StatusNotFound:
		drain(resp)
		return nil, fmt.Errorf("%s: %w", name, ErrNoEdition)
	case redirectsToLogin(resp), looksLikeAPage(resp):
		drain(resp)
		return nil, fmt.Errorf("%s: %w", name, ErrSessionExpired)
	case resp.StatusCode != http.StatusOK:
		drain(resp)
		return nil, fmt.Errorf("fetching %s: unexpected status %s: %w", name, resp.Status, ErrTransient)
	}

	return resp.Body, nil
}

// redirectsToLogin reports the answer INLABS gives a request with no live
// session: a 302 whose Location is the login page, sent relative.
func redirectsToLogin(resp *http.Response) bool {
	// TODO: no builtins for it ?
	if resp.StatusCode < 300 || resp.StatusCode > 399 {
		return false
	}
	location, err := url.Parse(resp.Header.Get("Location"))
	if err != nil {
		return false
	}
	return strings.HasSuffix(strings.TrimSuffix(location.Path, "/"), loginPage)
}

// looksLikeAPage catches the other shape of an expired session: a 200 whose
// body is the login page. An edition is a zip, never HTML.
func looksLikeAPage(resp *http.Response) bool {
	return resp.StatusCode == http.StatusOK &&
		strings.HasPrefix(resp.Header.Get("Content-Type"), "text/html")
}

// drain empties and closes a body we are not handing to the caller, so the
// connection goes back to the pool instead of being thrown away.
func drain(resp *http.Response) {
	_, _ = io.Copy(io.Discard, resp.Body)
	_ = resp.Body.Close()
}
