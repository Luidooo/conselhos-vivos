"""Testes da identidade dos conselhos (#4, ADR 0004), só com unittest.

Rodam no serviço carga do compose (make test), ou no host com Python >= 3.11:
    PYTHONPATH=src python3 -m unittest discover -s tests/conselhos
Os casos de renomeação são os da issue #4, com os atos conferidos no planalto.gov.br.
"""

import csv
import datetime as dt
import io
import json
import pathlib
import tempfile
import unittest

from conselhos import siorg
from conselhos.carga import sql
from conselhos.identidade import ErroDeDecisao, chave, resolver
from conselhos.relatorio import relatorio

RAIZ = pathlib.Path(__file__).resolve().parents[2]
PLANILHA = RAIZ / "data/raw/Cópia_bancos_dados_Carla_Rocha.xlsx"
DECISOES = RAIZ / "data/referencia/conselhos-decisoes.csv"
SIORG = RAIZ / "data/referencia/siorg-conselhos.csv"
GABARITO = RAIZ / "docs/adr/medicoes/0004-identidade/gabarito.csv"
RES = resolver(PLANILHA, DECISOES, SIORG)
ALIAS = {a.linha: a for a in RES.aliases}
ORGAO = {o.nome: o for o in RES.orgaos}


def com_decisoes(troca):
    """Resolve com o CSV de decisões alterado por troca(linhas), uma lista de dicts."""
    with open(DECISOES, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        campos, linhas = r.fieldnames, list(r)
    linhas = troca(linhas)
    with tempfile.TemporaryDirectory() as d:
        caminho = pathlib.Path(d) / "decisoes.csv"
        with open(caminho, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, campos, lineterminator="\n")
            w.writeheader()
            w.writerows(linhas)
        return resolver(PLANILHA, caminho, SIORG)


def sem_linha(n):
    return lambda linhas: [x for x in linhas if x["linha"] != str(n)]


def muda(n, **campos):
    return lambda linhas: [{**x, **campos} if x["linha"] == str(n) else x for x in linhas]


class Chave(unittest.TestCase):
    def test_caixa_acento_e_sigla(self):
        self.assertEqual(chave("CONSELHO NACIONAL DE ASSISTÊNCIA SOCIAL"),
                         chave("Conselho Nacional de Assistência Social (CNAS)"))

    def test_quebra_de_linha_e_espaco_duplo(self):
        self.assertEqual(chave("Conselho Nacional de Política \nCriminal e  Penitenciária (CNPCP)"),
                         chave("Conselho Nacional de Política Criminal e Penitenciária"))

    def test_sigla_com_hifen(self):
        self.assertEqual(chave("CONSELHO NACIONAL DAS ZONAS DE PROCESSAMENTO DE EXPORTAÇÃO-CZPE"),
                         chave("Conselho Nacional das Zonas de Processamento de Exportação"))

    def test_de_e_do_nao_sao_a_mesma_chave(self):
        # a chave não adivinha: "de Meio Ambiente" só chega ao CONAMA por decisão registrada
        self.assertNotEqual(chave("Conselho Nacional de Meio Ambiente"), chave("Conselho Nacional do Meio Ambiente"))


class CasosDaIssue(unittest.TestCase):
    def test_cnas_grafias_diferentes(self):
        self.assertEqual(ALIAS[49].orgao, "Conselho Nacional de Assistência Social")
        self.assertEqual(ALIAS[50].orgao, "Conselho Nacional de Assistência Social")

    def test_idoso_renomeado_por_decreto(self):
        o = ORGAO["Conselho Nacional dos Direitos da Pessoa Idosa"]
        self.assertEqual(ALIAS[122].orgao, o.nome)
        self.assertEqual(ALIAS[118].orgao, o.nome)
        self.assertEqual(o.inicio, dt.date(2019, 6, 27))
        [antigo] = o.nomes_antigos
        self.assertEqual((antigo.nome, antigo.fim), ("Conselho Nacional dos Direitos do Idoso", dt.date(2019, 6, 26)))

    def test_pirataria_tres_grafias_um_orgao(self):
        self.assertEqual({ALIAS[n].orgao for n in (53, 54, 55)},
                         {"Conselho Nacional de Combate à Pirataria e Delitos contra a Propriedade Intelectual"})

    def test_fertilizantes_fica_ambiguo_e_separado(self):
        for n in (68, 69):
            self.assertEqual((ALIAS[n].status, ALIAS[n].orgao), ("AMBIGUO", None))
        self.assertNotEqual(ALIAS[68].chave, ALIAS[69].chave)

    def test_cddph_vira_cndh_com_a_lei(self):
        o = ORGAO["Conselho Nacional dos Direitos Humanos"]
        [antigo] = o.nomes_antigos
        self.assertEqual((antigo.inicio, antigo.fim, o.inicio),
                         (dt.date(1964, 3, 16), dt.date(2014, 6, 1), dt.date(2014, 6, 2)))
        self.assertEqual(ALIAS[27].orgao, o.nome)

    def test_mulher_e_mulheres(self):
        o = ORGAO["Conselho Nacional dos Direitos das Mulheres"]
        self.assertEqual({ALIAS[n].orgao for n in (115, 116, 119)}, {o.nome})
        self.assertEqual(o.nomes_antigos[0].nome, "Conselho Nacional dos Direitos da Mulher")

    def test_mesma_sigla_nao_junta(self):
        # CNE: Educação e Esporte; CNT: Trabalho e Turismo
        self.assertNotEqual(ALIAS[67].orgao, ALIAS[106].orgao)
        self.assertNotEqual(ALIAS[104].orgao, ALIAS[110].orgao)


class Aceite(unittest.TestCase):
    def test_toda_linha_tem_orgao_ou_esta_marcada(self):
        self.assertEqual(len(RES.aliases), 125)
        for a in RES.aliases:
            with self.subTest(linha=a.linha):
                if a.status == "RESOLVIDO":
                    self.assertIn(a.orgao, ORGAO)
                else:
                    self.assertIsNone(a.orgao)
                    self.assertTrue(a.motivo)

    def test_82_conselhos_e_5_pendencias(self):
        self.assertEqual(len(RES.orgaos), 82)
        self.assertEqual(sorted(a.linha for a in RES.aliases if a.status != "RESOLVIDO"), [28, 33, 44, 68, 69])

    def test_particao_igual_ao_gabarito_do_adr(self):
        with open(GABARITO, newline="", encoding="utf-8") as f:
            gab = {int(r["linha"]): r for r in csv.DictReader(f)}
        status = {"certo": "RESOLVIDO", "ambiguo": "AMBIGUO", "indefinido": "INDEFINIDO"}
        self.assertEqual({n: status[r["status"]] for n, r in gab.items()}, {n: a.status for n, a in ALIAS.items()})

        def particao(rotulo):
            grupos = {}
            for n, r in gab.items():
                if r["status"] == "certo":
                    grupos.setdefault(rotulo(n), set()).add(n)
            return sorted(map(sorted, grupos.values()))
        self.assertEqual(particao(lambda n: gab[n]["grupo"]), particao(lambda n: ALIAS[n].orgao))

    def test_os_5_da_planilha_sao_achados_pelo_nome_do_sql_004(self):
        for nome in ("Conselho Nacional de Assistência Social", "Conselho Nacional do Meio Ambiente",
                     "Conselho das Cidades", "Conselho Nacional de Desenvolvimento Rural Sustentável",
                     "Conselho Nacional de Promoção da Igualdade Racial"):
            self.assertIn(nome, ORGAO)


class Decisoes(unittest.TestCase):
    def test_linha_inexistente_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "linha 999"):
            com_decisoes(lambda ls: ls + [{**ls[0], "linha": "999"}])

    def test_nome_que_nao_bate_com_a_planilha_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "não bate"):
            com_decisoes(muda(77, nome_na_planilha="Conselho Nacional de Outra Coisa"))

    def test_grafia_para_orgao_inexistente_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "não é nome de nenhum órgão"):
            com_decisoes(muda(77, canonico="Conselho Nacional do Meio Ambiente e Mudança do Clima"))

    def test_grupo_sem_siorg_e_sem_decisao_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "sem unidade no SIORG e sem decisão"):
            com_decisoes(sem_linha(24))

    def test_decisao_nome_contra_o_siorg_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "o SIORG já dá o nome"):
            com_decisoes(lambda ls: ls + [{**ls[0], "linha": "49", "nome_na_planilha": "CONSELHO NACIONAL DE ASSISTÊNCIA SOCIAL",
                                           "tipo": "nome", "canonico": "Conselho Nacional de Assistência Social"}])

    def test_renomeacao_sem_ato_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "sem ato"):
            com_decisoes(muda(122, ato=""))

    def test_data_invalida_para(self):
        with self.assertRaisesRegex(ErroDeDecisao, "não é data"):
            com_decisoes(muda(27, troca="02/06/2014"))

    def test_virgula_sem_aspas_para(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = pathlib.Path(d) / "decisoes.csv"
            texto = DECISOES.read_text(encoding="utf-8")
            caminho.write_text(texto.replace(',nome genérico: 9 unidades', ',nome genérico, 9 unidades'), encoding="utf-8")
            with self.assertRaisesRegex(ErroDeDecisao, "número de colunas"):
                resolver(PLANILHA, caminho, SIORG)

    def test_ambiguo_resolvido_vira_orgao(self):
        res = com_decisoes(muda(68, tipo="grafia", canonico="Conselho Nacional de Justiça", motivo="teste"))
        self.assertEqual({a.linha: a for a in res.aliases}[68].status, "RESOLVIDO")


class Saidas(unittest.TestCase):
    def test_relatorio_deterministico(self):
        self.assertEqual(relatorio(RES), relatorio(resolver(PLANILHA, DECISOES, SIORG)))

    def test_sql_tem_todos_os_aliases(self):
        s = sql(RES)
        self.assertIn("'Conselho de Defesa dos Direitos da Pessoa Humana'", s)
        self.assertEqual(s.count("'PLANILHA'"), 1)
        self.assertIn("'Conselho Nacional de Combate à Pirataria e aos Delitos Ministério da Justiça e Segurança Pública'", s)

    def test_recorte_do_siorg(self):
        dados = json.dumps({"servico": {"data": "2026-01-01"}, "unidades": [
            {"nome": "Conselho Nacional de Saúde ", "sigla": "CNS", "codigoUnidade": "x/10",
             "codigoTipoUnidade": "x/unidade-colegiada"},
            *({"nome": "Conselho Deliberativo", "sigla": s, "codigoUnidade": f"x/{i}", "codigoTipoUnidade": "x/u"}
              for i, s in enumerate("AB"))]}).encode()
        linhas = {r["chave"]: r for r in csv.DictReader(io.StringIO(siorg.recorte(PLANILHA, dados).split("\n", 1)[1]))}
        self.assertEqual((linhas["conselho nacional de saude"]["codigo"], linhas["conselho nacional de saude"]["nome"]),
                         ("10", "Conselho Nacional de Saúde"))
        self.assertEqual((linhas["conselho deliberativo"]["unidades"], linhas["conselho deliberativo"]["codigo"]), ("2", ""))
        self.assertEqual(linhas["conselho da justica federal"]["unidades"], "0")


if __name__ == "__main__":
    unittest.main()
