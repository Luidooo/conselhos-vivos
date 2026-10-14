"""Fumaça da infra de banco do dou (#52): o tearDown desfaz o que o teste gravou.

Dois testes, de propósito: o primeiro grava e termina sem desfazer nada; o
segundo abre outra conexão e confere que a linha não ficou. A ordem do
unittest é alfabética pelo nome do método, daí os prefixos.
"""

from dbtest import CasoComBanco

EMAIL = "fumaca-52@teste.local"


class TearDownDesfazATransacao(CasoComBanco):
    def test_1_grava_sem_desfazer(self):
        self.conn.execute(
            "INSERT INTO revisor (nome, tipo, email) VALUES ('Fumaça #52', 'HUMANO', %s)", (EMAIL,)
        )
        n = self.conn.execute("SELECT count(*) FROM revisor WHERE email = %s", (EMAIL,)).fetchone()[0]
        self.assertEqual(n, 1)
        # Sem rollback aqui: é o tearDown que tem de desfazer.

    def test_2_a_linha_do_teste_anterior_nao_ficou(self):
        n = self.conn.execute("SELECT count(*) FROM revisor WHERE email = %s", (EMAIL,)).fetchone()[0]
        self.assertEqual(n, 0)
