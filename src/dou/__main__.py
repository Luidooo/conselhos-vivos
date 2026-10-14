"""python -m dou <subcomando> — a porta de entrada da ingestão em Python.

Cada fatia da migração registra o seu subcomando em SUBCOMANDOS. Enquanto não
há nenhum, o comando só sabe dizer isso: é o que a #52 entrega, e o que o
teste de fumaça confere.
"""

import sys

# nome -> função(argv) que devolve o código de saída. Preenchido pelas fatias.
SUBCOMANDOS = {}


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
