"""O exportador da camada semântica (src/metricas): lê as consultas salvas do semantic_manifest.json do dbt.
Sem dbt nem banco: o manifesto é montado à mão e o mf é trocado por um registro das chamadas."""

import unittest
from unittest import mock

from metricas import consultas, exportar

MANIFESTO = {"saved_queries": [{"name": "b_consulta"}, {"name": "a_consulta"}], "metrics": []}


class Consultas(unittest.TestCase):
    def test_todas_as_consultas_salvas_em_ordem(self):
        self.assertEqual(consultas(MANIFESTO), ["a_consulta", "b_consulta"])

    def test_manifesto_sem_consultas(self):
        self.assertEqual(consultas({}), [])


class Exportar(unittest.TestCase):
    def test_um_csv_por_consulta_no_destino(self):
        with mock.patch("metricas.subprocess.run") as run:
            run.return_value.returncode = 0
            exportar(["a_consulta"], "/tmp/m", projeto="/app/dbt")
        run.assert_called_once_with(
            ["mf", "query", "--saved-query", "a_consulta", "--csv", "/tmp/m/a_consulta.csv"],
            cwd="/app/dbt", check=True,
        )


if __name__ == "__main__":
    unittest.main()
