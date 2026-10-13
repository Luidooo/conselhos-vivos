package dadosabertos

import (
	"archive/zip"
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"conselhos-vivos/internal/store"
)

var august = Month{Year: 2026, Month: time.August}

// zipPath is where the test server serves August's Section 1, shaped like the
// real address: the name, then the document's UUID.
const zipPath = "/documents/49035712/731891581/S01082026.zip/1a3dbffa-ed49-13ee-86d6-31bba2c02658"

// listing is August's page as the site serves it, trimmed to the links: the
// three sections, the query escaped as HTML.
const listing = `<html><body>
<a href="/documents/49035712/731891581/S01082026.zip/1a3dbffa-ed49-13ee-86d6-31bba2c02658?version=1.0&amp;download=t">S01082026.zip</a>
<a href="/documents/49035712/731891581/S02082026.zip/0facf097-be09-0968-33ae-258f1554478e?version=1.0&amp;download=t">S02082026.zip</a>
<a href="/documents/49035712/731891581/S03082026.zip/7eefd17d-4eb4-8d76-2520-09bf7f48a0bc?version=1.0&amp;download=t">S03082026.zip</a>
</body></html>`

func zipBody(t *testing.T) []byte {
	t.Helper()

	var buffer bytes.Buffer
	writer := zip.NewWriter(&buffer)
	file, err := writer.Create("515_20260803_24176216.xml")
	require.NoError(t, err)
	_, err = file.Write([]byte(`<xml><article id="1"/></xml>`))
	require.NoError(t, err)
	require.NoError(t, writer.Close())
	return buffer.Bytes()
}

// monthServer serves the listing page and hands every other path to zip. It
// counts the requests, and refuses one without the Accept header the real site
// needs, with the 403 the real site gives.
//
// assert is allowed inside the handlers, require is not: require calls
// t.FailNow, which only works on the test's own goroutine.
func monthServer(t *testing.T, page string, zipHandler http.HandlerFunc) (*Client, *atomic.Int32) {
	t.Helper()

	var requests atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		if r.Header.Get("Accept") != "*/*" {
			w.WriteHeader(http.StatusForbidden)
			return
		}
		if r.URL.Path == listingPath {
			assert.Equal(t, "2026", r.URL.Query().Get("ano"))
			assert.Equal(t, "Agosto", r.URL.Query().Get("mes"))
			w.Write([]byte(page))
			return
		}
		zipHandler(w, r)
	}))
	t.Cleanup(server.Close)

	client := New(nil)
	client.baseURL = server.URL
	return client, &requests
}

func mustStore(t *testing.T) (*store.Store, string) {
	t.Helper()

	dir := t.TempDir()
	dest, err := store.New(dir)
	require.NoError(t, err)
	return dest, dir
}

func entries(t *testing.T, dir string) []string {
	t.Helper()

	found, err := os.ReadDir(dir)
	require.NoError(t, err)
	names := make([]string, 0, len(found))
	for _, item := range found {
		names = append(names, item.Name())
	}
	return names
}

func TestZipNameIsThePublishedOne(t *testing.T) {
	assert.Equal(t, "S01082026.zip", ZipName(august))
	assert.Equal(t, "S01032010.zip", ZipName(Month{Year: 2010, Month: time.March}))
}

func TestParseMonthTakesOnlyYYYYMM(t *testing.T) {
	month, err := ParseMonth("2026-08")
	require.NoError(t, err)
	assert.Equal(t, august, month)

	for _, raw := range []string{"2026-8", "08/2026", "2026-13", "2026-08-01", ""} {
		_, err := ParseMonth(raw)
		assert.Error(t, err, raw)
	}
}

func TestFetchMonthSavesSection1(t *testing.T) {
	body := zipBody(t)
	client, _ := monthServer(t, listing, func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, zipPath, r.URL.Path, "only Section 1 is fetched")
		w.Write(body)
	})
	dest, dir := mustStore(t)

	outcome, err := client.FetchMonth(context.Background(), august, dest)

	require.NoError(t, err)
	assert.Equal(t, Downloaded, outcome)
	saved, err := os.ReadFile(filepath.Join(dir, "S01082026.zip"))
	require.NoError(t, err)
	assert.Equal(t, body, saved)
}

func TestFetchMonthAsksNothingForAMonthOnDisk(t *testing.T) {
	client, requests := monthServer(t, listing, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	dest, dir := mustStore(t)
	require.NoError(t, os.WriteFile(filepath.Join(dir, "S01082026.zip"), zipBody(t), 0o644))

	outcome, err := client.FetchMonth(context.Background(), august, dest)

	require.NoError(t, err)
	assert.Equal(t, AlreadyThere, outcome)
	assert.Zero(t, requests.Load())
}

func TestFetchMonthSaysWhenTheMonthIsNotOut(t *testing.T) {
	client, requests := monthServer(t, `<html><body>nenhum arquivo</body></html>`,
		func(w http.ResponseWriter, _ *http.Request) {
			w.WriteHeader(http.StatusInternalServerError)
		})
	dest, dir := mustStore(t)

	_, err := client.FetchMonth(context.Background(), august, dest)

	assert.ErrorIs(t, err, ErrNotPublished)
	assert.Equal(t, int32(1), requests.Load(), "only the listing is asked for")
	assert.Empty(t, entries(t, dir))
}

func TestFetchMonthLeavesNothingWhenTheDownloadFails(t *testing.T) {
	client, _ := monthServer(t, listing, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	dest, dir := mustStore(t)

	_, err := client.FetchMonth(context.Background(), august, dest)

	assert.ErrorContains(t, err, "500")
	assert.Empty(t, entries(t, dir))
}

func TestFetchMonthRefusesAPageInPlaceOfTheZip(t *testing.T) {
	client, _ := monthServer(t, listing, func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte("<html>manutenção</html>"))
	})
	dest, dir := mustStore(t)

	_, err := client.FetchMonth(context.Background(), august, dest)

	assert.ErrorContains(t, err, "not a zip")
	assert.Empty(t, entries(t, dir))
}

func TestFetchMonthRefusesALinkToAnotherHost(t *testing.T) {
	page := `<a href="https://outro.exemplo/documents/1/2/S01082026.zip/uuid?download=t">S01082026.zip</a>`
	client, requests := monthServer(t, page, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	dest, dir := mustStore(t)

	_, err := client.FetchMonth(context.Background(), august, dest)

	assert.ErrorContains(t, err, "outro.exemplo")
	assert.Equal(t, int32(1), requests.Load())
	assert.Empty(t, entries(t, dir))
}
