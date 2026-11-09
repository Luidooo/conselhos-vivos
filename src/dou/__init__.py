"""Ingestão do Diário Oficial da União, em Python (#51, ADR 0008 a escrever).

Substitui o ingestor em Go (src/ingestor/) fatia por fatia, cada uma provada
contra o Go sobre o mesmo ZIP antes de o Go sair. Subcomandos chegam com as
fatias: fetch-mensal (#53), extract (#54), persist (#55).

Só biblioteca padrão, exceto psycopg para o banco (a mesma versão do lake).
"""

# Código de saída quando o problema está no dado, não na infraestrutura: mês ainda não publicado
# (fetch-mensal) ou entrada do ZIP que não lê como matéria (persist). Repetir não resolve, então a
# orquestração falha sem retry (#83, #84). 1 continua sendo falha de infraestrutura; 2, erro de uso.
SAIDA_DE_DADO = 3
