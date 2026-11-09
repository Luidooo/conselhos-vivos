"""Ingestão do Diário Oficial da União, em Python (#51, ADR 0008).

Subcomandos: fetch-mensal (#53), extract (#54), persist (#55).

Só biblioteca padrão, exceto psycopg para o banco (a mesma versão do lake).
"""

# Código de saída quando o problema está no dado, não na infraestrutura: mês ainda não publicado
# (fetch-mensal) ou entrada do ZIP que não lê como matéria (persist). Repetir não resolve, então a
# orquestração falha sem retry (#83, #84). 1 continua sendo falha de infraestrutura; 2, erro de uso.
SAIDA_DE_DADO = 3
