# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Medição do diário de 26/09 (#3): com que ferramenta, e de que jeito, extrair a planilha da pesquisadora.

Candidatos (candidatos/*.py), todos com o mesmo contrato:

    python candidato.py planilha.xlsx  >  CSV no stdout
    cabeçalho: aba,linha,id_versao,data,ref_legal,tipologia,tema
    uma linha por linha do Excel com pelo menos um valor, na ordem das abas
    (CNAS, CONAMA, CONCIDADES, CONDRAF, CNPIR) e da linha; erro = saída != 0

Mede:
  A1-A8  as armadilhas desta planilha, conferidas contra um gabarito fixo
  M1-M2  duas mutações: a planilha muda e nenhuma linha pode sumir em silêncio
  sondas o que a chamada mais direta de cada biblioteca faz, sem contorno
  como   container no compose × `uv run` no host (máquina limpa simulada num container)

Uso, a partir da raiz do repositório (só precisa de Python >= 3.11 e Docker):
    python3 docs/diario/medicoes/2026-09-26-extracao/bench.py

Nada toca o banco do projeto; as imagens e volumes criados são removidos no fim.
"""

import datetime as dt
import hashlib
import json
import pathlib
import platform
import re
import shutil
import statistics
import subprocess
import tempfile
import time
import tomllib
import zipfile

AQUI = pathlib.Path(__file__).resolve().parent  # absoluto: vai para o `docker run -v`
PLANILHA = pathlib.Path("data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx")
CANDIDATOS = ["stdlib", "pandas_openpyxl", "duckdb_sql"]
BASE = "python:3.12-slim"
UV = "ghcr.io/astral-sh/uv:0.9.30-python3.12-bookworm-slim"
RUNS = 5  # execuções medidas (depois de 1 aquecimento); reporta a mediana

# ---------------------------------------------------------------- gabarito
# Conferido à mão contra o XML e contra o texto do TEMA (diário de 26/09).
CONTAGEM = {"CNAS": 53, "CONAMA": 98, "CONCIDADES": 28, "CONDRAF": 24, "CNPIR": 12}
PONTOS = {  # (aba, linha do Excel): campos esperados
    ("CNAS", 2): {"id_versao": "1", "data": "2003-02-19", "tipologia": "AUTO"},
    ("CNAS", 26): {"id_versao": "47", "data": "2004-08-25", "tipologia": "99"},
    ("CONAMA", 3): {"id_versao": "351", "data": "2003-01-08", "ref_legal": "Moção"},
    ("CONDRAF", 6): {"id_versao": "5", "ref_legal": "Resoluções de 5 de abril de 2004"},
    ("CNPIR", 6): {"id_versao": "5", "data": "2013-04-08", "tipologia": "99 MOÇÃO"},
}
CNPIR_REF = ["1/2005", "2/2006", "3/2007", "4/2011", "7/2013 (moção)", "2/2016",
             "1/2016", "1/2017", "3/2020", "2/2020", "8/2020", "9/2020"]


# ---------------------------------------------------------------- utilidades

def sh(*args, check=True, entrada=None):
    return subprocess.run(args, capture_output=True, text=True, check=check, input=entrada)


def cronometra(*args, check=True):
    t0 = time.perf_counter()
    r = sh(*args, check=check)
    return time.perf_counter() - t0, r


def tamanho_imagem(img):
    return int(sh("docker", "image", "inspect", "-f", "{{.Size}}", img).stdout)


def dependencias(candidato):
    texto = (AQUI / "candidatos" / f"{candidato}.py").read_text()
    bloco = re.search(r"^# /// script\n(.*?)^# ///$", texto, re.S | re.M)[1]
    return tomllib.loads("".join(l.removeprefix("# ").removeprefix("#") + "\n" for l in bloco.splitlines()))[
        "dependencies"]


def linhas_de_codigo(candidato):
    texto = (AQUI / "candidatos" / f"{candidato}.py").read_text()
    return sum(1 for l in texto.splitlines() if l.strip() and not l.strip().startswith("#"))


def le_csv(texto):
    import csv
    import io
    return list(csv.DictReader(io.StringIO(texto)))


# ---------------------------------------------------------------- mutações

def muta(origem, destino, aba_xml, troca_folha, troca_textos=None):
    with zipfile.ZipFile(origem) as zin, zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            dados = zin.read(info.filename)
            if info.filename == aba_xml:
                dados = troca_folha(dados.decode()).encode()
            elif info.filename == "xl/sharedStrings.xml" and troca_textos:
                dados = troca_textos(dados.decode()).encode()
            zout.writestr(info, dados)


def prepara(tmp):
    shutil.copy(PLANILHA, tmp / "planilha.xlsx")
    folha = "xl/worksheets/sheet3.xml"  # CNAS
    with zipfile.ZipFile(PLANILHA) as z:
        n_textos = z.read("xl/sharedStrings.xml").decode().count("<si>")

    # M1: a data da linha 3 do CNAS vira o texto "s/d"
    muta(PLANILHA, tmp / "data_texto.xlsx", folha,
         lambda s: re.sub(r'<c r="C3" s="(\d+)"><v>[^<]*</v></c>', rf'<c r="C3" s="\1" t="s"><v>{n_textos}</v></c>', s),
         lambda s: s.replace("</sst>", "<si><t>s/d</t></si></sst>"))

    # M2: alguém apaga o conteúdo da linha 10 do CNAS (a formatação fica)
    def esvazia(s):
        return re.sub(r'(<row r="10"[^>]*>)(.*?)(</row>)',
                      lambda m: m[1] + re.sub(r'<c r="([A-Z]+10)" s="(\d+)"(?: t="\w+")?><v>[^<]*</v></c>',
                                              r'<c r="\1" s="\2"/>', m[2]) + m[3], s, flags=re.S)
    muta(PLANILHA, tmp / "linha_vazia.xlsx", folha, esvazia)


# ---------------------------------------------------------------- critérios

def confere(registros):
    por_chave = {(r["aba"], int(r["linha"])): r for r in registros}
    contagem = {a: sum(1 for r in registros if r["aba"] == a) for a in CONTAGEM}
    pontos_ok = all(k in por_chave and all(por_chave[k][c] == v for c, v in esperado.items())
                    for k, esperado in PONTOS.items())
    tipos = [r["tipologia"] for r in registros]
    return {
        "A1 conta 215, não 2.638": contagem == CONTAGEM,
        "A2 cabeçalho do CONAMA na linha 2": por_chave.get(("CONAMA", 3), {}).get("id_versao") == "351",
        "A3 data serial → ISO, nas 215": all(re.fullmatch(r"\d{4}-\d\d-\d\d", r["data"]) for r in registros)
                                          and pontos_ok,
        "A4 CNPIR: '1/2005' recuperado": [r["ref_legal"] for r in registros if r["aba"] == "CNPIR"] == CNPIR_REF,
        "A5 tipologia mista (99 no meio de texto)": all(tipos) and tipos.count("99") == 5
                                                     and tipos.count("99 MOÇÃO") == 1,
        "A6 linha do Excel de cada registro": pontos_ok and len(por_chave) == len(registros),
    }


def erro(r):
    linhas = r.stderr.strip().splitlines()
    return next((l for l in reversed(linhas) if "Error" in l or "Exception" in l), linhas[-1]).strip()[:120]


def classifica_m1(r, original):
    if r.returncode != 0:
        return f"falha e para: {erro(r)}"
    regs = {(x["aba"], x["linha"]): x for x in le_csv(r.stdout)}
    if ("CNAS", "3") not in regs:
        return "SILENCIOSO: a linha sumiu"
    return f"SILENCIOSO: data = {regs[('CNAS', '3')]['data']!r}"


def classifica_m2(r, original):
    if r.returncode != 0:
        return f"falha e para: {erro(r)}"
    esperado = [(x["aba"], x["linha"], x["id_versao"]) for x in original if (x["aba"], x["linha"]) != ("CNAS", "10")]
    obtido = [(x["aba"], x["linha"], x["id_versao"]) for x in le_csv(r.stdout)]
    if obtido == esperado:
        return "ok: 214 registros, linhas certas"
    if len(obtido) < len(esperado):
        return f"SILENCIOSO: {len(esperado) - len(obtido)} registros a menos"
    return f"SILENCIOSO: linha errada em {sum(a != b for a, b in zip(obtido, esperado))} registros"


# ---------------------------------------------------------------- execução

def imagem(candidato, tmp):
    deps = dependencias(candidato)
    linhas = [f"FROM {BASE}"]
    if deps:
        linhas.append("RUN pip install --no-cache-dir --root-user-action=ignore " + " ".join(deps))
    if candidato == "duckdb_sql":  # a extensão excel vem da internet; no container, fica na imagem
        linhas.append("RUN python -c \"import duckdb; duckdb.sql('INSTALL excel')\"")
    linhas += ["COPY cand.py /app/cand.py", 'ENTRYPOINT ["python", "/app/cand.py"]']
    ctx = tmp / f"ctx-{candidato}"
    ctx.mkdir()
    (ctx / "Dockerfile").write_text("\n".join(linhas) + "\n")
    shutil.copy(AQUI / "candidatos" / f"{candidato}.py", ctx / "cand.py")
    if candidato != "stdlib":
        shutil.copytree(AQUI / "sondas", ctx / "sondas")
        (ctx / "Dockerfile").write_text("\n".join(linhas[:-2] + ["COPY sondas /app/sondas"] + linhas[-2:]) + "\n")
    tag = f"bench3-{candidato.replace('_', '-')}"
    t, _ = cronometra("docker", "build", "--no-cache", "-q", "-t", tag, str(ctx))
    return tag, t


def mede(candidato, tmp):
    vol = ["-v", f"{tmp}:/w:ro"]
    tag, t_build = imagem(candidato, tmp)
    roda = lambda arq: sh("docker", "run", "--rm", *vol, tag, f"/w/{arq}", check=False)

    r1, r2 = roda("planilha.xlsx"), roda("planilha.xlsx")
    if r1.returncode != 0:
        raise SystemExit(f"{candidato} falhou na planilha original:\n{r1.stderr}")
    registros = le_csv(r1.stdout)
    tempos = [cronometra("docker", "run", "--rm", *vol, tag, "/w/planilha.xlsx")[0] for _ in range(RUNS)]

    res = {
        "dependencias": dependencias(candidato),
        "linhas_de_codigo": linhas_de_codigo(candidato),
        "criterios": confere(registros) | {
            "A7 determinístico (2 execuções, mesmo sha256)":
                hashlib.sha256(r1.stdout.encode()).hexdigest() == hashlib.sha256(r2.stdout.encode()).hexdigest()},
        "M1 data vira texto 's/d'": classifica_m1(roda("data_texto.xlsx"), registros),
        "M2 linha 10 do CNAS esvaziada": classifica_m2(roda("linha_vazia.xlsx"), registros),
        "container": {"build_s": round(t_build, 1),
                      "imagem_mb": max(0.0, round((tamanho_imagem(tag) - tamanho_imagem(BASE)) / 1e6, 1)),
                      "execucao_s": round(statistics.median(tempos), 2)},
        "uv": mede_uv(candidato, tmp),
    }
    if candidato != "stdlib":
        s = sh("docker", "run", "--rm", *vol, "--entrypoint", "python", tag, f"/app/sondas/{candidato}.py")
        res["sonda"] = json.loads(s.stdout)
    return res, registros, tag


def mede_uv(candidato, tmp):
    """`uv run --script` numa máquina limpa que só tem o uv: fria (sem cache) e quente (com cache)."""
    vol_c = ["-v", f"{AQUI / 'candidatos'}:/c:ro", "-v", f"{tmp}:/w:ro"]
    cmd = ["uv", "run", "--quiet", "--script", f"/c/{candidato}.py", "/w/planilha.xlsx"]
    t_frio, _ = cronometra("docker", "run", "--rm", *vol_c, UV, *cmd)
    cache = f"bench3-uv-{candidato.replace('_', '-')}"
    sh("docker", "volume", "create", cache)
    try:
        quente = ["docker", "run", "--rm", *vol_c, "-v", f"{cache}:/root", UV, *cmd]
        sh(*quente)  # aquecimento
        tempos = [cronometra(*quente)[0] for _ in range(RUNS)]
        mb = int(sh("docker", "run", "--rm", "-v", f"{cache}:/root", UV, "du", "-sb", "/root").stdout.split()[0])
    finally:
        sh("docker", "volume", "rm", "-f", cache, check=False)
    return {"primeira_execucao_s": round(t_frio, 1), "execucao_s": round(statistics.median(tempos), 2),
            "cache_mb": round(mb / 1e6, 1)}


def ambiente():
    cpu = next((l.split(":", 1)[1].strip() for l in pathlib.Path("/proc/cpuinfo").read_text().splitlines()
                if l.startswith("model name")), platform.processor()) if pathlib.Path("/proc/cpuinfo").exists() \
        else platform.processor()
    return {"quando": dt.datetime.now().isoformat(timespec="seconds"), "so": platform.platform(), "cpu": cpu,
            "docker": sh("docker", "version", "-f", "{{.Server.Version}}").stdout.strip(),
            "planilha_sha256": hashlib.sha256(PLANILHA.read_bytes()).hexdigest(),
            "base_mb": round(tamanho_imagem(BASE) / 1e6, 1), "uv_mb": round(tamanho_imagem(UV) / 1e6, 1)}


def main():
    sh("docker", "pull", "-q", BASE)
    sh("docker", "pull", "-q", UV)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="bench3-"))
    tags, saidas, resultados = [], {}, {"ambiente": ambiente(), "candidatos": {}}
    try:
        prepara(tmp)
        for c in CANDIDATOS:
            print(f"→ {c}", flush=True)
            res, registros, tag = mede(c, tmp)
            tags.append(tag)
            saidas[c] = registros
            resultados["candidatos"][c] = res
        for c in CANDIDATOS:  # A8: os leitores concordam campo a campo?
            outros = [o for o in CANDIDATOS if o != c]
            resultados["candidatos"][c]["criterios"]["A8 mesmos 215 registros que os outros candidatos"] = all(
                saidas[c] == saidas[o] for o in outros)
    finally:
        for t in tags:
            sh("docker", "rmi", "-f", t, check=False)
        shutil.rmtree(tmp, ignore_errors=True)

    (AQUI / "resultados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n")
    imprime(resultados)


def imprime(res):
    cs = res["candidatos"]
    print(f"\n| | {' | '.join(CANDIDATOS)} |\n|---|{'---|' * len(CANDIDATOS)}")
    for k in cs[CANDIDATOS[0]]["criterios"]:
        print(f"| {k} | " + " | ".join("✅" if cs[c]["criterios"][k] else "❌" for c in CANDIDATOS) + " |")
    for k in ["M1 data vira texto 's/d'", "M2 linha 10 do CNAS esvaziada"]:
        print(f"| {k} | " + " | ".join(cs[c][k] for c in CANDIDATOS) + " |")
    print(f"| linhas de código | " + " | ".join(str(cs[c]["linhas_de_codigo"]) for c in CANDIDATOS) + " |")
    for modo in ["container", "uv"]:
        for k in cs[CANDIDATOS[0]][modo]:
            print(f"| {modo}: {k} | " + " | ".join(str(cs[c][modo][k]) for c in CANDIDATOS) + " |")
    for c in CANDIDATOS:
        if "sonda" in cs[c]:
            print(f"\nsonda {c}:")
            for k, v in cs[c]["sonda"].items():
                print(f"  {k}: {v}")
    print(f"\nambiente: {res['ambiente']}")


if __name__ == "__main__":
    main()
