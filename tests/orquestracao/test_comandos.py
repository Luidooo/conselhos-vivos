"""O roda do orquestrador (#83, #84, #85) e a regra do mês da agenda (#83).

Falha de dado (código 3 com `de_dado`) não usa o retry; o resto usa. A causa de toda falha leva a última
linha do stderr do comando. Os comandos aqui são `sh -c` de mentira: sem rede, sem banco, sem dbt.
Roda no serviço orquestrador, que tem o Dagster, depois de um dbt parse que gera o manifesto que o pacote
lê ao ser importado: make test-orquestracao
"""

import unittest
from datetime import date

import dagster as dg

from orquestracao.comandos import mes_a_carregar, roda


def materializa(*cmd, de_dado=None):
    """Materializa um asset que roda `cmd`, com retry de 2 tentativas sem espera. Devolve os tipos de evento
    e a mensagem da falha, se houver."""
    @dg.asset(retry_policy=dg.RetryPolicy(max_retries=2, delay=0))
    def passo(context):
        roda(context, *cmd, de_dado=de_dado)

    resultado = dg.materialize([passo], raise_on_error=False)
    tipos = [e.event_type_value for e in resultado.all_events]
    # Como o eventos_do_run.sh: a causa encadeada quando há (depois do último retry, a falha só diz
    # "Exceeded max_retries"), senão a mensagem do próprio Failure.
    erros = [e.event_specific_data.error for e in resultado.all_events if e.is_step_failure]
    falha = (erros[0].cause or erros[0]).message if erros else None
    return tipos, falha


def sh(script):
    return ("sh", "-c", script)


class Roda(unittest.TestCase):
    def test_falha_de_dado_nao_usa_o_retry(self):
        tipos, falha = materializa(*sh("echo 'mes ainda nao publicado mes=2026-10' >&2; exit 3"),
                                   de_dado="mês ainda não publicado")
        self.assertNotIn("STEP_UP_FOR_RETRY", tipos)
        self.assertIn("STEP_FAILURE", tipos)
        self.assertIn("mês ainda não publicado: mes ainda nao publicado mes=2026-10", falha)

    def test_falha_de_infraestrutura_usa_o_retry_e_mostra_o_erro(self):
        tipos, falha = materializa(*sh("echo 'linha antiga' >&2; echo 'run aborted err=Name or service not known' >&2; exit 1"),
                                   de_dado="mês ainda não publicado")
        self.assertEqual(tipos.count("STEP_UP_FOR_RETRY"), 2)
        self.assertIn("saiu com 1: run aborted err=Name or service not known", falha)

    def test_a_causa_e_a_linha_de_erro_nao_o_resumo(self):
        # Como o persist: a entrada ruim vira [WARNING], e o resumo [INFO] vem depois.
        tipos, falha = materializa(*sh(
            "echo '[WARNING] falhou zip=/tmp/ruim.zip erro=materia-quebrada.xml: XML malformado' >&2; "
            "echo '[INFO] done gravadas=0 falhou=1' >&2; exit 3"), de_dado="entrada que não lê")
        self.assertIn("erro=materia-quebrada.xml: XML malformado", falha)
        self.assertNotIn("done gravadas", falha)

    def test_codigo_3_sem_de_dado_e_falha_comum(self):
        # O lake e o dbt não têm falha de dado: um 3 deles é repetido como qualquer outra falha.
        tipos, _ = materializa(*sh("echo 'erro do lake' >&2; exit 3"))
        self.assertEqual(tipos.count("STEP_UP_FOR_RETRY"), 2)

    def test_comando_que_passa_nao_falha(self):
        tipos, falha = materializa(*sh("echo 'done gravadas=1' >&2"))
        self.assertIn("STEP_SUCCESS", tipos)
        self.assertIsNone(falha)


class MesACarregar(unittest.TestCase):
    def test_o_mes_anterior_quando_ainda_nao_foi_carregado(self):
        self.assertEqual(mes_a_carregar(date(2026, 11, 15), set()), "2026-10-01")

    def test_nada_quando_ja_foi_carregado(self):
        self.assertIsNone(mes_a_carregar(date(2026, 11, 20), {"2026-10-01"}))

    def test_janeiro_carrega_dezembro_do_ano_anterior(self):
        self.assertEqual(mes_a_carregar(date(2027, 1, 15), {"2026-11-01"}), "2026-12-01")


if __name__ == "__main__":
    unittest.main()
