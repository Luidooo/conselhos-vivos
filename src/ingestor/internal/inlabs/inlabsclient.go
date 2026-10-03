package inlabs

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strings"
)

const (
	defaultBaseURL      = "https://inlabs.in.gov.br"
	origem              = "736372697074"
	inlabsSessionCookie = "inlabs_session_cookie"
)

type Client struct {
	http *http.Client

	// baseURL is a field, and not the const, so the tests can point a real
	// client at a test server without reaching the network.
	baseURL string
}

func New() (*Client, error) {
	jar, err := cookiejar.New(nil)
	if err != nil {
		return nil, err
	}
	return &Client{
		http: &http.Client{
			Jar: jar,
		},
		baseURL: defaultBaseURL,
	}, nil

}

// TODO: make some use of the timeout of the cookie
func (c *Client) Login(ctx context.Context, email, password string) error {
	form := url.Values{"email": {email}, "password": {password}}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/logar.php", strings.NewReader(form.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("origem", origem)

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("logging in: %w", err)
	}
	// Close is mandatory: the body holds the connection open. Drain it
	// first because the transport only reuses a connection whose body
	// reached EOF; closing early costs a new TCP and TLS handshake.
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)

	for _, cookie := range c.http.Jar.Cookies(resp.Request.URL) {
		if cookie.Name == inlabsSessionCookie {
			return nil
		}
	}

	return errors.New("login rejected: no session cookie")
}
