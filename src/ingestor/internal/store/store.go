// Package store writes the downloaded editions to disk, so that a file under
// its final name is always a whole, readable zip.
package store

import (
	"archive/zip"
	"fmt"
	"io"
	"os"
	"path/filepath"
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

	if err := syncDir(s.dir); err != nil {
		return Receipt{}, fmt.Errorf("flushing the directory %s: %w", s.dir, err)
	}

	return Receipt{Path: final, Size: size}, nil
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
