"""Resposta do RAG (E4, ADR 0012): manda à API do Claude a pergunta e os atos que a busca achou, e devolve a resposta
citando os atos por número. Resposta que cita um ato que não foi enviado é recusada: o assistente só afirma o que
está nos atos. Sem ato achado, a API nem é chamada."""

import os
import re
from dataclasses import dataclass

MODELO = os.environ.get("PERGUNTAR_MODELO", "claude-sonnet-5-5")

# O raciocínio do modelo sai do mesmo teto que a resposta: com 1024, uma pergunta difícil seria cortada antes do texto.
MAX_TOKENS = 16000
# Se os filtros de segurança do modelo recusarem o pedido, a própria API tenta de novo num modelo de reserva,
# escolhido por ela. Só existe no endpoint beta, e por isso a chamada é cliente.beta.messages.create.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SISTEMA = (
    "Você responde perguntas sobre atos de conselhos nacionais de participação social publicados no Diário Oficial "
    "da União. Use só os atos fornecidos. Cite cada afirmação com o número do ato entre colchetes, como [2]. "
    "Se os atos não respondem a pergunta, diga que não encontrou a resposta nos atos achados; não complete com o "
    "que você sabe. Responda em português, em poucas frases."
)


class CitacaoInvalida(Exception):
    pass


class Recusada(Exception):
    """O modelo, e o de reserva, recusaram responder: não há texto para mostrar."""


@dataclass(frozen=True)
class Resposta:
    texto: str
    citados: list[int]
    tokens: int
    cortada: bool = False  # bateu no teto de tokens: o texto pode ter parado no meio


def contexto(pergunta, atos):
    blocos = [f"[{i}] {a.conselho}, {a.data:%d/%m/%Y}, DOU {a.id_dou or 'planilha'}\n"
              f"Ementa: {a.ementa or '-'}\nTrecho: {a.trecho}" for i, a in enumerate(atos, 1)]
    return "Atos encontrados:\n\n" + "\n\n".join(blocos) + f"\n\nPergunta: {pergunta}"


def responder(pergunta, atos, cliente, modelo=MODELO):
    if not atos:
        return Resposta("Não encontrei atos que respondam a essa pergunta.", [], 0)
    # Sem temperature nem thinking: o Sonnet 5.5 recusa os dois (400) e raciocina por conta própria.
    msg = cliente.beta.messages.create(model=modelo, max_tokens=MAX_TOKENS, system=SISTEMA,
                                       betas=[FALLBACK_BETA], fallbacks="default",
                                       messages=[{"role": "user", "content": contexto(pergunta, atos)}])
    if msg.stop_reason == "refusal":
        raise Recusada("o modelo recusou responder a essa pergunta")
    # Antes do texto vêm blocos de raciocínio, vazios: só os de texto são a resposta.
    texto = "".join(b.text for b in msg.content if b.type == "text")
    citados = list(dict.fromkeys(int(n) for n in re.findall(r"\[(\d+)\]", texto)))
    fora = [n for n in citados if not 1 <= n <= len(atos)]
    if fora:
        raise CitacaoInvalida(f"a resposta citou {fora}, mas só {len(atos)} atos foram enviados")
    return Resposta(texto, citados, msg.usage.input_tokens + msg.usage.output_tokens, msg.stop_reason == "max_tokens")
