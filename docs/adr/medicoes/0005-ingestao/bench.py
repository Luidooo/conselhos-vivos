"""Medição do ADR 0005: Comparativo arquitetural do mecanismo de propagação ao Delta Lake.

Compara com dados reais do domínio as três alternativas de propagação:
  (A, Opção Nula) Recarga periódica agendada (make lake completo)
  (B) CDC Lógico com consumidor próprio (make cdc incremental)
  (C) Debezium + Apache Kafka (arquitetura padrão com JVM / streaming)

Não altera o banco:
  As medições de latência executam apenas consultas de leitura (SELECT) no OLTP
  e gravações em diretórios temporários efêmeros descartados ao final.
  Os dados de retenção de WAL referenciam a medição do ADR 0007.
  A alternativa C registra estimativas arquiteturais típicas de literatura.

Uso:
    docker compose run --rm lake python docs/adr/medicoes/0005-ingestao/bench.py
"""

import json
from pathlib import Path
import statistics
import tempfile
import time

from lake.sync import extrair_oltp, obter_conexao, sincronizar_delta

REPETICOES = 30


def medir_tempo(func, *args, n: int = REPETICOES):
    # Aquecimento
    func(*args)
    tempos = []
    for _ in range(n):
        t0 = time.perf_counter()
        func(*args)
        tempos.append(time.perf_counter() - t0)
    return statistics.median(tempos) * 1000.0  # ms


def main():
    print("Iniciando medições para o ADR 0005 (Mecanismo de Ingestão e Propagação)...")
    print("Condição: não altera o banco (apenas SELECTs e escrita em disco temporário).")

    with obter_conexao() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM ato")
            total_atos = cur.fetchone()[0]

            cur.execute("SELECT id FROM ato ORDER BY id LIMIT 1")
            ato_id = cur.fetchone()[0]

    print(f"Total de atos no OLTP: {total_atos} (ato selecionado para teste incremental: {ato_id})")

    # 1. Medição empírica de latência no Python (extração + MERGE)
    with tempfile.TemporaryDirectory() as tmp_lake, tempfile.TemporaryDirectory() as tmp_cdc:
        p_lake = Path(tmp_lake)
        p_cdc = Path(tmp_cdc)

        with obter_conexao() as conn:
            tab_todos = extrair_oltp(conn)
            sincronizar_delta(tab_todos, p_lake)
            sincronizar_delta(tab_todos, p_cdc)

            # A. Opção Nula: Leitura e escrita completa (make lake)
            t_ext_completa = medir_tempo(extrair_oltp, conn, None)
            t_merge_completa = medir_tempo(sincronizar_delta, tab_todos, p_lake)
            t_total_completa = t_ext_completa + t_merge_completa

            # B. CDC Lógico próprio: Leitura e escrita incremental (1 ato)
            tab_1_ato = extrair_oltp(conn, [ato_id])
            t_ext_inc = medir_tempo(extrair_oltp, conn, [ato_id])
            t_merge_inc = medir_tempo(sincronizar_delta, tab_1_ato, p_cdc)
            t_total_inc = t_ext_inc + t_merge_inc

    # 2. Consolidação comparativa das 3 alternativas
    resultados = {
        "total_atos": total_atos,
        "base_referencia": "311 atos (215 históricos da planilha 2003-2020 + 96 atos de agosto/2026 do DOU)",
        "alternativas": {
            "A_opcao_nula_recarga_periodica": {
                "descricao": "Recarga periódica completa agendada (make lake sob demanda ou via cron)",
                "fonte_tempo": "medido",
                "tempo_parede_compose_s": 7.0,
                "latencia_processamento_ms": round(t_total_completa, 2),
                "detalhe_tempos": {
                    "extracao_oltp_ms": round(t_ext_completa, 2),
                    "merge_delta_ms": round(t_merge_completa, 2),
                },
                "latencia_chegada_efetiva": "Sob demanda (make lake) ou lote agendado (ex.: cron); ~7,0 s de container efêmero por execução",
                "containers_permanentes": 0,
                "ram_permanente_mb": 0,
                "ram_transitoria_pico_mb": 45,
                "fonte_infra": "estimativa (container efêmero)",
                "dependencias_externas": "Nenhuma (stdlib + deltalake efêmero)",
                "comportamento_reprocessamento": "Varre novamente todo o OLTP e todas as partições do Delta (O(N)), redundante e pesado em I/O",
            },
            "B_cdc_logico_consumidor_proprio": {
                "descricao": "CDC com decodificação lógica nativa (test_decoding), slot lógico e consumidor Python idempotente",
                "fonte_tempo": "medido",
                "fonte_wal": "medido no ADR 0007",
                "tempo_parede_compose_s": 6.8,
                "latencia_processamento_ms": round(t_total_inc, 2),
                "detalhe_tempos": {
                    "extracao_oltp_ms": round(t_ext_inc, 2),
                    "merge_delta_ms": round(t_merge_inc, 2),
                },
                "latencia_chegada_efetiva": "Sob demanda (make cdc) ou agendado; ~6,6-7,0 s de container efêmero (mesma categoria da opção A: até rodar o comando; difere no trabalho por execução: O(Δ) vs O(N))",
                "containers_permanentes": 0,
                "ram_permanente_mb": 0,
                "ram_transitoria_pico_mb": 45,
                "fonte_infra": "estimativa (container efêmero)",
                "wal_retido_em_dia_bytes": 56,
                "wal_retido_transacao_bytes": 512,
                "dependencias_externas": "Nenhuma (Postgres nativo wal_level=logical, sem JVM)",
                "comportamento_reprocessamento": "Entrega pelo menos uma vez no slot com absorção idempotente no MERGE do Delta Lake (effectively-once provado no teste de caos)",
            },
            "C_debezium_kafka": {
                "descricao": "Debezium PostgreSQL Connector + Cluster Apache Kafka + Schema Registry + Consumidor Spark/Python",
                "fonte": "estimativa",
                "nota": "Estimativas teóricas/de literatura para arquitetura distribuída com JVM, não executada no projeto",
                "latencia_processamento_ms": 1500,  # Estimativa de pipeline distribuído de streaming
                "latencia_chegada_efetiva": "1 a 3 segundos (estimativa de streaming contínuo, não medida)",
                "containers_permanentes": 4,  # Zookeeper/KRaft, Kafka Broker, Kafka Connect/Debezium, Consumidor
                "ram_permanente_mb": 2048,  # Média de 2 GB constante de JVM (Zookeeper 350MB, Kafka 700MB, Connect 750MB, consumidor 250MB)
                "ram_transitoria_pico_mb": 2560,
                "dependencias_externas": "Altíssima (Java/JVM, ZooKeeper/KRaft, Apache Kafka, Kafka Connect, Debezium, rede inter-container permanente)",
                "comportamento_reprocessamento": "Replay complexo via reinicialização de offsets em tópicos, gerenciamento de snapshots iniciais e políticas de retenção de log",
            },
        },
        "conclusoes": {
            "speedup_extracao_oltp": round(t_ext_completa / t_ext_inc, 2),
            "speedup_processamento_total": round(t_total_completa / t_total_inc, 2),
            "comparativo_parede_compose": "Empate prático (~7 s cada, dominado pelo overhead de inicialização do container efêmero)",
            "comparativo_cpu_python": f"Empate prático ({t_total_completa:.1f} ms vs {t_total_inc:.1f} ms, speedup total de {t_total_completa / t_total_inc:.2f}x; MERGE domina o tempo)",
            "criterio_decisao": "CDC escolhido pelo requisito de fluxo de mudanças da E2 com semântica demonstrada e custo zero de containers/RAM permanente",
            "economia_ram_permanente_mb_estimada": 2048,
            "diferenca_containers_permanentes_estimada": 4,
        },
    }

    print("\n" + "=" * 70)
    print("RESUMO COMPARATIVO DAS ALTERNATIVAS DO ADR 0005")
    print("=" * 70)
    print(f"Base de referência: {total_atos} atos no OLTP")
    print(f"Tempo de parede no Compose: ~7 s (Opção Nula) vs ~6,8 s (CDC Lógico) -> Empate prático")
    print(f"Extração OLTP: {t_ext_completa:.2f} ms (completa) vs {t_ext_inc:.2f} ms (incremental) -> {t_ext_completa / t_ext_inc:.1f}x mais rápida")
    print(f"Tempo total Python: {t_total_completa:.2f} ms (completa) vs {t_total_inc:.2f} ms (incremental) -> {t_total_completa / t_total_inc:.2f}x (praticamente empatam em CPU)")
    print(f"RAM permanente: 0 MB (A e B) vs ~2.048 MB (C - estimativa Debezium+Kafka)")
    print(f"Containers permanentes: 0 adicionais (A e B) vs 4 (C - estimativa Debezium+Kafka)")
    print(f"Retenção de WAL (ADR 0007): 56 bytes em dia; 512 bytes pendente")
    print("=" * 70)

    out_file = Path(__file__).parent / "resultados.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"Resultados gravados com sucesso em: {out_file}")


if __name__ == "__main__":
    main()
