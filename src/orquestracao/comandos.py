"""O que os assets rodam e a regra de qual mês a agenda carrega. Fica fora do __init__ para os testes
importarem sem o manifesto do dbt."""

import subprocess
import sys
from datetime import date, timedelta

import dagster as dg

from dou import SAIDA_DE_DADO


def roda(context: dg.AssetExecutionContext, *cmd: str, de_dado: str | None = None) -> None:
    """Roda o comando e falha com o erro dele, tirado do stderr (#85). Se o comando sair com SAIDA_DE_DADO
    e `de_dado` disser o que isso significa, falha sem retry: repetir não resolve (#83, #84)."""
    context.log.info(" ".join(cmd))
    p = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    sys.stderr.write(p.stderr)  # continua nos compute logs, de onde o eventos_do_run.sh lê o resumo do persist
    if p.returncode == 0:
        return
    erro = _erro(p.stderr)
    if de_dado and p.returncode == SAIDA_DE_DADO:
        raise dg.Failure(description=f"{de_dado}: {erro}", allow_retries=False)
    raise dg.Failure(description=f"{' '.join(cmd[2:4])} saiu com {p.returncode}: {erro}")


def _erro(stderr: str) -> str:
    """A última linha [ERROR]; senão a última [WARNING] (o persist loga assim cada entrada que não lê);
    senão a última linha, como o fim de um traceback. O resumo do persist vem depois e não serve de causa."""
    linhas = [linha.strip() for linha in stderr.splitlines() if linha.strip()]
    for nivel in ("[ERROR]", "[WARNING]"):
        achadas = [linha for linha in linhas if nivel in linha]
        if achadas:
            return achadas[-1]
    return linhas[-1] if linhas else "nada no stderr"


def mes_a_carregar(hoje: date, carregados: set[str]) -> str | None:
    """A partição do mês anterior a `hoje` (AAAA-MM-01), ou None se ela já foi carregada (#83)."""
    mes = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()
    return None if mes in carregados else mes
