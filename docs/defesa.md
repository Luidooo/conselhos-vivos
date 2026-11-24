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
3. Perguntar: uma pergunta com resposta citando o ato, e uma sem resposta nos atos. Pede a `ANTHROPIC_API_KEY` no `.env` e rede. **A página ainda não rodou com a API de verdade: se o ensaio não a exercitar, este passo sai,** ou fica só a busca, que funciona sem chave.
4. http://localhost:5173/conselhos-vivos/linhagem: "Percorrer a linhagem".
5. `bash tests/db/test_acesso.sh`: os casos saem como `ok`, e a recusa em si não aparece. Para a banca ver o `permission denied`, rode também o comando abaixo, que tenta ler o e-mail como o papel do app:

   ```bash
   docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SET ROLE app_curadoria; SELECT email FROM revisor"'
   ```

## Antes de começar

- O ambiente da demonstração é um clone limpo do `main`, à parte do banco de trabalho, com julho a setembro: o mesmo recorte das provas. A sequência é a da página da entrega da E4: `make setup`, `make test-orquestracao` (gera o manifesto do dbt que o backfill pede), `make demo-backfill DE=2026-07 ATE=2026-09`, `make gold`, `make metricas`, `make alertas`, `make painel`. O banco de trabalho já tem outubro na silver e na gold, e o painel dele mostra outros números.
- As migrações em dia. O `make setup` já as aplica; num banco que já existia, rode `make migrate`. Sem a 008, a página Perguntar e os casos do `app_perguntas` no passo 5 falham.
- As portas livres. O banco (`POSTGRES_PORT` no `.env`, 5432 por padrão) e o painel (8501) do clone disputam as do ambiente de trabalho: pare um deles ou mude a porta.
- Pelo menos um alerta aberto, para o passo 2. Depois de um backfill, a página Revisar mostra também os alertas dos meses anteriores (24 no clone limpo, com julho a setembro). Um alerta marcado no ensaio não volta a abrir sozinho.
- O site local no ar (`make docs`), para o passo 4.

## Plano B

Se a rede ou o Docker falharem: os prints em `docs/adr/medicoes/0011-disponibilizacao/` (`painel-metricas.png`, `revisar.png`, `tipologia-por-ano.png`, `grafo-dagster.jpg`), o de `docs/adr/medicoes/0012-rag/` (`perguntar-sem-chave.png`) e o site publicado.
