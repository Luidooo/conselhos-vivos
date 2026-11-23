"""A regra do ETL reverso (src/alertas): que situação da mart_vitalidade vira alerta para a curadoria. Sem banco."""

import unittest
from datetime import date

from alertas import alertas

SET = date(2026, 9, 1)


def linha(**k):
    base = dict(orgao_id=1, nome="Conselho Um", sigla="C1", situacao="ativo", mes_referencia=SET,
                meses_sem_publicar=0, mencoes_no_periodo=0)
    return {**base, **k}


class Regra(unittest.TestCase):
    def test_ativo_nao_alerta(self):
        self.assertEqual(alertas([linha(mencoes_no_periodo=5)]), [])

    def test_em_silencio_alerta(self):
        [a] = alertas([linha(situacao="em silêncio", meses_sem_publicar=5)])
        self.assertEqual((a.orgao_id, a.tipo, a.mes_referencia), (1, "em_silencio", SET))
        self.assertIn("5 meses sem ato próprio", a.detalhe)

    def test_em_silencio_sem_nunca_publicar(self):
        [a] = alertas([linha(situacao="em silêncio", meses_sem_publicar=None)])
        self.assertIn("nenhum ato próprio no período coberto", a.detalhe)

    def test_sem_ato_mas_citado(self):
        [a] = alertas([linha(situacao="sem ato no período coberto", meses_sem_publicar=None, mencoes_no_periodo=2)])
        self.assertEqual(a.tipo, "citado_sem_ato_proprio")
        self.assertIn("citado 2 vez(es)", a.detalhe)

    def test_silencio_e_citado_dao_dois_alertas(self):
        tipos = [a.tipo for a in alertas([linha(situacao="em silêncio", meses_sem_publicar=4, mencoes_no_periodo=1)])]
        self.assertEqual(tipos, ["em_silencio", "citado_sem_ato_proprio"])

    def test_sem_mes_de_referencia_nao_alerta(self):
        # gold sem DOU, como num clone limpo: não há período coberto para afirmar nada
        self.assertEqual(alertas([linha(situacao="em silêncio", mes_referencia=None)]), [])


if __name__ == "__main__":
    unittest.main()
