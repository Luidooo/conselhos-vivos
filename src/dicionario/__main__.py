"""python -m dicionario PAGINA MANIFEST CATALOG: lê os comentários do Postgres (variáveis PG*), monta o dicionário,
troca a página entre os marcadores e sai com 1 se alguma coluna estiver sem descrição."""

import json
import sys

import psycopg

from . import FIM, INICIO, linhas, markdown, sem_descricao

OLTP_SQL = """select c.relname, a.attname, format_type(a.atttypid, a.atttypmod), col_description(c.oid, a.attnum)
              from pg_attribute a join pg_class c on c.oid = a.attrelid join pg_namespace n on n.oid = c.relnamespace
              where n.nspname = 'public' and c.relkind = 'r' and a.attnum > 0 and not a.attisdropped
              order by 1, a.attnum"""

if __name__ == "__main__":
    pagina, manifest, catalog = sys.argv[1:4]
    with psycopg.connect() as conn:
        oltp = conn.execute(OLTP_SQL).fetchall()
    with open(manifest, encoding="utf-8") as f, open(catalog, encoding="utf-8") as g:
        lista = linhas(json.load(f), json.load(g), oltp)
    with open(pagina, encoding="utf-8") as f:
        texto = f.read()
    i, j = texto.index(INICIO) + len(INICIO), texto.index(FIM)
    with open(pagina, "w", encoding="utf-8") as f:
        f.write(texto[:i] + "\n" + markdown(lista) + "\n" + texto[j:])
    faltam = sem_descricao(lista)
    if faltam:
        print(f"{len(faltam)} coluna(s) sem descrição:\n  " + "\n  ".join(faltam), file=sys.stderr)
        sys.exit(1)
