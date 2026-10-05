package store

import (
	"archive/zip"
	"bytes"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// zipWith builds a real archive, so the check under test is the same one the
// parser will later rely on.
func zipWith(t *testing.T, entry, contents string) []byte {
	t.Helper()

	var buffer bytes.Buffer
	writer := zip.NewWriter(&buffer)
	file, err := writer.Create(entry)
	require.NoError(t, err)
	_, err = io.WriteString(file, contents)
	require.NoError(t, err)
	require.NoError(t, writer.Close())

	return buffer.Bytes()
}

func mustOpen(t *testing.T, dir string) *Store {
	t.Helper()

	store, err := New(dir)
	require.NoError(t, err)
	return store
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

func TestSaveLandsAValidZip(t *testing.T) {
	dir := t.TempDir()
	archive := zipWith(t, "DO1.xml", "<article/>")

	receipt, err := mustOpen(t, dir).Save("2026-10-02-DO1.zip", bytes.NewReader(archive))
	require.NoError(t, err)

	assert.Equal(t, filepath.Join(dir, "2026-10-02-DO1.zip"), receipt.Path)
	assert.Equal(t, int64(len(archive)), receipt.Size)
	assert.Equal(t, []string{"2026-10-02-DO1.zip"}, entries(t, dir), "no temporary file left behind")

	onDisk, err := os.ReadFile(receipt.Path)
	require.NoError(t, err)
	assert.Equal(t, archive, onDisk)
}

// The failure the whole order exists to prevent: the login page saved under a
// name that everything downstream reads as an edition.
func TestSaveRefusesAnHTMLBody(t *testing.T) {
	dir := t.TempDir()

	_, err := mustOpen(t, dir).Save("2026-10-02-DO1.zip", strings.NewReader("<html>faca login</html>"))

	require.Error(t, err)
	assert.Contains(t, err.Error(), "is not a zip")
	assert.Empty(t, entries(t, dir), "neither the final name nor a temporary file should exist")
}

func TestSaveLeavesNothingWhenTheStreamBreaks(t *testing.T) {
	dir := t.TempDir()
	broken := io.MultiReader(bytes.NewReader([]byte("PK\x03\x04")), failingReader{})

	_, err := mustOpen(t, dir).Save("2026-10-02-DO1.zip", broken)

	require.Error(t, err)
	assert.Empty(t, entries(t, dir))
}

func TestSaveReplacesAnExistingFile(t *testing.T) {
	dir := t.TempDir()
	store := mustOpen(t, dir)
	name := "2026-10-02-DO1.zip"

	_, err := store.Save(name, bytes.NewReader(zipWith(t, "old.xml", "old")))
	require.NoError(t, err)

	fresh := zipWith(t, "new.xml", "new")
	_, err = store.Save(name, bytes.NewReader(fresh))
	require.NoError(t, err)

	onDisk, err := os.ReadFile(filepath.Join(dir, name))
	require.NoError(t, err)
	assert.Equal(t, fresh, onDisk)
	assert.Equal(t, []string{name}, entries(t, dir))
}

func TestSaveIsSafeWhenTwoRunsRaceOnTheSameName(t *testing.T) {
	dir := t.TempDir()
	store := mustOpen(t, dir)
	name := "2026-10-02-DO1.zip"
	archive := zipWith(t, "DO1.xml", "<article/>")

	var group sync.WaitGroup
	for range 2 {
		group.Add(1)
		go func() {
			defer group.Done()
			_, err := store.Save(name, bytes.NewReader(archive))
			assert.NoError(t, err)
		}()
	}
	group.Wait()

	assert.Equal(t, []string{name}, entries(t, dir), "the loser's temporary file must not survive")
	onDisk, err := os.ReadFile(filepath.Join(dir, name))
	require.NoError(t, err)
	assert.Equal(t, archive, onDisk)
}

// Creating the directory would hide what this reports: INLABS_OUTPUT_DIR
// pointing somewhere the volume is not mounted.
func TestNewRefusesADirectoryThatIsNotThere(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "bronze", "inlabs")

	_, err := New(missing)

	require.ErrorIs(t, err, os.ErrNotExist)
	assert.Contains(t, err.Error(), missing)
}

func TestNewRefusesAPathThatIsAFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "inlabs")
	require.NoError(t, os.WriteFile(path, nil, 0o644))

	_, err := New(path)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "not a directory")
}

type failingReader struct{}

func (failingReader) Read([]byte) (int, error) {
	return 0, errors.New("the connection died mid-transfer")
}
