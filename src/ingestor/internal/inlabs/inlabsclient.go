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

	// loginPage is where INLABS redirects a session-less request. The Location
	// comes relative, so the comparison is on the path only.
	loginPage = "acessar.php"

	// maxAttempts counts the first try, so the retry cap is maxAttempts-1.
	maxAttempts = 3

	retryWaitMin = 200 * time.Millisecond
	retryWaitMax = 10 * time.Second

	// loginTimeout covers connecting and the login round trip, nothing else.
	loginTimeout = 30 * time.Second
)

// What a request can mean other than success. None is a program error.
var (
	ErrNoEdition = errors.New("no edition published for this date and section")

	// ErrDateOutOfRange is a day INLABS cannot have published, and costs no
	// request.
	ErrDateOutOfRange = errors.New("INLABS serves no edition for this date")

	// ErrSessionExpired escapes only after a re-login failed to restore the
	// session.
	ErrSessionExpired = errors.New("the INLABS session is no longer valid")

	// ErrLoginRejected: wrong or expired credentials, or a blocked account.
	ErrLoginRejected = errors.New("INLABS refused the credentials")

	ErrTransient = errors.New("INLABS failed in a way worth retrying")
)

// Credentials are the INLABS sign-in (free, at https://inlabs.in.gov.br/),
// given once to New.
type Credentials struct {
	Email    string
	Password string
}

// Client talks to INLABS, session included: it logs in when it has none and
// renews one that is refused. One Client serves one run at a time — nothing
// guards the session against two concurrent renewals.
type Client struct {
	http  *http.Client
	retry *retryablehttp.Client
	creds Credentials

	// clock and location decide which day it is in Brasília. Fields, so a test
	// can pin the day.
	clock    func() time.Time
	location *time.Location

	// logger reports each edition as the day is walked; a run lasts minutes.
	logger *slog.Logger

	// baseURL is a field, not the const, so a test can point a real client at a
	// test server.
	baseURL string
}

// New builds a client for these credentials; a nil logger discards the progress.
// Empty credentials are refused here, where it is still a configuration error.
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
		// becomes a 200 whose HTML body would be written out as a corrupt zip.
		CheckRedirect: func(*http.Request, []*http.Request) error {
			return http.ErrUseLastResponse
		},
		// Phase deadlines only: a global Client.Timeout would cut a large
		// download short.
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

// backoff is ours because neither ready-made one does both: DefaultBackoff
// honours Retry-After without jitter, LinearJitterBackoff the reverse.
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
	// Half to all of the computed wait, so several runs do not line up.
	return time.Duration(exponential * (0.5 + 0.5*rand.Float64()))
}

// retryAfter honours only the delay-seconds form; an HTTP-date falls through to
// the curve.
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
// login accepts.
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

// login authenticates and leaves the session cookie in the jar; unexported,
// because the session is this package's to keep. Its own deadline out of ctx
// keeps one unanswered POST from stalling a run for a download's worth of time.
func (c *Client) login(ctx context.Context) error {
	site, err := url.Parse(c.baseURL)
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(ctx, loginTimeout)
	defer cancel()

	// Drop the previous session first: otherwise a refused re-login looks like a
	// success, because the check below finds the old cookie still in the jar.
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

	// The cookie is the only proof: with wrong credentials INLABS still answers
	// 200, with an HTML page. No body and no e-mail in the error, which is
	// logged.
	for _, cookie := range c.http.Jar.Cookies(resp.Request.URL) {
		if cookie.Name == inlabsSessionCookie {
			return nil
		}
	}
	return fmt.Errorf("%w: no session cookie came back", ErrLoginRejected)
}

// fetchSection asks for one edition and returns its body for the caller to
// stream; it writes nothing. The session is handled here: it logs in when the
// jar is empty, and renews once when INLABS says the session is gone.
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

	// One renewal, never a loop: a session minted seconds ago being refused
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

// redirectsToLogin: a 302 whose relative Location is the login page.
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
// body is the login page.
func looksLikeAPage(resp *http.Response) bool {
	return resp.StatusCode == http.StatusOK &&
		strings.HasPrefix(resp.Header.Get("Content-Type"), "text/html")
}

// drain empties and closes a body we are not handing over, so the connection
// goes back to the pool.
func drain(resp *http.Response) {
	_, _ = io.Copy(io.Discard, resp.Body)
	_ = resp.Body.Close()
}
