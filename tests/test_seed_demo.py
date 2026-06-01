import seed_demo
import sostenibilidad as s


def test_seed_genera_sobredosis_y_acumulado(conn):
    seed_demo.sembrar(conn)
    glob = s.compute_acumulado_global(conn)
    assert glob["lotes_analizados"] >= 1
    assert glob["excedente_kg"] > 0
    assert glob["agua_evitable_l"] > 0


def test_seed_es_idempotente(conn):
    seed_demo.sembrar(conn)
    seed_demo.sembrar(conn)  # segunda vez no debe duplicar ni fallar
    glob = s.compute_acumulado_global(conn)
    assert glob["excedente_kg"] > 0
