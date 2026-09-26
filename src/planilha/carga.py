"""SQL de carga para o psql do container db (a biblioteca padrão não tem driver de Postgres).

Idempotente: o ato entra uma vez por (conselho, ID_VERSAO), pelo índice uq_ato_planilha
(sql/003), e a classificação da planilha entra uma vez por ato. Se a pesquisadora já
classificou o ato, pela planilha ou pela curadoria, a carga não repete nem sobrepõe.
Tudo numa transação: se algo falhar, nada fica no banco.
"""

from .abas import REVISOR


def literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def sql(res):
    linhas = ",\n".join(
        "(" + ", ".join(literal(v) for v in (i, a.conselho, a.id_planilha, a.data_publicacao.isoformat(),
                                             a.ref_legal, a.ementa, a.conteudo, a.tipologia)) + ")"
        for i, a in enumerate(res.atos))
    return f"""-- Gerado por `python -m planilha sql` a partir de {res.arquivo} (sha256 {res.sha256}).
\\set ON_ERROR_STOP on
SET client_min_messages = warning;
BEGIN;

CREATE TEMP TABLE carga_planilha (
  ordem int, conselho text, id_planilha int, data_publicacao date,
  ref_legal text, ementa text, conteudo text, tipologia text
) ON COMMIT DROP;

INSERT INTO carga_planilha VALUES
{linhas};

-- Falta de órgão, revisor ou tipologia faria o JOIN abaixo perder linhas em silêncio: para antes.
DO $$
DECLARE faltando text;
BEGIN
  SELECT string_agg(DISTINCT c.conselho, ', ') INTO faltando FROM carga_planilha c
   WHERE NOT EXISTS (SELECT 1 FROM orgao_nome n WHERE n.nome = c.conselho AND n.data_fim IS NULL);
  IF faltando IS NOT NULL THEN
    RAISE EXCEPTION 'conselho sem órgão no banco: % (rode make migrate)', faltando;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM revisor WHERE email = {literal(REVISOR)}) THEN
    RAISE EXCEPTION 'revisor {REVISOR} não existe (rode make migrate)';
  END IF;
  SELECT string_agg(DISTINCT c.tipologia, ', ') INTO faltando FROM carga_planilha c
   WHERE c.tipologia IS NOT NULL AND NOT EXISTS (SELECT 1 FROM tipologia t WHERE t.sigla = c.tipologia);
  IF faltando IS NOT NULL THEN
    RAISE EXCEPTION 'tipologia sem cadastro no banco: % (rode make migrate)', faltando;
  END IF;
END $$;

WITH novos AS (
  INSERT INTO ato (origem, id_planilha, orgao_id, data_publicacao, ref_legal, ementa, conteudo)
  SELECT 'PLANILHA', c.id_planilha, n.orgao_id, c.data_publicacao, c.ref_legal, c.ementa, c.conteudo
    FROM carga_planilha c JOIN orgao_nome n ON n.nome = c.conselho AND n.data_fim IS NULL
   ORDER BY c.ordem
  ON CONFLICT (orgao_id, id_planilha) WHERE origem = 'PLANILHA' DO NOTHING
  RETURNING 1
) SELECT count(*) AS atos_novos FROM novos \\gset

WITH novas AS (
  INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id)
  SELECT a.id, c.tipologia, r.id
    FROM carga_planilha c
    JOIN orgao_nome n ON n.nome = c.conselho AND n.data_fim IS NULL
    JOIN ato a ON a.origem = 'PLANILHA' AND a.orgao_id = n.orgao_id AND a.id_planilha = c.id_planilha
    CROSS JOIN (SELECT id FROM revisor WHERE email = {literal(REVISOR)}) r
   WHERE c.tipologia IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM classificacao k WHERE k.ato_id = a.id AND k.revisor_id = r.id)
   ORDER BY c.ordem
  RETURNING 1
) SELECT count(*) AS classificacoes_novas FROM novas \\gset

COMMIT;
\\echo '→ planilha:' :atos_novos 'atos novos e' :classificacoes_novas 'classificações novas ({len(res.atos)} atos na planilha)'
"""
