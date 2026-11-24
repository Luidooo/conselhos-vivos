"""O dicionário de dados gerado do manifest, do catalog do dbt e dos comentários do Postgres (src/dicionario)."""

import unittest

from dicionario import linhas, markdown, sem_descricao

MANIFEST = {"nodes": {"model.p.fct_ato": {"resource_type": "model", "name": "fct_ato", "fqn": ["p", "marts", "fct_ato"],
                                          "columns": {"ato_id": {"description": "Id do ato no OLTP."}}}},
            "sources": {}}
CATALOG = {"nodes": {"model.p.fct_ato": {"columns": {"ATO_ID": {"name": "ato_id", "type": "BIGINT"},
                                                     "MES": {"name": "mes", "type": "DATE"}}}},
           "sources": {}}
OLTP = [("ato", "id", "bigint", "Identificador do ato."), ("ato", "ementa", "text", None)]


class Dicionario(unittest.TestCase):
    def test_gold_e_oltp_juntos(self):
        l = linhas(MANIFEST, CATALOG, OLTP)
        self.assertIn(("gold", "fct_ato", "ato_id", "BIGINT", "Id do ato no OLTP."), l)
        self.assertIn(("oltp", "ato", "id", "bigint", "Identificador do ato."), l)

    def test_coluna_sem_descricao_e_apontada(self):
        self.assertEqual(sem_descricao(linhas(MANIFEST, CATALOG, OLTP)), ["gold.fct_ato.mes", "oltp.ato.ementa"])

    def test_markdown_tem_uma_tabela_por_camada(self):
        md = markdown(linhas(MANIFEST, CATALOG, OLTP))
        self.assertIn("## gold", md)
        self.assertIn("## oltp", md)
        self.assertIn("| fct_ato | ato_id | BIGINT | Id do ato no OLTP. |", md)


if __name__ == "__main__":
    unittest.main()
