# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]>=3.2", "pymysql>=1.1", "cassandra-driver>=3.29"]
# ///
"""Medição do ADR 0002: em que motor roda o OLTP de curadoria.

Sobe um container descartável por motor (PostgreSQL, MySQL, MariaDB, Cassandra;
SQLite é um arquivo), aplica o mesmo mini-esquema da curadoria e mede:

  C1-C5  capacidades que o nosso esquema usa, testadas executando (não lidas na doc)
  Q1/Q2  leitura da classificação vigente, com dados sintéticos no volume do domínio
  ops    tamanho da imagem, tempo até aceitar conexão, RAM ociosa

Uso, a partir da raiz do repositório:
    uv run docs/adr/medicoes/0002-motor/bench.py            # n = 2638 e 26380
    uv run docs/adr/medicoes/0002-motor/bench.py --n 2638

Nada toca o banco do projeto: cada container ganha uma porta livre em 127.0.0.1
e é removido no fim.
"""

import argparse
import datetime as dt
import json
import pathlib
import sqlite3
import statistics
import subprocess
import tempfile
import time

TIPOS = ["DEF", "FISC", "GEST", "AUTO", "IP"]
RUNS = 7  # execuções medidas por consulta (depois de 1 aquecimento); reporta a mediana
HUMANO, PIPELINE = 1, 2

MOTORES = {
    "postgres": dict(image="postgres:16.15", internal=5432,
                     env={"POSTGRES_PASSWORD": "bench", "POSTGRES_DB": "bench"}),
    "mysql": dict(image="mysql:8.4", internal=3306,
                  env={"MYSQL_ROOT_PASSWORD": "bench", "MYSQL_DATABASE": "bench"}),
    "mariadb": dict(image="mariadb:11.4", internal=3306,
                    env={"MARIADB_ROOT_PASSWORD": "bench", "MARIADB_DATABASE": "bench"}),
    "cassandra": dict(image="cassandra:5.0", internal=9042, env={}),
}


# ---------------------------------------------------------------- containers

def sh(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check).stdout.strip()


def subir(nome):
    m = MOTORES[nome]
    sh("docker", "rm", "-f", f"bench-{nome}", check=False)
    env = sum((["-e", f"{k}={v}"] for k, v in m["env"].items()), [])
    t0 = time.perf_counter()
    sh("docker", "run", "-d", "--name", f"bench-{nome}",
       "-p", f"127.0.0.1::{m['internal']}", *env, m["image"])
    # porta livre escolhida pelo Docker, só em 127.0.0.1
    m["port"] = int(sh("docker", "port", f"bench-{nome}", str(m["internal"])).splitlines()[0].rsplit(":", 1)[1])
    return t0


def derrubar(nome):
    sh("docker", "rm", "-f", f"bench-{nome}", check=False)


def ram_mb(nome):
    uso = sh("docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", f"bench-{nome}")
    valor = uso.split("/")[0].strip()
    num = float("".join(c for c in valor if c.isdigit() or c == "."))
    return round(num * 1024 if "GiB" in valor else num)


def imagem_mb(image):
    sh("docker", "pull", "-q", image)  # máquina nova: baixa a imagem; já baixada: não faz nada
    return round(int(sh("docker", "image", "inspect", "-f", "{{.Size}}", image)) / 1e6)


def esperar(conectar, timeout=240):
    fim = time.time() + timeout
    while True:
        try:
            return conectar()
        except Exception:
            if time.time() > fim:
                raise
            time.sleep(1)


# ---------------------------------------------------------------- dados sintéticos

def gerar(n):
    """Por ato: a pesquisadora classifica 1 a 3 vezes, o pipeline 1 vez."""
    base = dt.datetime(2026, 9, 1)
    atos, classes, cid = [], [], 0
    for a in range(1, n + 1):
        atos.append((a, "PLANILHA", f"Resolução {a}/bench", f"ementa {a}"))
        for r in range(1, 2 + a % 3):
            cid += 1
            classes.append((cid, a, TIPOS[(a + r) % 5], HUMANO, base + dt.timedelta(days=r)))
        cid += 1
        classes.append((cid, a, TIPOS[a % 5], PIPELINE, base))
    return atos, classes


def mediana_ms(fn):
    fn()
    tempos = []
    for _ in range(RUNS):
        t = time.perf_counter()
        fn()
        tempos.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(tempos), 2)


# ---------------------------------------------------------------- motores relacionais

Q1 = """SELECT revisor_id, tipologia FROM (
  SELECT c.*, ROW_NUMBER() OVER (PARTITION BY ato_id, revisor_id
                                 ORDER BY criado_em DESC, id DESC) AS rn
  FROM classificacao c WHERE ato_id = {p}) x WHERE rn = 1"""
Q2 = """SELECT x.tipologia, count(*) FROM (
  SELECT c.tipologia, c.revisor_id, ROW_NUMBER() OVER (PARTITION BY ato_id, revisor_id
                                 ORDER BY criado_em DESC, id DESC) AS rn
  FROM classificacao c) x JOIN revisor r ON r.id = x.revisor_id
WHERE x.rn = 1 AND r.tipo = 'HUMANO' GROUP BY x.tipologia"""
Q2_DISTINCT_ON = """SELECT v.tipologia, count(*) FROM (
  SELECT DISTINCT ON (ato_id, revisor_id) * FROM classificacao
  ORDER BY ato_id, revisor_id, criado_em DESC, id DESC) v
JOIN revisor r ON r.id = v.revisor_id AND r.tipo = 'HUMANO' GROUP BY 1"""

DDL = {
    "postgres": {
        "tabelas": [
            "CREATE TABLE orgao_nome (id SERIAL PRIMARY KEY, orgao_id INT NOT NULL, nome TEXT NOT NULL,"
            " data_inicio DATE NOT NULL, data_fim DATE)",
            "CREATE TABLE revisor (id INT PRIMARY KEY, tipo VARCHAR(20) NOT NULL)",
            "CREATE TABLE ato (id BIGINT PRIMARY KEY, origem VARCHAR(20) NOT NULL, id_dou VARCHAR(100),"
            " ref_legal VARCHAR(100), ementa TEXT, conteudo TEXT,"
            " CONSTRAINT ck_ato_dou_completo CHECK (origem <> 'DOU' OR (id_dou IS NOT NULL AND conteudo IS NOT NULL)))",
            "CREATE TABLE classificacao (id BIGINT PRIMARY KEY, ato_id BIGINT NOT NULL REFERENCES ato(id) ON DELETE RESTRICT,"
            " tipologia VARCHAR(10) NOT NULL, revisor_id INT NOT NULL REFERENCES revisor(id), criado_em TIMESTAMP NOT NULL)",
            "CREATE INDEX ix_classificacao_recente ON classificacao (ato_id, revisor_id, criado_em DESC, id DESC)",
        ],
        "parcial": "CREATE UNIQUE INDEX uq_orgao_nome_vigente ON orgao_nome (orgao_id) WHERE data_fim IS NULL",
        "parcial_contorno": None,
        "trigger": [
            "CREATE FUNCTION bloqueia() RETURNS trigger LANGUAGE plpgsql AS"
            " $$ BEGIN RAISE EXCEPTION 'insert-only'; END $$",
            "CREATE TRIGGER tg_insert_only BEFORE UPDATE OR DELETE ON classificacao"
            " FOR EACH ROW EXECUTE FUNCTION bloqueia()",
        ],
        "p": "%s",
    },
    "mysql": {
        "tabelas": [
            "CREATE TABLE orgao_nome (id INT AUTO_INCREMENT PRIMARY KEY, orgao_id INT NOT NULL, nome TEXT NOT NULL,"
            " data_inicio DATE NOT NULL, data_fim DATE)",
            "CREATE TABLE revisor (id INT PRIMARY KEY, tipo VARCHAR(20) NOT NULL)",
            "CREATE TABLE ato (id BIGINT PRIMARY KEY, origem VARCHAR(20) NOT NULL, id_dou VARCHAR(100),"
            " ref_legal VARCHAR(100), ementa TEXT, conteudo TEXT,"
            " CONSTRAINT ck_ato_dou_completo CHECK (origem <> 'DOU' OR (id_dou IS NOT NULL AND conteudo IS NOT NULL)))",
            "CREATE TABLE classificacao (id BIGINT PRIMARY KEY, ato_id BIGINT NOT NULL, tipologia VARCHAR(10) NOT NULL,"
            " revisor_id INT NOT NULL, criado_em DATETIME NOT NULL,"
            " FOREIGN KEY (ato_id) REFERENCES ato(id) ON DELETE RESTRICT, FOREIGN KEY (revisor_id) REFERENCES revisor(id))",
            "CREATE INDEX ix_classificacao_recente ON classificacao (ato_id, revisor_id, criado_em DESC, id DESC)",
        ],
        "parcial": "CREATE UNIQUE INDEX uq_orgao_nome_vigente ON orgao_nome (orgao_id) WHERE data_fim IS NULL",
        # contorno clássico: coluna gerada que só tem valor quando o nome é vigente
        "parcial_contorno": "ALTER TABLE orgao_nome ADD COLUMN vigente_de INT"
                            " AS (IF(data_fim IS NULL, orgao_id, NULL)) STORED UNIQUE",
        "trigger": [
            "CREATE TRIGGER tg_insert_only BEFORE UPDATE ON classificacao FOR EACH ROW"
            " SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'insert-only'",
        ],
        "p": "%s",
    },
    "sqlite": {
        "tabelas": [
            "CREATE TABLE orgao_nome (id INTEGER PRIMARY KEY, orgao_id INT NOT NULL, nome TEXT NOT NULL,"
            " data_inicio DATE NOT NULL, data_fim DATE)",
            "CREATE TABLE revisor (id INT PRIMARY KEY, tipo TEXT NOT NULL)",
            "CREATE TABLE ato (id INTEGER PRIMARY KEY, origem TEXT NOT NULL, id_dou TEXT, ref_legal TEXT, ementa TEXT,"
            " conteudo TEXT,"
            " CONSTRAINT ck_ato_dou_completo CHECK (origem <> 'DOU' OR (id_dou IS NOT NULL AND conteudo IS NOT NULL)))",
            "CREATE TABLE classificacao (id INTEGER PRIMARY KEY, ato_id INT NOT NULL REFERENCES ato(id) ON DELETE RESTRICT,"
            " tipologia TEXT NOT NULL, revisor_id INT NOT NULL REFERENCES revisor(id), criado_em TIMESTAMP NOT NULL)",
            "CREATE INDEX ix_classificacao_recente ON classificacao (ato_id, revisor_id, criado_em DESC, id DESC)",
        ],
        "parcial": "CREATE UNIQUE INDEX uq_orgao_nome_vigente ON orgao_nome (orgao_id) WHERE data_fim IS NULL",
        "parcial_contorno": None,
        "trigger": [
            "CREATE TRIGGER tg_insert_only BEFORE UPDATE ON classificacao"
            " BEGIN SELECT RAISE(ABORT, 'insert-only'); END",
        ],
        "p": "?",
    },
}
DDL["mariadb"] = DDL["mysql"]


def conectar_relacional(nome, db_path=None):
    if nome == "postgres":
        import psycopg
        return psycopg.connect(host="127.0.0.1", port=MOTORES[nome]["port"], user="postgres",
                               password="bench", dbname="bench", autocommit=True)
    if nome in ("mysql", "mariadb"):
        import pymysql
        return pymysql.connect(host="127.0.0.1", port=MOTORES[nome]["port"], user="root",
                               password="bench", database="bench", autocommit=True)
    return sqlite3.connect(db_path, isolation_level=None)  # autocommit; BEGIN explícito


def executa(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params) if params is not None else cur.execute(sql)
    try:
        return cur.fetchall()
    except Exception:
        return None


def recusa(conn, sql):
    """True se o banco recusar o comando. Desfaz o que tiver entrado."""
    try:
        executa(conn, "BEGIN")
        executa(conn, sql)
        executa(conn, "ROLLBACK")
        return False
    except Exception:
        try:
            executa(conn, "ROLLBACK")
        except Exception:
            pass
        return True


def existe_tabela(conn, nome_motor, tabela):
    if nome_motor == "sqlite":
        q = "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = ?"
    elif nome_motor == "postgres":
        q = "SELECT count(*) FROM information_schema.tables WHERE table_name = %s"
    else:
        q = "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'bench' AND table_name = %s"
    return executa(conn, q, (tabela,))[0][0] > 0


def medir_relacional(nome, ns):
    r = {"motor": nome}
    tmp = None
    if nome == "sqlite":
        tmp = tempfile.mkdtemp()
        db_path = str(pathlib.Path(tmp) / "bench.db")
        r["imagem_mb"] = 0
        t0 = time.perf_counter()
        conn = conectar_relacional(nome, db_path)
    else:
        r["imagem_mb"] = imagem_mb(MOTORES[nome]["image"])
        t0 = subir(nome)
        conn = esperar(lambda: conectar_relacional(nome))
        if nome == "postgres":
            # o psycopg conecta durante o initdb; espera o banco final aceitar consulta
            esperar(lambda: executa(conectar_relacional(nome), "SELECT 1"))
            conn = conectar_relacional(nome)
    r["pronto_s"] = round(time.perf_counter() - t0, 1)
    d = DDL[nome]

    # C1 — DDL transacional: uma migração cria tabela e quebra no meio. A tabela sobrevive?
    try:
        executa(conn, "BEGIN")
        executa(conn, "CREATE TABLE migracao_quebrada (x INT)")
        executa(conn, "SELECT coluna_que_nao_existe FROM migracao_quebrada")
    except Exception:
        try:
            executa(conn, "ROLLBACK")
        except Exception:
            pass
    r["C1_ddl_transacional"] = not existe_tabela(conn, nome, "migracao_quebrada")

    for s in d["tabelas"]:
        executa(conn, s)
    if nome == "sqlite":
        executa(conn, "PRAGMA foreign_keys = OFF")  # o padrão do SQLite; medido abaixo

    # C2 — um só nome vigente por órgão
    try:
        executa(conn, d["parcial"])
        r["C2_indice_parcial"] = "nativo"
    except Exception:
        executa(conn, d["parcial_contorno"])
        r["C2_indice_parcial"] = "contorno (coluna gerada)"
    r["C2_recusa_2_vigentes"] = recusa(
        conn, "INSERT INTO orgao_nome (orgao_id, nome, data_inicio) VALUES (1, 'A', '2020-01-01'), (1, 'B', '2021-01-01')")

    # C4 — CHECK: ato do DOU sem id_dou
    r["C4_check"] = recusa(conn, "INSERT INTO ato (id, origem, conteudo) VALUES (999999999, 'DOU', 't')")

    # carga sintética de referência
    executa(conn, f"INSERT INTO revisor (id, tipo) VALUES ({HUMANO}, 'HUMANO'), ({PIPELINE}, 'PIPELINE')")
    p = d["p"]
    atos, classes = gerar(max(ns))
    cur = conn.cursor()
    executa(conn, "BEGIN")
    cur.executemany(f"INSERT INTO ato (id, origem, ref_legal, ementa) VALUES ({p},{p},{p},{p})", atos)
    cur.executemany(f"INSERT INTO classificacao (id, ato_id, tipologia, revisor_id, criado_em)"
                    f" VALUES ({p},{p},{p},{p},{p})", classes)
    executa(conn, "COMMIT")

    # C3 — FK RESTRICT: apagar ato que tem classificação
    r["C3_fk_padrao"] = recusa(conn, "DELETE FROM ato WHERE id = 1")
    if nome == "sqlite":
        executa(conn, "PRAGMA foreign_keys = ON")
        r["C3_fk_com_pragma"] = recusa(conn, "DELETE FROM ato WHERE id = 1")

    # C5 — trigger bloqueando UPDATE (classificação insert-only)
    for s in d["trigger"]:
        executa(conn, s)
    r["C5_trigger"] = recusa(conn, "UPDATE classificacao SET tipologia = 'IP' WHERE id = 1")

    # CDC: configuração padrão do container, medida
    if nome == "postgres":
        r["cdc_padrao"] = "wal_level=" + executa(conn, "SHOW wal_level")[0][0]
    elif nome in ("mysql", "mariadb"):
        lb, fmt = executa(conn, "SELECT @@log_bin, @@binlog_format")[0]
        r["cdc_padrao"] = f"log_bin={lb}, binlog_format={fmt}"
    else:
        r["cdc_padrao"] = "não existe"

    # Q1/Q2 em cada volume: apaga os atos acima de n (as classificações são insert-only,
    # então o volume menor é medido primeiro numa cópia filtrada por ato_id)
    for n in sorted(ns):
        filtro = f" WHERE ato_id <= {n}"
        q1 = Q1.format(p=n)  # último ato do recorte
        q2 = Q2.replace("FROM classificacao c)", f"FROM classificacao c{filtro})")
        r[f"Q1_ms_n{n}"] = mediana_ms(lambda: executa(conn, q1))
        r[f"Q2_ms_n{n}"] = mediana_ms(lambda: executa(conn, q2))
        if nome == "postgres":
            q2d = Q2_DISTINCT_ON.replace("FROM classificacao\n", f"FROM classificacao{filtro}\n")
            r[f"Q2_distinct_on_ms_n{n}"] = mediana_ms(lambda: executa(conn, q2d))
        r[f"Q2_resultado_n{n}"] = sorted(executa(conn, q2))

    if nome == "sqlite":
        r["ram_mb"] = "no processo da aplicação"
        r["disco_kb"] = round(pathlib.Path(db_path).stat().st_size / 1024)
    else:
        time.sleep(5)
        r["ram_mb"] = ram_mb(nome)
        derrubar(nome)
    conn.close()
    return r


# ---------------------------------------------------------------- Cassandra

def medir_cassandra(ns):
    from cassandra.cluster import Cluster
    from cassandra.concurrent import execute_concurrent_with_args
    from cassandra.io.asyncioreactor import AsyncioConnection

    nome = "cassandra"
    r = {"motor": nome, "imagem_mb": imagem_mb(MOTORES[nome]["image"])}
    t0 = subir(nome)

    def abrir():
        c = Cluster(["127.0.0.1"], port=MOTORES[nome]["port"], connection_class=AsyncioConnection)
        return c, c.connect()

    cluster, s = esperar(abrir, timeout=300)
    r["pronto_s"] = round(time.perf_counter() - t0, 1)
    s.execute("CREATE KEYSPACE bench WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
    s.set_keyspace("bench")

    # C1 — não há transação: o CREATE vale mesmo que o passo seguinte da migração quebre
    s.execute("CREATE TABLE migracao_quebrada (x int PRIMARY KEY)")
    try:
        s.execute("SELECT coluna_que_nao_existe FROM migracao_quebrada")
    except Exception:
        pass
    r["C1_ddl_transacional"] = "migracao_quebrada" not in cluster.metadata.keyspaces["bench"].tables

    # modelagem por consulta: a partição é o ato; a mais recente vem primeiro
    s.execute("CREATE TABLE orgao_nome (orgao_id int, data_inicio date, nome text, data_fim date,"
              " PRIMARY KEY (orgao_id, data_inicio))")
    s.execute("CREATE TABLE ato (id int PRIMARY KEY, origem text, id_dou text, ref_legal text, ementa text, conteudo text)")
    s.execute("CREATE TABLE classificacao (ato_id int, revisor_id int, criado_em timestamp, id int, tipologia text,"
              " PRIMARY KEY ((ato_id), revisor_id, criado_em)) WITH CLUSTERING ORDER BY (revisor_id ASC, criado_em DESC)")

    def aceita(cql):
        try:
            s.execute(cql)
            return True
        except Exception:
            return False

    r["C2_indice_parcial"] = "não existe (sem unicidade além da chave)"
    r["C2_recusa_2_vigentes"] = not (
        aceita("INSERT INTO orgao_nome (orgao_id, data_inicio, nome) VALUES (1, '2020-01-01', 'A')")
        and aceita("INSERT INTO orgao_nome (orgao_id, data_inicio, nome) VALUES (1, '2021-01-01', 'B')"))
    r["C4_check"] = not aceita("INSERT INTO ato (id, origem, conteudo) VALUES (999999999, 'DOU', 't')")

    atos, classes = gerar(max(ns))
    execute_concurrent_with_args(
        s, s.prepare("INSERT INTO ato (id, origem, ref_legal, ementa) VALUES (?, ?, ?, ?)"), atos, concurrency=64)
    execute_concurrent_with_args(
        s, s.prepare("INSERT INTO classificacao (id, ato_id, tipologia, revisor_id, criado_em) VALUES (?, ?, ?, ?, ?)"),
        classes, concurrency=64)

    r["C3_fk_padrao"] = not aceita("DELETE FROM ato WHERE id = 1")
    # C5: UPDATE numa linha que existe (o ato 2 tem classificação humana)
    ultima = s.execute("SELECT criado_em FROM classificacao WHERE ato_id = 2 AND revisor_id = 1 LIMIT 1").one()
    r["C5_trigger"] = not aceita(
        f"UPDATE classificacao SET tipologia = 'IP' WHERE ato_id = 2 AND revisor_id = 1"
        f" AND criado_em = '{ultima.criado_em.isoformat()}'")
    r["cdc_padrao"] = "cdc_enabled=false (padrão do cassandra.yaml)"

    q1 = s.prepare("SELECT revisor_id, tipologia FROM classificacao WHERE ato_id = ? GROUP BY ato_id, revisor_id")
    todas = s.prepare("SELECT ato_id, revisor_id, tipologia FROM classificacao GROUP BY ato_id, revisor_id")
    todas.fetch_size = 5000
    for n in sorted(ns):
        r[f"Q1_ms_n{n}"] = mediana_ms(lambda: list(s.execute(q1, (n,))))

        def q2():  # sem JOIN nem GROUP BY global: varre tudo e agrega no cliente
            cont = {}
            for row in s.execute(todas):
                if row.ato_id <= n and row.revisor_id == HUMANO:
                    cont[row.tipologia] = cont.get(row.tipologia, 0) + 1
            return sorted(cont.items())

        r[f"Q2_ms_n{n}"] = mediana_ms(q2)
        r[f"Q2_resultado_n{n}"] = q2()

    time.sleep(5)
    r["ram_mb"] = ram_mb(nome)
    cluster.shutdown()
    derrubar(nome)
    return r


# ---------------------------------------------------------------- relatório

def sim_nao(v):
    return {True: "✅ recusa", False: "❌ aceita"}.get(v, v)


def relatorio(res, ns):
    ordem = ["postgres", "mysql", "mariadb", "sqlite", "cassandra"]
    res = sorted(res, key=lambda x: ordem.index(x["motor"]))
    cab = "| | " + " | ".join(x["motor"] for x in res) + " |\n|---|" + "---|" * len(res) + "\n"
    linhas = [
        ("C1 migração que quebra no meio é desfeita", lambda x: "✅ sim" if x["C1_ddl_transacional"] else "❌ tabela órfã"),
        ("C2 índice único parcial", lambda x: x["C2_indice_parcial"]),
        ("C2 dois nomes vigentes", lambda x: sim_nao(x["C2_recusa_2_vigentes"])),
        ("C3 apagar ato com classificação (config padrão)", lambda x: sim_nao(x["C3_fk_padrao"])
            + (f" (com PRAGMA: {sim_nao(x['C3_fk_com_pragma'])})" if "C3_fk_com_pragma" in x else "")),
        ("C4 ato do DOU sem id_dou (CHECK)", lambda x: sim_nao(x["C4_check"])),
        ("C5 UPDATE em classificação (trigger)", lambda x: sim_nao(x["C5_trigger"])),
        ("CDC na configuração padrão", lambda x: x["cdc_padrao"]),
    ]
    for n in sorted(ns):
        linhas.append((f"Q1 vigente de 1 ato, n={n} (ms)", lambda x, n=n: x[f"Q1_ms_n{n}"]))
        linhas.append((f"Q2 indicador, n={n} (ms)", lambda x, n=n: x[f"Q2_ms_n{n}"]
                       if "Q2_distinct_on_ms_n%d" % n not in x
                       else f"{x[f'Q2_ms_n{n}']} ({x['Q2_distinct_on_ms_n%d' % n]} com DISTINCT ON)"))
    linhas += [
        ("download da imagem, comprimida (MB)", lambda x: x["imagem_mb"] or "— (biblioteca)"),
        ("até aceitar conexão (s)", lambda x: x["pronto_s"]),
        ("RAM após a carga (MB)", lambda x: x["ram_mb"]),
    ]
    out = cab + "".join(f"| {rot} | " + " | ".join(str(f(x)) for x in res) + " |\n" for rot, f in linhas)
    # sanidade: todos os motores precisam chegar à mesma resposta do indicador
    # Motor que aceitou o UPDATE do C5 teve 1 classificação alterada: é o efeito medido, não erro.
    for n in sorted(ns):
        respostas = {x["motor"]: [(t, int(c)) for t, c in x[f"Q2_resultado_n{n}"]] for x in res}
        protegidos = {m: v for m, v in respostas.items() if next(x for x in res if x["motor"] == m)["C5_trigger"]}
        iguais = len({json.dumps(v) for v in protegidos.values()}) == 1
        out += (f"\nQ2 n={n}: os motores que recusaram o UPDATE do C5 devolveram a mesma distribuição: "
                f"{'sim' if iguais else 'NÃO — ' + json.dumps(protegidos)}")
        for m, v in respostas.items():
            if m not in protegidos:
                ref = next(iter(protegidos.values()))
                dif = {t: c - dict(ref)[t] for t, c in v if c != dict(ref)[t]}
                out += f"\n  {m} aceitou o UPDATE do C5 e o indicador mudou: {dif}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, action="append", help="atos sintéticos (padrão: 2638 e 26380)")
    ap.add_argument("--motor", action="append", choices=["postgres", "mysql", "mariadb", "sqlite", "cassandra"])
    a = ap.parse_args()
    ns = a.n or [2638, 26380]
    motores = a.motor or ["postgres", "mysql", "mariadb", "sqlite", "cassandra"]
    res = []
    for m in motores:
        print(f"→ {m}", flush=True)
        try:
            res.append(medir_cassandra(ns) if m == "cassandra" else medir_relacional(m, ns))
        finally:
            if m != "sqlite":
                derrubar(m)
    saida = pathlib.Path(__file__).with_name("resultados.json")
    saida.write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    print()
    print(relatorio(res, ns))
    print(f"\n(dados brutos em {saida})")


if __name__ == "__main__":
    main()
