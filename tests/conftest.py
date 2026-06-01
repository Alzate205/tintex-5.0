import os
import sqlite3
import sys

import pytest

# Permite importar migraciones.py y sostenibilidad.py desde la raíz del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import migraciones  # noqa: E402

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "create_database.sql")


@pytest.fixture
def conn():
    """Conexión SQLite en memoria con el schema base + migraciones aplicadas."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        c.executescript(f.read())
    migraciones.aplicar_migraciones(c)
    c.commit()
    yield c
    c.close()
