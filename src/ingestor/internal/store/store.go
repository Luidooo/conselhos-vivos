// Package store writes the downloaded editions to disk, so that a file under
// its final name is always a whole, readable zip.
//
// The directory is also the record of what was asked of INLABS: for an edition
// there is its zip, a marker saying there was none, or nothing, which means
// nobody fetched it. Never the zip and the marker together.
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
	if err := os.Remove(filepath.Join(s.dir, MarkerName(name))); err != nil && !errors.Is(err, fs.ErrNotExist) {
		return Receipt{}, fmt.Errorf("removing the no-edition marker of %s: %w", name, err)
	}

	if err := syncDir(s.dir); err != nil {
		return Receipt{}, fmt.Errorf("flushing the directory %s: %w", s.dir, err)
	}

	return Receipt{Path: final, Size: size}, nil
}

// markerSuffix ends the name of the file that says an edition does not exist.
const markerSuffix = ".sem-edicao"

// MarkerName is the marker's file name for the edition whose zip is name:
// 2026-10-04-DO1.zip gives 2026-10-04-DO1.sem-edicao.
func MarkerName(name string) string {
	return strings.TrimSuffix(name, ".zip") + markerSuffix
}

// MarkNoEdition records that the edition whose zip would be name does not
// exist, as an empty file. Without it, a day with no edition and a day nobody
// fetched look the same on disk.
//
// A zip already there wins: an edition that was downloaded once existed, and
// one later "not found" does not unpublish it. Then nothing is written.
func (s *Store) MarkNoEdition(name string) error {
	if _, err := os.Stat(filepath.Join(s.dir, name)); err == nil {
		return nil
	} else if !errors.Is(err, fs.ErrNotExist) {
		return fmt.Errorf("looking for %s: %w", name, err)
	}

	marker := MarkerName(name)
	if err := os.WriteFile(filepath.Join(s.dir, marker), nil, 0o644); err != nil {
		return fmt.Errorf("writing %s: %w", marker, err)
	}
	if err := syncDir(s.dir); err != nil {
		return fmt.Errorf("flushing the directory %s: %w", s.dir, err)
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
