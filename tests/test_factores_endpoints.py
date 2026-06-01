import json
import sqlite3

import pytest

import app as appmod


@pytest.fixture
def client(tmp_path, monkeypatch):
    # BD temporal aislada con schema + migraciones
    import migraciones
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    with open("create_database.sql", encoding="utf-8") as f:
        conn.executescript(f.read())
    migraciones.aplicar_migraciones(conn)
    conn.commit()
    conn.close()
    monkeypatch.setattr(appmod, "DATABASE_PATH", str(db))
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()


def _token(client):
    r = client.post("/api/login", json={"nombre": "Ana Gómez", "contrasena": "admin123"})
    return r.get_json()["token"]


def test_get_factores_vacio(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = client.get("/api/factores_ambientales", headers=h)
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_post_y_get_factor(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    payload = {"id_producto": 1, "agua_l_por_kg": 300, "co2_kg_por_kg": 7,
               "eco_score": "B", "fuente": "Doe 2021", "es_estimacion": 1}
    r = client.post("/api/factores_ambientales", json=payload, headers=h)
    assert r.status_code == 201
    data = client.get("/api/factores_ambientales", headers=h).get_json()
    assert any(f["id_producto"] == 1 and f["agua_l_por_kg"] == 300 for f in data)


def test_put_actualiza_factor(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    client.post("/api/factores_ambientales",
                json={"id_producto": 1, "agua_l_por_kg": 300, "co2_kg_por_kg": 7}, headers=h)
    r = client.put("/api/factores_ambientales/1",
                   json={"agua_l_por_kg": 250, "co2_kg_por_kg": 5}, headers=h)
    assert r.status_code == 200
    data = client.get("/api/factores_ambientales", headers=h).get_json()
    f = next(f for f in data if f["id_producto"] == 1)
    assert f["agua_l_por_kg"] == 250


def test_factores_requiere_token(client):
    assert client.get("/api/factores_ambientales").status_code == 401
