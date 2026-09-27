"""SQL de carga dos órgãos e aliases para o psql do container db (ADR 0004).

Idempotente. O órgão é achado pelo código SIORG ou pelo nome vigente (é assim que os 5
conselhos do sql/004 são reaproveitados), e só é criado se não existir. Nome antigo entra
uma vez. O alias é atualizado pelo arquivo de decisões: um ambíguo resolvido passa a
apontar para o órgão na próxima carga. A carga não apaga nada. Tudo numa transação.
"""

from planilha.carga import literal


def _data(d):
    return literal(d.isoformat() if d else None)


def _valores(linhas):
    return ",\n".join("(" + ", ".join(v) + ")" for v in linhas)


def sql(res):
    orgaos = _valores([literal(o.nome), literal(o.sigla), literal(o.codigo_siorg), _data(o.inicio)]
                      for o in res.orgaos)
    antigos = _valores([literal(o.nome), literal(a.nome), _data(a.inicio), _data(a.fim)]
                       for o in res.orgaos for a in o.nomes_antigos)
    aliases = _valores([literal(a.nome), literal(a.chave), literal(a.orgao), literal(a.status), literal(a.motivo)]
                       for a in res.aliases)
    return f"""-- Gerado por `python -m conselhos sql` a partir de {res.arquivos['planilha'][0]}, \
{res.arquivos['decisões'][0]} e {res.arquivos['recorte do SIORG'][0]}.
\\set ON_ERROR_STOP on
SET client_min_messages = warning;
BEGIN;

CREATE TEMP TABLE carga_orgao (nome text, sigla text, codigo_siorg int, inicio date,
                               orgao_id int, novo boolean DEFAULT false) ON COMMIT DROP;
INSERT INTO carga_orgao (nome, sigla, codigo_siorg, inicio) VALUES
{orgaos};

CREATE TEMP TABLE carga_nome_antigo (orgao text, nome text, inicio date, fim date) ON COMMIT DROP;
INSERT INTO carga_nome_antigo VALUES
{antigos};

CREATE TEMP TABLE carga_alias (nome text, chave text, orgao text, status text, motivo text) ON COMMIT DROP;
INSERT INTO carga_alias VALUES
{aliases};

-- O órgão já existe? Pelo código SIORG e, se não, pelo nome vigente.
UPDATE carga_orgao c SET orgao_id = o.id FROM orgao o WHERE o.codigo_siorg = c.codigo_siorg;
UPDATE carga_orgao c SET orgao_id = n.orgao_id
  FROM orgao_nome n WHERE c.orgao_id IS NULL AND n.nome = c.nome AND n.data_fim IS NULL;

DO $$
DECLARE c record; criado int;
BEGIN
  FOR c IN SELECT * FROM carga_orgao WHERE orgao_id IS NULL ORDER BY nome LOOP
    INSERT INTO orgao (codigo_siorg, sigla) VALUES (c.codigo_siorg, c.sigla) RETURNING id INTO criado;
    INSERT INTO orgao_nome (orgao_id, nome, data_inicio) VALUES (criado, c.nome, c.inicio);
    UPDATE carga_orgao SET orgao_id = criado, novo = true WHERE nome = c.nome;
  END LOOP;
END $$;

-- Órgão que já existia (os 5 do sql/004) ganha o código SIORG e a sigla, se ainda não tem.
UPDATE orgao o SET codigo_siorg = COALESCE(o.codigo_siorg, c.codigo_siorg), sigla = COALESCE(o.sigla, c.sigla)
  FROM carga_orgao c WHERE c.orgao_id = o.id AND NOT c.novo
   AND (o.codigo_siorg IS NULL AND c.codigo_siorg IS NOT NULL OR o.sigla IS NULL AND c.sigla IS NOT NULL);

SELECT count(*) FILTER (WHERE novo) AS orgaos_novos, count(*) AS orgaos FROM carga_orgao \\gset

WITH novos AS (
  INSERT INTO orgao_nome (orgao_id, nome, data_inicio, data_fim)
  SELECT c.orgao_id, a.nome, a.inicio, a.fim
    FROM carga_nome_antigo a JOIN carga_orgao c ON c.nome = a.orgao
   WHERE NOT EXISTS (SELECT 1 FROM orgao_nome n WHERE n.orgao_id = c.orgao_id AND n.nome = a.nome)
   ORDER BY a.orgao, a.fim
  RETURNING 1
) SELECT count(*) AS nomes_antigos_novos FROM novos \\gset

WITH gravados AS (
  INSERT INTO orgao_alias (nome, chave, fonte, orgao_id, status, motivo)
  SELECT a.nome, a.chave, 'PLANILHA', c.orgao_id, a.status, a.motivo
    FROM carga_alias a LEFT JOIN carga_orgao c ON c.nome = a.orgao
   ORDER BY a.nome
  ON CONFLICT (fonte, nome) DO UPDATE
     SET chave = EXCLUDED.chave, orgao_id = EXCLUDED.orgao_id, status = EXCLUDED.status, motivo = EXCLUDED.motivo
   WHERE (orgao_alias.chave, orgao_alias.orgao_id, orgao_alias.status, orgao_alias.motivo)
         IS DISTINCT FROM (EXCLUDED.chave, EXCLUDED.orgao_id, EXCLUDED.status, EXCLUDED.motivo)
  RETURNING (xmax = 0) AS inserido
) SELECT count(*) FILTER (WHERE inserido) AS aliases_novos, count(*) FILTER (WHERE NOT inserido) AS aliases_alterados
    FROM gravados \\gset

COMMIT;
\\echo '→ conselhos:' :orgaos_novos 'de' :orgaos 'órgãos são novos;' :nomes_antigos_novos 'nomes antigos novos;' \
:aliases_novos 'aliases novos e' :aliases_alterados 'alterados ({len(res.aliases)} linhas na planilha)'
"""
