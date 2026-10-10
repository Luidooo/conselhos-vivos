// Package oltp writes a matéria of the DOU into the curation database: one row
// in ato, insert-only (ADR 0001), under the organ its artCategory names.
//
// It decides nothing about the classification: that stays with the
// spreadsheet and the human curation (ADR 0003).
package oltp

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"

	"conselhos-vivos/internal/article"
)

// ErrNoContent marks a matéria with an empty <Texto>. ato takes a DOU row only
// with its content, and an empty string would satisfy the constraint without
// honouring it.
var ErrNoContent = errors.New("matéria has no <Texto>")

// DB is what the package needs from a connection. A pgx.Tx satisfies it, so a
// caller picks the transaction, and a test can roll everything back.
type DB interface {
	Exec(ctx context.Context, sql string, args ...any) (pgconn.CommandTag, error)
	Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error)
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
}

// Outcome says what Save did with a matéria.
type Outcome int

const (
	// Saved is a matéria seen for the first time: version 1 in ato.
	Saved Outcome = iota + 1
	// NewVersion is a matéria already there that came back different: the
	// edition was republished. It is a new row, with the next version; the
	// earlier ones stay (insert-only, ADR 0001).
	NewVersion
	// Unchanged is a matéria already there as it is: nothing is written. It is
	// what makes running again safe.
	Unchanged
	// UnknownOrgan is a matéria whose organ is none of the known ones, which
	// is most of an edition. Nothing goes into ato; the organ's name goes into
	// orgao_alias once, waiting for a decision (ADR 0004).
	UnknownOrgan
)

// Writer saves matérias against the organs known when it was opened.
type Writer struct {
	db DB
	// organs maps a Key to its orgao.id. A key that names more than one organ
	// is in ambiguous instead: it never resolves by itself.
	organs    map[string]int32
	ambiguous map[string]bool
}

// Open reads the identity of the organs: every name an organ has or had
// (orgao_nome) and every spelling resolved to one (orgao_alias).
func Open(ctx context.Context, db DB) (*Writer, error) {
	rows, err := db.Query(ctx, `
		SELECT orgao_id, nome FROM orgao_nome
		UNION
		SELECT orgao_id, nome FROM orgao_alias WHERE status = 'RESOLVIDO'`)
	if err != nil {
		return nil, fmt.Errorf("reading the organs: %w", err)
	}
	defer rows.Close()

	writer := &Writer{db: db, organs: map[string]int32{}, ambiguous: map[string]bool{}}
	for rows.Next() {
		var (
			id   int32
			name string
		)
		if err := rows.Scan(&id, &name); err != nil {
			return nil, fmt.Errorf("reading the organs: %w", err)
		}
		key := Key(name)
		if known, ok := writer.organs[key]; ok && known != id {
			writer.ambiguous[key] = true
		}
		writer.organs[key] = id
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("reading the organs: %w", err)
	}
	for key := range writer.ambiguous {
		delete(writer.organs, key)
	}
	return writer, nil
}

// Save writes one matéria. With a known organ it becomes a row in ato:
// origem DOU, the article's id as id_dou and <Texto> as published as conteudo;
// an <Ementa> with only blanks is stored as NULL, as an empty one.
// With an unknown one it is left out and its organ is queued.
//
// It can be run again. The matéria is compared with its latest version, in
// everything Save writes: organ, date, ementa and content. Equal, nothing
// happens; different, it goes in as the next version.
func (w *Writer) Save(ctx context.Context, a article.Article) (Outcome, error) {
	if strings.TrimSpace(a.HTML) == "" {
		return 0, fmt.Errorf("%s: %w", a.Entry, ErrNoContent)
	}

	organ := squeeze(a.Organ())
	key := Key(organ)
	id, known := w.organs[key]
	if !known {
		if err := w.queue(ctx, a, organ, key); err != nil {
			return 0, err
		}
		return UnknownOrgan, nil
	}

	// One statement, so the check and the insert see the same rows. Two runs
	// racing on a matéria still cannot both win: uq_ato_dou_versao refuses the
	// second, which fails and is run again.
	var version int
	err := w.db.QueryRow(ctx, `
		WITH latest AS (
			SELECT versao,
			       orgao_id = $2 AND data_publicacao = $3
			         AND ementa IS NOT DISTINCT FROM NULLIF($4, '') AND conteudo = $5 AS same
			  FROM ato
			 WHERE origem = 'DOU' AND id_dou = $1
			 ORDER BY versao DESC
			 LIMIT 1
		)
		INSERT INTO ato (origem, id_dou, versao, orgao_id, data_publicacao, ementa, conteudo)
		SELECT 'DOU', $1, COALESCE((SELECT versao FROM latest), 0) + 1, $2, $3, NULLIF($4, ''), $5
		 WHERE NOT COALESCE((SELECT same FROM latest), FALSE)
		RETURNING versao`,
		a.ID, id, a.PubDate.In(time.UTC), strings.TrimSpace(a.Ementa), a.HTML).Scan(&version)
	switch {
	case errors.Is(err, pgx.ErrNoRows):
		return Unchanged, nil
	case err != nil:
		return 0, fmt.Errorf("saving %s (id %s): %w", a.Entry, a.ID, err)
	case version > 1:
		return NewVersion, nil
	}
	return Saved, nil
}

// queue records the organ's name in orgao_alias, once per name, with no organ
// and the reason. A name already there is left as it is: someone may have
// decided on it since.
func (w *Writer) queue(ctx context.Context, a article.Article, organ, key string) error {
	status, reason := "INDEFINIDO", "órgão não reconhecido na ingestão do DOU"
	if w.ambiguous[key] {
		status, reason = "AMBIGUO", "a chave casa com mais de um órgão"
	}
	reason += "; artCategory: " + strings.Join(a.Category, "/")

	_, err := w.db.Exec(ctx, `
		INSERT INTO orgao_alias (nome, chave, fonte, status, motivo)
		VALUES ($1, $2, 'DOU', $3, $4)
		ON CONFLICT (fonte, nome) DO NOTHING`,
		organ, key, status, reason)
	if err != nil {
		return fmt.Errorf("queueing the organ %q of %s: %w", organ, a.Entry, err)
	}
	return nil
}
