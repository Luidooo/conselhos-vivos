# Uso de IA neste projeto

Conforme a Política de Uso de IA da disciplina.

## Como usamos

| Onde | Ferramenta | O que foi feito |
|---|---|---|
| Levantamento do domínio | Claude Code | Transcrição do áudio de briefing, leitura das planilhas, pesquisa da estrutura do DOU/INLABS |
| Documentação | Claude Code | Redação do briefing da squad e deste README |
| Issue #1 — planejamento (26/09) | Claude Code | Leitura do plano de ensino e do checklist da E1, levantamento das tags de imagem no Docker Hub, detecção do conflito de porta 5432 na máquina local, e redação do plano de implementação da issue |
| Issue #1 — implementação (26/09) | Claude Code | Geração do `docker-compose.yml`, do teste de fumaça `tests/infra/test_compose.sh`, do `Makefile` (`make setup`) e da seção "Como rodar" do README. Revisado e executado pela Luiza, incluindo teste em clone limpo |
| Issue #1 — revisão pós-merge (26/09) | Claude Code | Revisão de código do PR #7: achou as portas publicadas em `0.0.0.0` (pgAdmin sem login exposto na rede), o `source .env` frágil no teste e o `servers.json` que não acompanha o `.env`. Correções, teste de bind e `make pgadmin-reset` gerados com IA; exposição e correção confirmadas com `curl` no IP da rede |

## Princípios da squad

- Toda saída de IA é **verificada em fonte primária** antes de entrar no repositório.
- Decisões de arquitetura são da equipe. IA ajuda a levantar alternativas; quem escolhe e assina o ADR somos nós.
- Código gerado com auxílio de IA passa pela mesma revisão que qualquer outro.

## Registro

Atualizar esta tabela a cada entrega.
