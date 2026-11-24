"""O diagrama da linhagem gerado do manifest do dbt (src/linhagem). Sem dbt: um manifest mínimo, montado à mão.
Roda com make test-linhagem, ou no host: PYTHONPATH=src python3 -m unittest discover -s tests/linhagem
"""

import os
import tempfile
import unittest

from linhagem import FIM, INICIO, atualizar, mermaid

MANIFEST = {
    "sources": {"source.p.silver.atos": {"source_name": "silver", "name": "atos"}},
    "nodes": {
        "model.p.stg_atos": {"resource_type": "model", "name": "stg_atos", "fqn": ["p", "staging", "stg_atos"],
                             "depends_on": {"nodes": ["source.p.silver.atos"]}},
        "model.p.fct_ato": {"resource_type": "model", "name": "fct_ato", "fqn": ["p", "marts", "fct_ato"],
                            "depends_on": {"nodes": ["model.p.stg_atos", "model.p.stg_atos"]}},
        "test.p.unique_fct_ato": {"resource_type": "test", "name": "unique_fct_ato", "fqn": ["p", "unique_fct_ato"],
                                  "depends_on": {"nodes": ["model.p.fct_ato"]}},
    },
    "semantic_models": {
        "semantic_model.p.atos": {"name": "atos", "depends_on": {"nodes": ["model.p.fct_ato"]}},
    },
    "metrics": {
        "metric.p.atos_publicados": {"name": "atos_publicados", "depends_on": {"nodes": ["semantic_model.p.atos"]}},
    },
    "saved_queries": {
        "saved_query.p.atividade_por_mes": {"name": "atividade_por_mes", "depends_on": {"nodes": ["metric.p.atos_publicados"]}},
    },
}


class Mermaid(unittest.TestCase):
    def test_camadas_e_setas(self):
        d = mermaid(MANIFEST)
        self.assertIn('subgraph c0["fonte silver"]', d)
        self.assertIn('["silver.atos"]', d)
        self.assertIn('subgraph c1["staging"]', d)
        self.assertIn('subgraph c2["marts"]', d)
        self.assertEqual(d.count("-->"), 5, "a dependência repetida vira uma seta só")

    def test_camada_semantica_ate_a_consulta_salva(self):
        d = mermaid(MANIFEST)
        self.assertIn('subgraph c3["semântica"]', d)
        self.assertIn('subgraph c4["consultas salvas"]', d)
        self.assertIn('["métrica atos_publicados"]', d)
        self.assertEqual(d.count("-->"), 5, "fonte → stg → fct → modelo semântico → métrica → consulta")

    def test_teste_do_dbt_nao_entra(self):
        self.assertNotIn("unique_fct_ato", mermaid(MANIFEST))

    def test_mesma_entrada_mesmo_texto(self):
        self.assertEqual(mermaid(MANIFEST), mermaid(MANIFEST))


class Atualizar(unittest.TestCase):
    def test_troca_so_o_que_esta_entre_os_marcadores(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            pagina, man = os.path.join(d, "p.md"), os.path.join(d, "m.json")
            with open(man, "w") as f:
                json.dump(MANIFEST, f)
            with open(pagina, "w") as f:
                f.write(f"antes\n{INICIO}\nvelho\n{FIM}\ndepois\n")
            atualizar(pagina, man)
            texto = open(pagina).read()
        self.assertTrue(texto.startswith("antes\n"))
        self.assertTrue(texto.endswith(f"{FIM}\ndepois\n"))
        self.assertNotIn("velho", texto)
        self.assertIn("flowchart LR", texto)


if __name__ == "__main__":
    unittest.main()
