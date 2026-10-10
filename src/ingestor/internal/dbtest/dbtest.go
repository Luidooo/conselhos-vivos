// Package dbtest gives a test the compose Postgres without letting it leave
// anything there.
package dbtest

import (
	"context"
	"os"
	"testing"

	"github.com/jackc/pgx/v5"
)

// Begin opens a transaction that is never committed, as tests/db does: the
// test leaves the database as it found it.
//
// The connection comes from the PG* variables, which the ingestor-db-test
// service sets. Without them the test is skipped, so `go test ./...` stays
// runnable with no database; `make test-db-go` is what runs it.
func Begin(t *testing.T) pgx.Tx {
	t.Helper()
	if os.Getenv("PGHOST") == "" {
		t.Skip("no PGHOST: run make test-db-go, with the database up and migrated")
	}

	ctx := context.Background()
	conn, err := pgx.Connect(ctx, "")
	if err != nil {
		t.Fatalf("connecting to the database: %v", err)
	}
	tx, err := conn.Begin(ctx)
	if err != nil {
		t.Fatalf("opening the transaction: %v", err)
	}
	t.Cleanup(func() {
		_ = tx.Rollback(ctx)
		_ = conn.Close(ctx)
	})
	return tx
}
