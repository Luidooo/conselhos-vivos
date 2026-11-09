"""O bronze: as edições do DOU em disco, de modo que um arquivo sob o nome
final seja sempre um ZIP inteiro e legível.

Os marcadores `.sem-edicao` e `.falhou` (ADR 0008) vêm do cliente do INLABS, que
saiu: ninguém mais os escreve, e o `TEM_EDICAO` do Makefile ainda lê os que
estão em disco. Aqui só se grava o ZIP, e gravá-lo apaga os marcadores da sua
edição.
"""

import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

SEM_EDICAO = ".sem-edicao"
FALHOU = ".falhou"


class NaoEZip(Exception):
    """O corpo salvo não abre como ZIP: a página de login no lugar da edição."""


@dataclass(frozen=True)
class Recibo:
    """O que chegou ao disco, para o log e o resumo."""

    caminho: Path
    tamanho: int


def _sem_zip(nome):
    return nome[: -len(".zip")] if nome.endswith(".zip") else nome


class Bronze:
    """Grava num diretório, que tem de existir: criá-lo aqui esconderia um
    volume que não foi montado, e as edições iriam parar dentro do container."""

    def __init__(self, diretorio):
        self.dir = Path(diretorio)
        if not self.dir.exists():
            raise FileNotFoundError(f"o diretório de saída {self.dir} não existe")
        if not self.dir.is_dir():
            raise NotADirectoryError(f"o caminho de saída {self.dir} não é um diretório")

    def tem(self, nome):
        """Só o ZIP conta — um marcador não é a edição."""
        return (self.dir / nome).is_file()

    def salvar(self, nome, corpo):
        """Copia `corpo` (um objeto com .read) para dir/nome, e só deixa o nome
        final existir quando os bytes são um ZIP que abre.

        A ordem é o ponto: temporário no mesmo diretório (renomear entre
        sistemas de arquivos falha), cópia, fsync, validação do ZIP, rename,
        fsync do diretório. Validar depois do rename deixaria um arquivo
        corrompido sob o nome em que todo o resto confia.
        """
        temp = tempfile.NamedTemporaryFile(dir=self.dir, prefix=nome + ".part-", delete=False)
        caminho_temp = Path(temp.name)
        try:
            with temp:
                tamanho = _copiar(corpo, temp)
                temp.flush()
                os.fsync(temp.fileno())
            # Abre o diretório central: é o que o leitor vai exigir depois.
            try:
                with zipfile.ZipFile(caminho_temp) as z:
                    z.infolist()
            except zipfile.BadZipFile as e:
                raise NaoEZip(f"{nome} is not a zip ({tamanho} bytes): {e}") from e
            final = self.dir / nome
            os.replace(caminho_temp, final)
        finally:
            # Depois do rename o temporário já não existe: remover é inócuo.
            # Isso cobre toda falha acima sem precisar saber onde parou.
            caminho_temp.unlink(missing_ok=True)

        # A edição existe agora, o que quer que uma busca anterior tenha dito.
        self._desmarcar(nome, SEM_EDICAO, FALHOU)
        _fsync_dir(self.dir)
        return Recibo(caminho=final, tamanho=tamanho)

    def _desmarcar(self, nome, *sufixos):
        for sufixo in sufixos:
            (self.dir / (_sem_zip(nome) + sufixo)).unlink(missing_ok=True)


def _copiar(origem, destino):
    """shutil.copyfileobj contando os bytes."""
    total = 0
    while True:
        bloco = origem.read(1 << 16)
        if not bloco:
            return total
        destino.write(bloco)
        total += len(bloco)


def _fsync_dir(diretorio):
    """Torna o rename durável: sem isso, uma queda pode perder a entrada do
    diretório mesmo com os bytes do arquivo já no disco."""
    fd = os.open(diretorio, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
