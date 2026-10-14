"""python -m dou <subcomando> — a porta de entrada da ingestão em Python.

Cada fatia da migração registra o seu subcomando em SUBCOMANDOS.
"""

import sys

from . import extract, fetch_mensal, persist

# nome -> função(argv) que devolve o código de saída. Uma entrada por fatia.
SUBCOMANDOS = {
    "fetch-mensal": fetch_mensal.main,  # #53
    "extract": extract.main,  # #54
    "persist": persist.main,  # #55
}


def main(argv):
    uso = f"uso: python -m dou <subcomando> [opções]\nsubcomandos: {', '.join(sorted(SUBCOMANDOS)) or 'nenhum ainda'}"
    if argv and argv[0] in ("-h", "--help"):
        print(uso)  # ajuda pedida é saída normal: stdout, código 0
        return 0
    if not argv:
        print(uso, file=sys.stderr)  # falta o subcomando: erro de uso, código 2
        return 2
    if argv[0] not in SUBCOMANDOS:
        print(f"dou: subcomando desconhecido: {argv[0]}", file=sys.stderr)
        return 2
    return SUBCOMANDOS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
