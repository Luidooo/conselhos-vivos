"""A gravação das menções na silver (src/mencoes/silver): idempotente, com update só quando o conteúdo muda,
e a tabela vazia criada quando não há nada. Precisa do deltalake: roda no serviço orquestrador (make test-mencoes).
"""

import datetime as dt
import tempfile
import unittest

try:
    from deltalake import DeltaTable
    from mencoes.silver import gravar, tabela
except ImportError:  # no host, sem o deltalake: os testes da extração rodam, estes ficam para o container
    DeltaTable = None


def mencao(id_dou="900", orgao_id=1, ementa="Homologa o parecer"):
    return {"id_dou": id_dou, "orgao_id": orgao_id, "nome_citado": "conselho nacional de educacao",
            "data_publicacao": dt.date(2026, 8, 3), "tipo_ato": "Despacho", "publicador": "Ministério da Educação",
            "titulo": "DESPACHO", "ementa": ementa, "assunto": "homologação", "fonte": "S01082026.zip"}


@unittest.skipIf(DeltaTable is None, "precisa do deltalake (make test-mencoes)")
class Gravar(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.destino = self._tmp.name + "/mencoes"

    def test_segunda_gravacao_nao_muda_nada(self):
        linhas = [mencao(), mencao(id_dou="901", orgao_id=2)]
        self.assertEqual(gravar(tabela(linhas), self.destino)["inseridas"], 2)
        self.assertEqual(gravar(tabela(linhas), self.destino), {"inseridas": 0, "atualizadas": 0, "inalteradas": 2})
        self.assertEqual(DeltaTable(self.destino).count(), 2)

    def test_conteudo_novo_atualiza_a_mesma_linha(self):
        gravar(tabela([mencao()]), self.destino)
        r = gravar(tabela([mencao(ementa="Homologa o parecer, retificado")]), self.destino)
        self.assertEqual((r["inseridas"], r["atualizadas"]), (0, 1))
        self.assertEqual(DeltaTable(self.destino).count(), 1)

    def test_mesma_materia_dois_conselhos_sao_duas_linhas(self):
        gravar(tabela([mencao(orgao_id=1), mencao(orgao_id=2)]), self.destino)
        self.assertEqual(DeltaTable(self.destino).count(), 2)

    def test_sem_nada_cria_a_tabela_vazia(self):
        self.assertEqual(gravar(tabela([]), self.destino)["inseridas"], 0)
        self.assertTrue(DeltaTable.is_deltatable(self.destino))
        self.assertEqual(DeltaTable(self.destino).count(), 0)


if __name__ == "__main__":
    unittest.main()
