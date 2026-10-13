"""Medição do ADR 0007: CDC incremental vs recarga analítica completa (opção nula) e retenção de WAL.

Executa benchmark comparativo real com os dados do banco:
1. Tempo de execução no Python (CPU e I/O de banco):
   - make lake completo (todos os atos)
   - make cdc incremental (1 ato com reclassificação)
2. Retenção de WAL no slot de replicação lógica:
   - Slot consumido (em dia)
   - Transação única de reclassificação retida
   - Slot pós-consumo

Uso:
    docker compose run --rm lake python docs/adr/medicoes/0007-cdc/bench.py
"""

import json
from pathlib import Path
import statistics
import tempfile
import time

from lake.cdc import garantir_slot, remover_slot
from lake.sync import extrair_oltp, obter_conexao, sincronizar_delta

REPETICOES = 30
SLOT_BENCH = "bench_cdc_slot"


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
    print("Iniciando benchmark do ADR 0007 (CDC vs Opção Nula)...")
    with obter_conexao() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM ato")
            total_atos = cur.fetchone()[0]

            cur.execute("SELECT id FROM ato ORDER BY id LIMIT 1")
            ato_id = cur.fetchone()[0]

            # Tipologia vigente original da pesquisadora para restauração
            cur.execute(
                """
                SELECT COALESCE(
                    (SELECT cv.tipologia_sigla
                     FROM classificacao_vigente cv
                     JOIN revisor r ON r.id = cv.revisor_id
                     WHERE cv.ato_id = %s
                     ORDER BY (r.tipo = 'HUMANO') DESC, cv.criado_em DESC LIMIT 1),
                    'AUTO'
                )
                """,
                (ato_id,),
            )
            tipologia_original = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO revisor (nome, tipo, email)
                VALUES ('Revisor Bench CDC', 'HUMANO', 'bench-cdc@sistema.local')
                ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome
                RETURNING id
                """
            )
            revisor_bench = cur.fetchone()[0]

    print(f"Total de atos no banco: {total_atos} (ato selecionado para teste incremental: {ato_id})")

    resultados = {
        "total_atos": total_atos,
        "tempos_python_ms": {},
        "wal_retido_bytes": {},
    }

    # -------------------------------------------------------------
    # 1. Medição de Tempos: Carga Completa (Lake) vs Incremental (CDC)
    # -------------------------------------------------------------
    print("\n==> 1. Medindo tempos no Python (extração OLTP + MERGE Delta)...")
    with tempfile.TemporaryDirectory() as tmp_lake, tempfile.TemporaryDirectory() as tmp_cdc:
        p_lake = Path(tmp_lake)
        p_cdc = Path(tmp_cdc)

        with obter_conexao() as conn:
            # Popula tabelas Delta iniciais
            tab_todos = extrair_oltp(conn)
            sincronizar_delta(tab_todos, p_lake)
            sincronizar_delta(tab_todos, p_cdc)

            # A. Carga Completa (make lake)
            t_ext_completa = medir_tempo(extrair_oltp, conn, None)
            t_merge_completa = medir_tempo(sincronizar_delta, tab_todos, p_lake)
            t_total_completa = t_ext_completa + t_merge_completa

            # B. Incremental (make cdc)
            tab_1_ato = extrair_oltp(conn, [ato_id])
            t_ext_inc = medir_tempo(extrair_oltp, conn, [ato_id])
            t_merge_inc = medir_tempo(sincronizar_delta, tab_1_ato, p_cdc)
            t_total_inc = t_ext_inc + t_merge_inc

        resultados["tempos_python_ms"] = {
            "make_lake_completo": {
                "extracao_ms": round(t_ext_completa, 2),
                "merge_delta_ms": round(t_merge_completa, 2),
                "total_ms": round(t_total_completa, 2),
            },
            "make_cdc_incremental": {
                "extracao_ms": round(t_ext_inc, 2),
                "merge_delta_ms": round(t_merge_inc, 2),
                "total_ms": round(t_total_inc, 2),
            },
            "speedup_cpu": round(t_total_completa / t_total_inc, 2),
        }

        print(f"  make lake completo ({total_atos} atos): extração={t_ext_completa:.2f} ms | merge={t_merge_completa:.2f} ms | total={t_total_completa:.2f} ms")
        print(f"  make cdc incremental (1 ato):  extração={t_ext_inc:.2f} ms | merge={t_merge_inc:.2f} ms | total={t_total_inc:.2f} ms")
        print(f"  Vantagem em tempo de processamento: {t_total_completa / t_total_inc:.2f}x mais rápido")

    # -------------------------------------------------------------
    # 2. Medição de Retenção de WAL no Slot Lógico
    # -------------------------------------------------------------
    print("\n==> 2. Medindo retenção de WAL no PostgreSQL...")
    with obter_conexao() as conn:
        remover_slot(conn, SLOT_BENCH)
        garantir_slot(conn, SLOT_BENCH)

        # Zera pendências anteriores
        conn.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s, NULL, NULL)", (SLOT_BENCH,))

        # Medição A: Slot em dia (consumido)
        wal_em_dia = conn.execute(
            "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) FROM pg_replication_slots WHERE slot_name = %s",
            (SLOT_BENCH,),
        ).fetchone()[0]

        # Gera 1 evento de reclassificação
        nova_tipologia = "IP" if tipologia_original != "IP" else "GEST"
        conn.execute(
            "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (%s, %s, %s)",
            (ato_id, nova_tipologia, revisor_bench),
        )

        # Medição B: WAL retido com a transação pendente
        wal_pendente = conn.execute(
            "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) FROM pg_replication_slots WHERE slot_name = %s",
            (SLOT_BENCH,),
        ).fetchone()[0]

        # Restaura a tipologia original com novo insert (insert-only, sem contaminar)
        conn.execute(
            "INSERT INTO classificacao (ato_id, tipologia_sigla, revisor_id) VALUES (%s, %s, %s)",
            (ato_id, tipologia_original, revisor_bench),
        )

        # Consome tudo e remove o slot
        conn.execute("SELECT count(*) FROM pg_logical_slot_get_changes(%s, NULL, NULL)", (SLOT_BENCH,))
        remover_slot(conn, SLOT_BENCH)

        resultados["wal_retido_bytes"] = {
            "slot_consumido_bytes": int(wal_em_dia),
            "transacao_reclassificacao_bytes": int(wal_pendente),
            "transacao_reclassificacao_kb": round(float(wal_pendente) / 1024, 1),
        }

        print(f"  Slot em dia / consumido: {wal_em_dia} bytes")
        print(f"  Transação de reclassificação pendente: {wal_pendente} bytes (~{wal_pendente/1024:.1f} KB)")

    out_json = Path(__file__).parent / "resultados.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nResultados gravados em {out_json}")


if __name__ == "__main__":
    main()
