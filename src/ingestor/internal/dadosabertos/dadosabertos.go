// Package dadosabertos downloads a whole month of the Diário Oficial from the
// Imprensa Nacional's open data: one zip per month and section, public (CC0),
// with no sign-in, and with the same XML as INLABS inside, extra editions
// included. The month is published about two weeks after it ends.
//
// Only Section 1 is fetched: it is where the conselhos' acts come out.
package dadosabertos

import (
	"context"
	"errors"
	"fmt"
	"html"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"conselhos-vivos/internal/store"
)

const (
	defaultBaseURL = "https://www.in.gov.br"

	// listingPath is the page that links a month's zips. Each link carries a
	// document UUID, so the zip's address cannot be built, only found.
	listingPath = "/acesso-a-informacao/dados-abertos/base-de-dados"

	userAgent = "conselhos-vivos-ingest/0.1"

	// maxListing caps how much of the page is read; it is about 150 KB.
	maxListing = 5 << 20

	// monthTimeout covers the page and the download, body included: a month of
	// Section 1 is about 50 MB. A global http.Client.Timeout would cut it short.
	monthTimeout = 10 * time.Minute
)

// ErrNotPublished is a month whose zip the listing does not link yet: the
// current one, or the last one before about the 15th.
var ErrNotPublished = errors.New("the month is not published in the open data yet")

// Month is a calendar month, the unit the open data is published in.
type Month struct {
	Year  int
	Month time.Month
}

// ParseMonth accepts one spelling and no other: YYYY-MM.
func ParseMonth(raw string) (Month, error) {
	parsed, err := time.Parse("2006-01", raw)
	if err != nil {
		return Month{}, fmt.Errorf("want a month as YYYY-MM, like 2026-08")
	}
	return Month{Year: parsed.Year(), Month: parsed.Month()}, nil
}

func (m Month) String() string {
	return fmt.Sprintf("%04d-%02d", m.Year, int(m.Month))
}

// ZipName is the zip's name as the Imprensa Nacional publishes it, kept on
// disk as is: Section 1 of August 2026 is S01082026.zip.
func ZipName(m Month) string {
	return fmt.Sprintf("S01%02d%04d.zip", int(m.Month), m.Year)
}

// monthNames is the listing's mes parameter. The page takes "Marco" as well,
// but this is how it spells the months itself.
var monthNames = [...]string{"", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
	"Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"}

// Saver is where the zip lands. Has lets a month already on disk cost no
// request: the archive of a closed month does not change.
type Saver interface {
	Has(name string) (bool, error)
	Save(name string, body io.Reader) (store.Receipt, error)
}

// Outcome is what happened to the month.
type Outcome string

const (
	Downloaded   Outcome = "baixada"
	AlreadyThere Outcome = "ja-baixada"
)

// Client talks to www.in.gov.br.
type Client struct {
	http   *http.Client
	logger *slog.Logger

	// baseURL is a field, not the const, so a test can point a real client at a
	// test server.
	baseURL string
}

// New builds a client; a nil logger discards the progress.
func New(logger *slog.Logger) *Client {
	if logger == nil {
		logger = slog.New(slog.DiscardHandler)
	}
	return &Client{
		http: &http.Client{
			// Phase deadlines only, as in the inlabs client; the whole month is
			// bounded by monthTimeout.
			Transport: &http.Transport{
				Proxy:                 http.ProxyFromEnvironment,
				DialContext:           (&net.Dialer{Timeout: 10 * time.Second}).DialContext,
				TLSHandshakeTimeout:   10 * time.Second,
				ResponseHeaderTimeout: 30 * time.Second,
				IdleConnTimeout:       90 * time.Second,
			},
		},
		logger:  logger,
		baseURL: defaultBaseURL,
	}
}

// FetchMonth puts the month's Section 1 zip in dest, unless it is there
// already. A failure leaves nothing under the zip's name: Save only publishes a
// whole zip, so running again is the retry.
func (c *Client) FetchMonth(ctx context.Context, m Month, dest Saver) (Outcome, error) {
	name := ZipName(m)

	has, err := dest.Has(name)
	if err != nil {
		return "", err
	}
	if has {
		c.logger.Info("mes", "mes", m.String(), "zip", name, "desfecho", string(AlreadyThere))
		return AlreadyThere, nil
	}

	ctx, cancel := context.WithTimeout(ctx, monthTimeout)
	defer cancel()

	link, err := c.findLink(ctx, m, name)
	if err != nil {
		return "", err
	}

	resp, err := c.get(ctx, link)
	if err != nil {
		return "", fmt.Errorf("downloading %s: %w", name, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("downloading %s: unexpected status %s", name, resp.Status)
	}

	receipt, err := dest.Save(name, resp.Body)
	if err != nil {
		return "", err
	}
	c.logger.Info("mes", "mes", m.String(), "zip", name, "desfecho", string(Downloaded), "bytes", receipt.Size)
	return Downloaded, nil
}

// findLink reads the month's listing and returns the address of the zip called
// name.
func (c *Client) findLink(ctx context.Context, m Month, name string) (string, error) {
	query := url.Values{"ano": {strconv.Itoa(m.Year)}, "mes": {monthNames[m.Month]}}
	listing := c.baseURL + listingPath + "?" + query.Encode()

	resp, err := c.get(ctx, listing)
	if err != nil {
		return "", fmt.Errorf("reading the listing of %s: %w", m, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("reading the listing of %s: unexpected status %s", m, resp.Status)
	}

	page, err := io.ReadAll(io.LimitReader(resp.Body, maxListing))
	if err != nil {
		return "", fmt.Errorf("reading the listing of %s: %w", m, err)
	}
	base, err := url.Parse(listing)
	if err != nil {
		return "", err
	}
	return linkTo(page, name, base)
}

var hrefPattern = regexp.MustCompile(`href="([^"]+)"`)

// linkTo finds, among the page's links, the one to the zip called name. The
// name is a path segment, followed by the document's UUID. A link to another
// host is refused: the page decides what is downloaded, so it may only point
// back at the site it came from.
func linkTo(page []byte, name string, base *url.URL) (string, error) {
	for _, match := range hrefPattern.FindAllSubmatch(page, -1) {
		href, err := url.Parse(html.UnescapeString(string(match[1])))
		if err != nil {
			continue
		}
		if !strings.Contains(href.Path+"/", "/"+name+"/") {
			continue
		}
		link := base.ResolveReference(href)
		if link.Host != base.Host {
			return "", fmt.Errorf("the link to %s points at %s, not at %s", name, link.Host, base.Host)
		}
		return link.String(), nil
	}
	return "", fmt.Errorf("%s: %w", name, ErrNotPublished)
}

// get sends a GET with the headers both requests need. Without an Accept
// header www.in.gov.br answers 403; "*/*" is what a client that takes any type
// sends, and the User-Agent stays ours.
func (c *Client) get(ctx context.Context, address string) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, address, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "*/*")
	return c.http.Do(req)
}
