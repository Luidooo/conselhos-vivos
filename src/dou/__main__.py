"""python -m dou <subcomando> — a porta de entrada da ingestão em Python.

Cada fatia da migração registra o seu subcomando em SUBCOMANDOS. Enquanto não
há nenhum, o comando só sabe dizer isso: é o que a #52 entrega, e o que o
teste de fumaça confere.
"""

import sys

# nome -> função(argv) que devolve o código de saída. Preenchido pelas fatias.
SUBCOMANDOS = {}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        nomes = ", ".join(sorted(SUBCOMANDOS)) or "nenhum ainda"
        print(f"uso: python -m dou <subcomando> [opções]\nsubcomandos: {nomes}", file=sys.stderr)
        return 2 if not argv else 0
    if argv[0] not in SUBCOMANDOS:
        print(f"dou: subcomando desconhecido: {argv[0]}", file=sys.stderr)
        return 2
    return SUBCOMANDOS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
