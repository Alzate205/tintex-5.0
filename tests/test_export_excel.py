import sqlite3

import pytest

import app as appmod


@pytest.fixture
def client(tmp_path, monkeypatch):
    import migraciones
    db = tmp_path / "t.db"
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
    return client.post(
        "/api/login", json={"nombre": "Ana Gómez", "contrasena": "admin123"}
    ).get_json()["token"]


def test_export_excel_devuelve_xlsx(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = client.get("/api/reportes/export", headers=h)
    assert r.status_code == 200
    # un .xlsx es un zip: empieza con 'PK'
    assert r.data[:2] == b"PK"
    assert "spreadsheet" in r.headers.get("Content-Type", "")
