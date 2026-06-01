# sostenibilidad.py
"""Lógica de cálculo de sostenibilidad para TINTEX 5.0.

Funciones puras que reciben una conexión sqlite3 (sin Flask) para ser
testeables de forma aislada. Densidad ~1 g/ml para líquidos (estimación).
"""

import sqlite3

# Factores de conversión a gramos según abreviatura de unidad
_A_GRAMOS = {"g": 1.0, "kg": 1000.0, "ml": 1.0, "L": 1000.0}


def to_grams(cantidad, abreviatura):
    """Convierte una cantidad a gramos según la abreviatura de unidad.

    Líquidos (ml/L) se tratan con densidad ~1 (estimación documentada).
    """
    if cantidad is None:
        return 0.0
    return float(cantidad) * _A_GRAMOS.get(abreviatura, 1.0)


def _dosis_referencia(conn, nombre_proceso, id_producto):
    row = conn.execute(
        "SELECT dosis_g_kg FROM dosis_referencia WHERE nombre_proceso = ? AND id_producto = ?",
        (nombre_proceso, id_producto),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _factor_ambiental(conn, id_producto):
    row = conn.execute(
        "SELECT agua_l_por_kg, co2_kg_por_kg FROM factores_ambientales WHERE id_producto = ?",
        (id_producto,),
    ).fetchone()
    if row is None:
        return None
    return {"agua_l_por_kg": float(row[0] or 0), "co2_kg_por_kg": float(row[1] or 0)}


def compute_lote_optimizacion(conn, id_lote, umbral_leve=0.10):
    """Compara consumo real (g/kg) vs. dosis de referencia por etapa del lote.

    Devuelve detalle por etapa + totales (excedente kg, agua L, CO2 kg, ahorro).
    Etapas sin peso de tela o sin dosis de referencia se marcan 'sin_referencia'
    y no aportan a los totales (no se inventan números).
    """
    conn.row_factory = sqlite3.Row
    lote = conn.execute(
        "SELECT id_lote, numero_lote, peso_tela_kg FROM lotes WHERE id_lote = ?",
        (id_lote,),
    ).fetchone()
    if lote is None:
        raise ValueError(f"Lote {id_lote} no existe")
    peso = float(lote["peso_tela_kg"] or 0)

    etapas = conn.execute(
        """
        SELECT el.nombre_etapa, ep.id_producto, ep.cantidad_usada,
               p.nombre AS nombre_producto, p.precio, u.abreviatura AS unidad
        FROM etapas_lotes el
        JOIN etapas_productos ep ON ep.id_etapa_lote = el.id_etapa_lote
        JOIN productos p ON p.id_producto = ep.id_producto
        LEFT JOIN unidades_medida u ON u.id_unidad = p.id_unidad
        WHERE el.id_lote = ?
        ORDER BY el.numero_etapa
        """,
        (id_lote,),
    ).fetchall()

    detalle = []
    tot_exc = tot_agua = tot_co2 = tot_ahorro = 0.0
    for e in etapas:
        ref = _dosis_referencia(conn, e["nombre_etapa"], e["id_producto"])
        item = {
            "etapa": e["nombre_etapa"],
            "producto": e["nombre_producto"],
            "dosis_real_g_kg": None,
            "dosis_ref_g_kg": ref,
            "desviacion_pct": None,
            "excedente_kg": 0.0,
            "agua_evitable_l": None,
            "co2_evitable_kg": None,
            "ahorro": 0.0,
            "estado": "sin_referencia",
        }
        if peso > 0 and ref is not None and ref > 0:
            real = to_grams(e["cantidad_usada"], e["unidad"]) / peso
            desv = (real - ref) / ref
            excedente = max(0.0, (real - ref) * peso / 1000.0)
            item["dosis_real_g_kg"] = round(real, 3)
            item["desviacion_pct"] = round(desv * 100, 1)
            item["excedente_kg"] = round(excedente, 4)
            if desv <= 0:
                item["estado"] = "optimo"
            elif desv <= umbral_leve:
                item["estado"] = "leve"
            else:
                item["estado"] = "sobredosis"

            factor = _factor_ambiental(conn, e["id_producto"])
            if factor is not None:
                item["agua_evitable_l"] = round(excedente * factor["agua_l_por_kg"], 2)
                item["co2_evitable_kg"] = round(excedente * factor["co2_kg_por_kg"], 3)
                tot_agua += item["agua_evitable_l"]
                tot_co2 += item["co2_evitable_kg"]
            item["ahorro"] = round(excedente * float(e["precio"] or 0), 2)
            tot_exc += excedente
            tot_ahorro += item["ahorro"]
        detalle.append(item)

    return {
        "id_lote": id_lote,
        "numero_lote": lote["numero_lote"],
        "peso_tela_kg": peso,
        "detalle": detalle,
        "totales": {
            "excedente_kg": round(tot_exc, 4),
            "agua_evitable_l": round(tot_agua, 2),
            "co2_evitable_kg": round(tot_co2, 3),
            "ahorro": round(tot_ahorro, 2),
        },
    }


def compute_acumulado_global(conn):
    """Suma de excedente/agua/CO2/ahorro sobre todos los lotes con peso > 0."""
    conn.row_factory = sqlite3.Row
    ids = [r[0] for r in conn.execute(
        "SELECT id_lote FROM lotes WHERE peso_tela_kg > 0").fetchall()]
    tot = {"excedente_kg": 0.0, "agua_evitable_l": 0.0,
           "co2_evitable_kg": 0.0, "ahorro": 0.0, "lotes_analizados": 0}
    for id_lote in ids:
        r = compute_lote_optimizacion(conn, id_lote)
        t = r["totales"]
        tot["excedente_kg"] += t["excedente_kg"]
        tot["agua_evitable_l"] += t["agua_evitable_l"]
        tot["co2_evitable_kg"] += t["co2_evitable_kg"]
        tot["ahorro"] += t["ahorro"]
        tot["lotes_analizados"] += 1
    for k in ("excedente_kg", "agua_evitable_l", "co2_evitable_kg", "ahorro"):
        tot[k] = round(tot[k], 3)
    return tot


def compute_kpis(conn):
    """KPIs del panel de sostenibilidad."""
    conn.row_factory = sqlite3.Row
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM productos WHERE estado_verificacion = 'Verificado'"
    ).fetchone()["c"]
    peligrosos = conn.execute(
        "SELECT COUNT(*) AS c FROM productos WHERE estado_verificacion = 'Verificado' "
        "AND (es_toxico = 1 OR es_corrosivo = 1 OR es_inflamable = 1)"
    ).fetchone()["c"]
    bajo_stock = conn.execute(
        "SELECT COUNT(*) AS c FROM productos "
        "WHERE estado_verificacion = 'Verificado' AND cantidad < stock_minimo"
    ).fetchone()["c"]
    glob = compute_acumulado_global(conn)
    return {
        "total_productos": total,
        "peligrosos": peligrosos,
        "pct_peligrosos": round(100.0 * peligrosos / total, 1) if total else 0.0,
        "bajo_stock": bajo_stock,
        "agua_evitada_l": glob["agua_evitable_l"],
        "co2_evitado_kg": glob["co2_evitable_kg"],
        "excedente_kg": glob["excedente_kg"],
    }


def predecir_consumo(conn, id_producto, ventana=6, alpha=0.5):
    """Proyección del consumo del próximo periodo con suavizado exponencial.

    Agrupa las salidas por mes y aplica suavizado exponencial simple (Python puro).
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', fecha_movimiento) AS mes, SUM(cantidad) AS total
        FROM movimientos_inventario
        WHERE id_producto = ? AND tipo_movimiento = 'Salida'
        GROUP BY mes ORDER BY mes
        """,
        (id_producto,),
    ).fetchall()
    serie = [float(r["total"] or 0) for r in rows][-ventana:]
    if not serie:
        return {"id_producto": id_producto, "proyeccion": 0.0,
                "confianza": "baja", "historial": 0}
    s_val = serie[0]
    for x in serie[1:]:
        s_val = alpha * x + (1 - alpha) * s_val
    confianza = "alta" if len(serie) >= 4 else ("media" if len(serie) >= 2 else "baja")
    return {"id_producto": id_producto, "proyeccion": round(s_val, 2),
            "confianza": confianza, "historial": len(serie)}
