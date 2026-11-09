"""python -m linhagem PAGINA MANIFEST: atualiza o diagrama da linhagem do dbt na página do site."""

import sys

from . import atualizar

if __name__ == "__main__":
    atualizar(sys.argv[1], sys.argv[2])
