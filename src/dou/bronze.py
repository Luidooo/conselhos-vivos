"""O bronze: as edições do DOU em disco, de modo que um arquivo sob o nome
final seja sempre um ZIP inteiro e legível (o par do internal/store do Go).

O diretório também é o registro do que foi pedido: para uma edição há o ZIP,
um marcador dizendo que ela não existiu (`.sem-edicao`), um marcador dizendo
que a busca falhou (`.falhou`), ou nada — que é "ninguém buscou". Nunca dois
deles juntos, e o ZIP em disco vence os marcadores.
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


def nome_sem_edicao(nome):
    """`2026-10-04-DO1.zip` -> `2026-10-04-DO1.sem-edicao`."""
    return _sem_zip(nome) + SEM_EDICAO


def nome_falhou(nome):
    """`2026-10-04-DO1.zip` -> `2026-10-04-DO1.falhou`."""
    return _sem_zip(nome) + FALHOU


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

    def marcar_sem_edicao(self, nome):
        """O INLABS disse que a edição não existe. Sem o marcador, um dia sem
        edição e um dia que ninguém buscou ficariam iguais no disco."""
        self._marcar(nome, SEM_EDICAO, FALHOU)

    def marcar_falhou(self, nome):
        """A edição foi pedida e não chegou: é a que se busca de novo."""
        self._marcar(nome, FALHOU, SEM_EDICAO)

    def _marcar(self, nome, sufixo, outro):
        # O ZIP em disco vence: uma edição baixada existiu, e nem um "não
        # encontrada" nem uma falha posterior a desfazem.
        if self.tem(nome):
            return
        # O marcador antigo sai primeiro: uma queda no meio deixa nenhum
        # (um dia a buscar de novo), nunca dois que se contradizem.
        self._desmarcar(nome, outro)
        (self.dir / (_sem_zip(nome) + sufixo)).write_bytes(b"")
        _fsync_dir(self.dir)

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
