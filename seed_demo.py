# seed_demo.py
"""Siembra datos de demo idempotentes para que las pantallas muestren números reales.

Asigna peso de tela a los lotes, define dosis de referencia (g/kg) por
proceso+producto y coeficientes ambientales con fuente citada.
"""

# (nombre_proceso, id_producto, dosis_g_kg)  — nombre_proceso == etapas_lotes.nombre_etapa
_DOSIS = [
    ("Teñido", 1, 5.0),
    ("Teñido", 2, 3.0),
    ("Lavado enzimático", 4, 4.5),
    ("Pre-lavado", 3, 1.0),
    ("Aplicación de suavizante", 5, 8.0),
]

# (id_producto, agua_l_por_kg, co2_kg_por_kg, carga_efluente_gdqo_por_kg, eco_score, fuente)
_FACTORES = [
    (1, 300, 7.0, 120, "C", "Estimación literatura textil (ej. Kant 2012)"),
    (2, 90, 2.0, 40, "B", "Estimación literatura textil"),
    (3, 60, 1.5, 30, "B", "Estimación literatura textil"),
    (4, 50, 1.2, 25, "A", "Estimación literatura textil"),
    (5, 80, 1.8, 35, "B", "Estimación literatura textil"),
]


def sembrar(conn):
    """Aplica los datos de demo de forma idempotente."""
    # Peso de tela para los lotes existentes
    conn.execute("UPDATE lotes SET peso_tela_kg = 420 WHERE id_lote = 1")
    conn.execute("UPDATE lotes SET peso_tela_kg = 380 WHERE id_lote = 2")

    for nombre_proceso, id_producto, dosis in _DOSIS:
        conn.execute(
            "INSERT INTO dosis_referencia (nombre_proceso, id_producto, dosis_g_kg) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(nombre_proceso, id_producto) DO UPDATE SET dosis_g_kg = excluded.dosis_g_kg",
            (nombre_proceso, id_producto, dosis),
        )

    for id_producto, agua, co2, dqo, score, fuente in _FACTORES:
        conn.execute(
            "INSERT INTO factores_ambientales "
            "(id_producto, agua_l_por_kg, co2_kg_por_kg, carga_efluente_gdqo_por_kg, eco_score, fuente, es_estimacion) "
            "VALUES (?, ?, ?, ?, ?, ?, 1) "
            "ON CONFLICT(id_producto) DO UPDATE SET "
            "agua_l_por_kg=excluded.agua_l_por_kg, co2_kg_por_kg=excluded.co2_kg_por_kg, "
            "carga_efluente_gdqo_por_kg=excluded.carga_efluente_gdqo_por_kg, "
            "eco_score=excluded.eco_score, fuente=excluded.fuente",
            (id_producto, agua, co2, dqo, score, fuente),
        )
    conn.commit()


if __name__ == "__main__":
    import sqlite3
    import migraciones
    c = sqlite3.connect("gyh_local.db")
    migraciones.aplicar_migraciones(c)
    sembrar(c)
    c.close()
    print("Datos de demo sembrados en gyh_local.db")
