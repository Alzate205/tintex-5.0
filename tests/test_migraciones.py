# tests/test_migraciones.py
import sqlite3

import migraciones


def _columnas(conn, tabla):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()]


def _tablas(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]


def test_agrega_peso_tela_kg_a_lotes(conn):
    assert "peso_tela_kg" in _columnas(conn, "lotes")


def test_crea_tabla_factores_ambientales(conn):
    assert "factores_ambientales" in _tablas(conn)
    cols = _columnas(conn, "factores_ambientales")
    for c in ("id_producto", "agua_l_por_kg", "co2_kg_por_kg",
              "carga_efluente_gdqo_por_kg", "eco_score", "fuente", "es_estimacion"):
        assert c in cols


def test_crea_tabla_dosis_referencia(conn):
    assert "dosis_referencia" in _tablas(conn)
    cols = _columnas(conn, "dosis_referencia")
    for c in ("nombre_proceso", "id_producto", "dosis_g_kg"):
        assert c in cols


def test_migracion_es_idempotente(conn):
    # Aplicarla de nuevo no debe lanzar error
    migraciones.aplicar_migraciones(conn)
    assert "peso_tela_kg" in _columnas(conn, "lotes")
