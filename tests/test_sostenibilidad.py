# tests/test_sostenibilidad.py
import sostenibilidad as s


def test_to_grams_kg():
    assert s.to_grams(2, "kg") == 2000.0


def test_to_grams_litros_densidad_1():
    assert s.to_grams(1, "L") == 1000.0


def test_to_grams_gramos_y_ml():
    assert s.to_grams(50, "g") == 50.0
    assert s.to_grams(50, "ml") == 50.0


def test_to_grams_none_es_cero():
    assert s.to_grams(None, "kg") == 0.0


def test_to_grams_unidad_desconocida_factor_1():
    assert s.to_grams(5, "??") == 5.0


# Añadir al final de tests/test_sostenibilidad.py


def _semilla_lote_sobredosis(conn):
    """Lote #900 (100 kg tela). Etapa 'Teñido' usa 1.24 kg de producto 1.
    Dosis real = 1240 g / 100 kg = 12.4 g/kg. Referencia = 5.0 g/kg => sobredosis.
    Excedente = (12.4 - 5.0) * 100 / 1000 = 0.74 kg.
    """
    conn.execute("INSERT INTO lotes (id_lote, numero_lote, peso_tela_kg, id_usuario) "
                 "VALUES (900, 'LOTE #900', 100, 1)")
    conn.execute("INSERT INTO etapas_lotes (id_etapa_lote, id_lote, numero_etapa, "
                 "nombre_etapa, estado_etapa) VALUES (900, 900, 1, 'Teñido', 'Completado')")
    # producto 1 = Hipoclorito de sodio (seed); su unidad convierte 1.24 -> 1240 g
    conn.execute("INSERT INTO etapas_productos (id_etapa_lote, id_producto, cantidad_usada, "
                 "nombre_producto) VALUES (900, 1, 1.24, 'Hipoclorito de sodio')")
    conn.execute("INSERT INTO dosis_referencia (nombre_proceso, id_producto, dosis_g_kg) "
                 "VALUES ('Teñido', 1, 5.0)")
    conn.execute("INSERT INTO factores_ambientales (id_producto, agua_l_por_kg, co2_kg_por_kg) "
                 "VALUES (1, 300, 7)")
    conn.commit()


def test_optimizacion_detecta_sobredosis(conn):
    _semilla_lote_sobredosis(conn)
    r = s.compute_lote_optimizacion(conn, 900)
    item = r["detalle"][0]
    assert item["estado"] == "sobredosis"
    assert item["dosis_real_g_kg"] == 12.4
    assert item["dosis_ref_g_kg"] == 5.0
    assert item["excedente_kg"] == 0.74


def test_optimizacion_calcula_agua_y_co2(conn):
    _semilla_lote_sobredosis(conn)
    r = s.compute_lote_optimizacion(conn, 900)
    item = r["detalle"][0]
    assert item["agua_evitable_l"] == 222.0   # 0.74 * 300
    assert item["co2_evitable_kg"] == 5.18     # 0.74 * 7
    assert r["totales"]["excedente_kg"] == 0.74


def test_optimizacion_sin_peso_marca_sin_referencia(conn):
    conn.execute("INSERT INTO lotes (id_lote, numero_lote, peso_tela_kg, id_usuario) "
                 "VALUES (901, 'LOTE #901', 0, 1)")
    conn.execute("INSERT INTO etapas_lotes (id_etapa_lote, id_lote, numero_etapa, "
                 "nombre_etapa, estado_etapa) VALUES (901, 901, 1, 'Teñido', 'Completado')")
    conn.execute("INSERT INTO etapas_productos (id_etapa_lote, id_producto, cantidad_usada, "
                 "nombre_producto) VALUES (901, 1, 1.24, 'Hipoclorito de sodio')")
    conn.commit()
    r = s.compute_lote_optimizacion(conn, 901)
    assert r["detalle"][0]["estado"] == "sin_referencia"
    assert r["totales"]["excedente_kg"] == 0.0


def test_optimizacion_lote_inexistente_lanza_error(conn):
    import pytest
    with pytest.raises(ValueError):
        s.compute_lote_optimizacion(conn, 99999)


def test_acumulado_global_suma_lotes(conn):
    _semilla_lote_sobredosis(conn)  # lote 900, excedente 0.74 kg
    glob = s.compute_acumulado_global(conn)
    assert glob["excedente_kg"] == 0.74
    assert glob["agua_evitable_l"] == 222.0
    assert glob["lotes_analizados"] == 1


def test_kpis_porcentaje_peligrosos(conn):
    # El seed marca el producto 1 (Hipoclorito) como peligroso
    k = s.compute_kpis(conn)
    assert k["total_productos"] > 0
    assert 0 <= k["pct_peligrosos"] <= 100


def test_prediccion_sin_historial_es_cero(conn):
    pred = s.predecir_consumo(conn, id_producto=1)
    assert pred["proyeccion"] == 0.0
    assert pred["confianza"] == "baja"


def test_prediccion_con_historial(conn):
    # 3 meses de salidas crecientes para el producto 1
    conn.execute("INSERT INTO movimientos_inventario (id_producto, tipo_movimiento, cantidad, "
                 "fecha_movimiento) VALUES (1,'Salida',10,'2025-01-15 10:00:00')")
    conn.execute("INSERT INTO movimientos_inventario (id_producto, tipo_movimiento, cantidad, "
                 "fecha_movimiento) VALUES (1,'Salida',20,'2025-02-15 10:00:00')")
    conn.execute("INSERT INTO movimientos_inventario (id_producto, tipo_movimiento, cantidad, "
                 "fecha_movimiento) VALUES (1,'Salida',30,'2025-03-15 10:00:00')")
    conn.commit()
    pred = s.predecir_consumo(conn, id_producto=1)
    # Suavizado exponencial alpha=0.5 sobre [10,20,30] => 22.5
    assert pred["proyeccion"] == 22.5
    assert pred["historial"] == 3


def test_graficas_estructura_y_alertas(conn):
    import seed_demo
    seed_demo.sembrar(conn)
    g = s.compute_graficas(conn)
    pv = g["peligrosos_vs_seguros"]
    assert pv["seguros"] + pv["corrosivos"] + pv["toxicos_inflamables"] >= 1
    assert isinstance(g["top_quimicos"], list) and len(g["top_quimicos"]) >= 1
    assert isinstance(g["consumo_por_lote"], list) and len(g["consumo_por_lote"]) >= 1
    # con seed_demo hay sobredosis -> al menos una alerta de ese tipo
    assert any(a["tipo"] == "sobredosis" for a in g["alertas"])
