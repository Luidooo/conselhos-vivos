"""python -m dou persist EDICAO.zip: grava no banco de curadoria as matérias de
uma edição já em disco (o par do cmd/persist do Go). Só orquestra: a leitura é
do materia, a escrita é do oltp.

Um ZIP por execução, como no extract, e uma transação por ZIP: a edição entra
inteira ou não entra. Pode rodar de novo: o que já está lá fica como está, e
um id que vem duas vezes no ZIP conta uma. XML que não é matéria é falha, e a
saída é 1 mesmo com o resto do ZIP gravado e confirmado.
"""

import argparse
import logging
import sys
import zipfile
from dataclasses import dataclass

from . import db, materia, oltp

logger = logging.getLogger("dou.persist")


@dataclass
class Resumo:
    gravadas: int = 0            # matéria escrita pela primeira vez
    versoes_novas: int = 0       # já estava e voltou diferente
    inalteradas: int = 0         # já estava como está
    orgao_desconhecido: int = 0  # fora de ato; o órgão foi para a fila
    repetidas: int = 0           # id que outra entrada do ZIP já tinha: fora, diga o que disser
    ignoradas: int = 0           # entrada que não é XML
    falhou: int = 0              # XML que não leu como matéria, ou sem <Texto>


def persistir(conn, caminho):
    """Grava toda matéria do ZIP por `conn`. Entrada ruim é logada e contada;
    ZIP que não abre, ou banco que recusa uma escrita, encerra a execução.

    De duas entradas com o mesmo id, a primeira no ZIP é a matéria e a outra
    fica de fora. Gravar as duas faria da segunda uma versão nova da primeira,
    e da execução seguinte uma versão nova da segunda: o mesmo ZIP nunca
    pararia de escrever.
    """
    resumo = Resumo()
    with zipfile.ZipFile(caminho) as edicao:
        gravador = oltp.Gravador(conn)
        vistos = {}  # id -> entrada que o teve primeiro
        for item, erro in materia.ler(edicao):
            if erro is not None:
                if isinstance(erro.__cause__, materia.NaoEXML):
                    resumo.ignoradas += 1
                    logger.info("ignorada zip=%s erro=%s", caminho, erro)
                else:
                    resumo.falhou += 1
                    logger.warning("falhou zip=%s erro=%s", caminho, erro)
                continue
            if item.id in vistos:
                resumo.repetidas += 1
                logger.warning("repetida zip=%s entrada=%s id=%s primeira=%s", caminho, item.entry, item.id, vistos[item.id])
                continue
            vistos[item.id] = item.entry
            try:
                desfecho = gravador.salvar(item)
            except oltp.SemConteudo as e:
                resumo.falhou += 1
                logger.warning("falhou zip=%s erro=%s", caminho, e)
                continue
            if desfecho is oltp.Desfecho.GRAVADA:
                resumo.gravadas += 1
            elif desfecho is oltp.Desfecho.VERSAO_NOVA:
                resumo.versoes_novas += 1
                logger.info("versao-nova zip=%s entrada=%s id=%s", caminho, item.entry, item.id)
            elif desfecho is oltp.Desfecho.INALTERADA:
                resumo.inalteradas += 1
            else:
                resumo.orgao_desconhecido += 1
    return resumo


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
    parser = argparse.ArgumentParser(prog="python -m dou persist", description=__doc__.split("\n\n")[0])
    parser.add_argument("zip", metavar="EDICAO.zip")
    args = parser.parse_args(argv)
    try:
        with db.conectar() as conn:  # o `with` confirma ao sair sem exceção, desfaz com exceção
            resumo = persistir(conn, args.zip)
    except (zipfile.BadZipFile, OSError) as e:
        logger.error("run aborted err=opening %s: %s", args.zip, e)
        return 1
    except Exception as e:
        logger.error("run aborted err=%s", e)
        return 1
    logger.info("done gravadas=%d versoes-novas=%d inalteradas=%d orgao-desconhecido=%d repetidas=%d ignoradas=%d falhou=%d",
                resumo.gravadas, resumo.versoes_novas, resumo.inalteradas, resumo.orgao_desconhecido,
                resumo.repetidas, resumo.ignoradas, resumo.falhou)
    # O ZIP já foi confirmado: 1 diz que uma entrada falhou, não que nada entrou.
    return 1 if resumo.falhou else 0
