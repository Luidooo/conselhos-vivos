"""A busca do RAG (src/painel/busca.py) no Postgres, em transação desfeita: acha pela raiz da palavra, fica com a
versão mais recente da matéria e respeita os filtros."""

import unittest
from datetime import date

import dbtest

from painel.busca import buscar


class Busca(dbtest.CasoComBanco):
    def setUp(self):
        super().setUp()
        self.orgao = self.conn.execute("insert into orgao default values returning id").fetchone()[0]
        self.conn.execute("insert into orgao_nome (orgao_id, nome, data_inicio) values (%s, 'Conselho de Teste', '2000-01-01')", (self.orgao,))
        atos = [
            ("BUSCA-1", 1, "2026-08-10", "<p>Aprova o licenciamento ambiental de empreendimentos de saneamento.</p>"),
            ("BUSCA-1", 2, "2026-08-12", "<p>Aprova o licenciamento ambiental de empreendimentos de saneamento, retificado.</p>"),
            ("BUSCA-2", 1, "2026-09-01", "<p>Altera o regimento interno do conselho.</p>"),
        ]
        for id_dou, versao, data, texto in atos:
            self.conn.execute("insert into ato (origem, id_dou, versao, orgao_id, data_publicacao, conteudo) "
                              "values ('DOU', %s, %s, %s, %s, %s)", (id_dou, versao, self.orgao, data, texto))

    def test_acha_pela_raiz_e_so_a_versao_mais_recente(self):
        achados = buscar(self.conn, "licenciar empreendimentos", orgao=self.orgao)
        self.assertEqual([(a.id_dou, a.data) for a in achados], [("BUSCA-1", date(2026, 8, 12))])
        self.assertEqual(achados[0].conselho, "Conselho de Teste")
        self.assertNotIn("<p>", achados[0].trecho)

    def test_filtro_de_data(self):
        self.assertEqual(buscar(self.conn, "licenciamento", orgao=self.orgao, de=date(2026, 9, 1)), [])

    def test_pergunta_so_com_palavras_vazias(self):
        self.assertEqual(buscar(self.conn, "o que e de", orgao=self.orgao), [])


if __name__ == "__main__":
    unittest.main()
