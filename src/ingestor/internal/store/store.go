// Package store writes the downloaded editions to disk, so that a file under
// its final name is always a whole, readable zip.
//
// The directory is also the record of what was asked of INLABS: for an edition
// there is its zip, a marker saying there was none, a marker saying the fetch
// failed, or nothing, which means nobody fetched it. Never two of them
// together.
package store

import (
	"archive/zip"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

// Store writes into one directory.
type Store struct {
	dir string
}

// New opens dir as the destination. It has to exist already: creating it here
// would paper over a missing volume mount and write the editions inside the
// container, where nobody goes looking for them.
func New(dir string) (*Store, error) {
	info, err := os.Stat(dir)
	if err != nil {
		return nil, fmt.Errorf("the output directory %s: %w", dir, err)
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("the output path %s is not a directory", dir)
	}
	return &Store{dir: dir}, nil
}

// Receipt says what landed, for the log and the summary.
type Receipt struct {
	Path string
	Size int64
}

// Save streams r into dir/name, and only lets the final name exist once the
// bytes are a zip that opens.
//
// The order is the whole point: a temporary file in the same directory (a rename
// across filesystems fails with EXDEV), the copy, an fsync, the zip check, the
// rename, then an fsync of the directory. Checking after the rename would leave
// a corrupt file under the name everything else trusts.
func (s *Store) Save(name string, r io.Reader) (Receipt, error) {
	temp, err := os.CreateTemp(s.dir, name+".part-*")
	if err != nil {
		return Receipt{}, fmt.Errorf("creating the temporary file for %s: %w", name, err)
	}
	// Removing a renamed path is a no-op, so this covers every failure below
	// without a flag to track whether the rename happened.
	defer os.Remove(temp.Name())
	defer temp.Close()

	size, err := io.Copy(temp, r)
	if err != nil {
		return Receipt{}, fmt.Errorf("writing %s: %w", name, err)
	}
	if err := temp.Sync(); err != nil {
		return Receipt{}, fmt.Errorf("flushing %s: %w", name, err)
	}

	if _, err := zip.NewReader(temp, size); err != nil {
		return Receipt{}, fmt.Errorf("%s is not a zip (%d bytes): %w", name, size, err)
	}

	if err := temp.Close(); err != nil {
		return Receipt{}, fmt.Errorf("closing %s: %w", name, err)
	}

	final := filepath.Join(s.dir, name)
	if err := os.Rename(temp.Name(), final); err != nil {
		return Receipt{}, fmt.Errorf("publishing %s: %w", name, err)
	}

	// The edition exists now, whatever an earlier run was told.
	if err := s.unmark(name, noEditionSuffix, failedSuffix); err != nil {
		return Receipt{}, err
	}

	if err := syncDir(s.dir); err != nil {
		return Receipt{}, fmt.Errorf("flushing the directory %s: %w", s.dir, err)
	}

	return Receipt{Path: final, Size: size}, nil
}

// The suffixes of the two markers. A marker is an empty file under the
// edition's name, with the suffix in place of ".zip".
const (
	// noEditionSuffix says INLABS answered that the edition does not exist.
	noEditionSuffix = ".sem-edicao"
	// failedSuffix says the edition was asked for and did not arrive.
	failedSuffix = ".falhou"
)

// NoEditionName is the name of the marker MarkNoEdition leaves for the edition
// whose zip is name: 2026-10-04-DO1.zip gives 2026-10-04-DO1.sem-edicao.
func NoEditionName(name string) string {
	return strings.TrimSuffix(name, ".zip") + noEditionSuffix
}

// FailedName is the name of the marker MarkFailed leaves for the edition whose
// zip is name: 2026-10-04-DO1.zip gives 2026-10-04-DO1.falhou.
func FailedName(name string) string {
	return strings.TrimSuffix(name, ".zip") + failedSuffix
}

// MarkNoEdition records that the edition whose zip would be name does not
// exist. Without it, a day with no edition and a day nobody fetched look the
// same on disk.
func (s *Store) MarkNoEdition(name string) error {
	return s.mark(name, noEditionSuffix, failedSuffix)
}

// MarkFailed records that the edition whose zip would be name was asked for
// and did not arrive, so it is not mistaken for one nobody fetched: it is the
// one to fetch again.
func (s *Store) MarkFailed(name string) error {
	return s.mark(name, failedSuffix, noEditionSuffix)
}

// mark leaves the marker with suffix for the edition, and removes the one with
// the other suffix: the record is what the last fetch found. The old marker
// goes first: a crash in between leaves no marker (a day to fetch again), never
// two that contradict each other.
//
// A zip already there wins over both: an edition that was downloaded once
// existed, and neither a later "not found" nor a later failure takes it back.
// Then nothing is written.
func (s *Store) mark(name, suffix, other string) error {
	if _, err := os.Stat(filepath.Join(s.dir, name)); err == nil {
		return nil
	} else if !errors.Is(err, fs.ErrNotExist) {
		return fmt.Errorf("looking for %s: %w", name, err)
	}

	if err := s.unmark(name, other); err != nil {
		return err
	}
	marker := strings.TrimSuffix(name, ".zip") + suffix
	if err := os.WriteFile(filepath.Join(s.dir, marker), nil, 0o644); err != nil {
		return fmt.Errorf("writing %s: %w", marker, err)
	}
	if err := syncDir(s.dir); err != nil {
		return fmt.Errorf("flushing the directory %s: %w", s.dir, err)
	}
	return nil
}

// unmark removes the edition's markers with the given suffixes. One that is
// not there is not an error.
func (s *Store) unmark(name string, suffixes ...string) error {
	for _, suffix := range suffixes {
		marker := strings.TrimSuffix(name, ".zip") + suffix
		if err := os.Remove(filepath.Join(s.dir, marker)); err != nil && !errors.Is(err, fs.ErrNotExist) {
			return fmt.Errorf("removing %s: %w", marker, err)
		}
	}
	return nil
}

// syncDir makes the rename itself durable: without it, a crash can leave the
// directory entry behind even though the file's bytes are on disk.
func syncDir(dir string) error {
	handle, err := os.Open(dir)
	if err != nil {
		return err
	}
	defer handle.Close()

	return handle.Sync()
}
