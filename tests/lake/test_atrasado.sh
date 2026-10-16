#!/usr/bin/env bash
# Dado atrasado de ponta a ponta (#31): um ato publicado em 2024 chega hoje, entra
# no OLTP pelo persist e cai na partição ano=2024 do Delta pelo make lake, sem
# mexer nas outras partições. Reexecutar não duplica.
#
# Usa um Delta temporário (não toca o do dia a dia). O ato é de órgão conhecido
# (CONAMA, sql/004) e não ganha classificação, então pode ser apagado no fim: ato
# não é insert-only; só classificacao é.
# Uso: bash tests/lake/test_atrasado.sh   (a partir de qualquer diretório)
set -euo pipefail
cd "$(dirname "$0")/../.."

ID_DOU=900031024   # fora da faixa do DOU, como a amostra construída
TMP_NAME="_test_atrasado_$$"
TMP_HOST_DIR="data/silver/$TMP_NAME"
TMP_CONTAINER_DIR="/data/silver/$TMP_NAME"
ZIP_HOST="data/bronze/_test_atrasado_$$.zip"
ZIP_CONTAINER="/data/bronze/_test_atrasado_$$.zip"

psql_db() {
  docker compose exec -T db sh -c \
    'psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q -tA -c "$1"' sh "$1"
}
duck() {
  docker run --rm -v "$PWD/data/silver:/data/silver:ro" --entrypoint duckdb duckdb/duckdb:1.5.6 -csv -noheader -c "
INSTALL delta; LOAD delta; $1" | tr -d '[:space:]'
}
limpa() {
  rm -rf "$TMP_HOST_DIR" "$ZIP_HOST"
  psql_db "DELETE FROM ato WHERE origem = 'DOU' AND id_dou = '$ID_DOU'" >/dev/null 2>&1 || true
}
trap limpa EXIT INT TERM
limpa

echo "==> [test_atrasado] 1. Delta de referência (sem o ato atrasado)"
DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR" >/dev/null 2>&1
antes_total=$(duck "SELECT count(*) FROM delta_scan('$TMP_CONTAINER_DIR')")
antes_2024=$(duck "SELECT count(*) FROM delta_scan('$TMP_CONTAINER_DIR') WHERE ano = 2024")
antes_outros=$(duck "SELECT string_agg(ano || ':' || n, ',' ORDER BY ano) FROM (SELECT ano, count(*) n FROM delta_scan('$TMP_CONTAINER_DIR') WHERE ano <> 2024 GROUP BY ano)")
echo "    total=$antes_total, ano=2024: $antes_2024"

echo "==> [test_atrasado] 2. Um ato publicado em 15/03/2024 chega hoje, num ZIP de edição corrente"
# A amostra construída (CONAMA) com outro id e a data antiga; o ZIP leva o nome de hoje,
# como o fetch deixaria: o que vale é o pubDate da matéria, não o nome do arquivo.
sed -e "s/id=\"900000001\"/id=\"$ID_DOU\"/" -e 's|pubDate="02/10/2026"|pubDate="15/03/2024"|' \
  tests/dou/amostras/conselho-construido.xml > "data/bronze/_atrasada_$$.xml"
( cd data/bronze && python3 -c "
import zipfile, sys
with zipfile.ZipFile('_test_atrasado_$$.zip', 'w') as z:
    z.write('_atrasada_$$.xml', 'conselho-atrasada.xml')
" ) && rm -f "data/bronze/_atrasada_$$.xml"

saida=$(docker compose --progress quiet run --rm -T dou persist "$ZIP_CONTAINER" 2>&1)
echo "$saida" | grep -q "gravadas=1" || { echo "FALHOU: o persist não gravou o ato atrasado:"; echo "$saida"; exit 1; }
data_oltp=$(psql_db "SELECT data_publicacao FROM ato WHERE origem = 'DOU' AND id_dou = '$ID_DOU'")
[ "$data_oltp" = "2024-03-15" ] || { echo "FALHOU: no OLTP a data é '$data_oltp', esperava 2024-03-15"; exit 1; }
echo "    no OLTP: data_publicacao=$data_oltp (a data de publicação, não a de chegada)"

echo "==> [test_atrasado] 3. make lake: o ato cai na partição ano=2024"
saida=$(DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR" 2>&1)
echo "$saida" | grep -q "inseridas=1" || { echo "FALHOU: o lake não inseriu exatamente 1:"; echo "$saida"; exit 1; }
echo "$saida" | grep -q "atualizadas=0" || { echo "FALHOU: o lake atualizou linhas que não mudaram:"; echo "$saida"; exit 1; }
depois_2024=$(duck "SELECT count(*) FROM delta_scan('$TMP_CONTAINER_DIR') WHERE ano = 2024")
ano_do_ato=$(duck "SELECT ano FROM delta_scan('$TMP_CONTAINER_DIR') WHERE id_origem = '$ID_DOU'")
depois_outros=$(duck "SELECT string_agg(ano || ':' || n, ',' ORDER BY ano) FROM (SELECT ano, count(*) n FROM delta_scan('$TMP_CONTAINER_DIR') WHERE ano <> 2024 GROUP BY ano)")
[ "$ano_do_ato" = "2024" ] || { echo "FALHOU: o ato está em ano=$ano_do_ato, esperava 2024"; exit 1; }
[ "$depois_2024" = "$((antes_2024 + 1))" ] || { echo "FALHOU: ano=2024 tinha $antes_2024 e ficou com $depois_2024"; exit 1; }
[ "$depois_outros" = "$antes_outros" ] || { echo "FALHOU: outras partições mudaram: antes [$antes_outros] depois [$depois_outros]"; exit 1; }
[ -d "$TMP_HOST_DIR/ano=2024" ] || { echo "FALHOU: o diretório ano=2024 não existe no Delta"; exit 1; }
echo "    ano=2024: $antes_2024 -> $depois_2024; demais partições intactas"

echo "==> [test_atrasado] 4. De novo: nada duplica"
saida=$(DOCKER_UID=$(id -u) DOCKER_GID=$(id -g) docker compose --progress quiet run --rm -T lake "$TMP_CONTAINER_DIR" 2>&1)
echo "$saida" | grep -q "inseridas=0 atualizadas=0" || { echo "FALHOU: a reexecução escreveu:"; echo "$saida"; exit 1; }
total=$(duck "SELECT count(*) FROM delta_scan('$TMP_CONTAINER_DIR')")
[ "$total" = "$((antes_total + 1))" ] || { echo "FALHOU: total $total, esperava $((antes_total + 1))"; exit 1; }

echo "==> [test_atrasado] OK: ato de 2024 chegado hoje está no OLTP e em ano=2024 no Delta; reexecução não duplica"
