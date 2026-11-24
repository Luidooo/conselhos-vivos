# Defesa da E4: roteiro

Vinte minutos, divididos entre as duas metades da banca: a gestão, que quer a resposta, e a técnica, que quer saber como ela foi construída.

| Min | Quem | Para quem | O quê |
|---|---|---|---|
| 0–3 | | gestão | A pergunta: quais conselhos de participação social ainda funcionam? Por que ninguém sabe hoje. |
| 3–7 | | gestão | A resposta no painel: ativos, sem ato, citados por outros órgãos, e os limites do que o DOU mostra. |
| 7–10 | | gestão e técnica | A página Revisar: um alerta, quem o trata, e por que ele não vira uma decisão automática. |
| 10–15 | | técnica | O caminho do dado na linhagem interativa, do ZIP ao alerta, com o ADR de cada trecho. |
| 15–18 | | técnica | Governança: a métrica com uma definição só, o papel que não vê o e-mail, a LGPD. |
| 18–20 | | as duas | O que faríamos diferente (retrospectiva) e o que vem depois (a classificação automática, P4). |

A coluna "Quem" a squad preenche no ensaio.

## Demonstração, na ordem

1. `make painel` → http://127.0.0.1:8501: os três números, a tabela, o gráfico das métricas.
2. Revisar: marcar um alerta como tratado ao vivo.
3. Perguntar: uma pergunta com resposta citando o ato, e uma sem resposta nos atos. **Só se a página Perguntar (#109) entrar até a defesa;** senão, este passo sai.
4. http://localhost:5173/conselhos-vivos/linhagem: "Percorrer a linhagem".
5. `bash tests/db/test_acesso.sh`: o `permission denied` do e-mail.

## Antes de começar

- O banco de trabalho no ar, com julho a setembro carregados, e a gold feita: `make up`, `make gold`, `make metricas`, `make alertas`.
- Pelo menos um alerta aberto, para o passo 2. Um alerta marcado no ensaio não volta a abrir sozinho.
- O site local no ar (`make docs`), para o passo 4.

## Plano B

Se a rede ou o Docker falharem: os prints em `docs/adr/medicoes/0011-disponibilizacao/` (`painel-metricas.png`, `revisar.png`, `grafo-dagster.jpg`) e o site publicado.
