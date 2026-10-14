"""Fumaça da infra de banco do dou (#52): a transação do teste é desfeita."""

from dbtest import CasoComBanco


class TransacaoDesfeita(CasoComBanco):
    def test_o_que_o_teste_grava_nao_fica(self):
        antes = self.conn.execute("SELECT count(*) FROM revisor").fetchone()[0]
        self.conn.execute(
            "INSERT INTO revisor (nome, tipo, email) VALUES ('Fumaça #52', 'HUMANO', 'fumaca-52@teste.local')"
        )
        dentro = self.conn.execute("SELECT count(*) FROM revisor").fetchone()[0]
        self.assertEqual(dentro, antes + 1)
        # O tearDown faz rollback; um segundo teste abriria outra conexão e
        # veria `antes`. Conferimos aqui mesmo, com rollback explícito.
        self.conn.rollback()
        depois = self.conn.execute("SELECT count(*) FROM revisor").fetchone()[0]
        self.assertEqual(depois, antes)
