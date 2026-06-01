# migraciones.py
"""Migraciones idempotentes de la BD de TINTEX.

Se pueden aplicar múltiples veces sin error y sin alterar tablas existentes.
"""


def _columna_existe(conn, tabla, columna):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()]
    return columna in cols


def aplicar_migraciones(conn):
    """Aplica todas las migraciones aditivas. Idempotente."""
    # 1) peso de tela por lote (base de normalización g/kg)
    if not _columna_existe(conn, "lotes", "peso_tela_kg"):
        conn.execute("ALTER TABLE lotes ADD COLUMN peso_tela_kg REAL DEFAULT 0")

    # 2) coeficientes ambientales configurables por producto
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factores_ambientales (
            id_factor INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL UNIQUE,
            agua_l_por_kg REAL DEFAULT 0,
            co2_kg_por_kg REAL DEFAULT 0,
            carga_efluente_gdqo_por_kg REAL DEFAULT 0,
            eco_score TEXT DEFAULT 'C',
            fuente TEXT,
            es_estimacion INTEGER DEFAULT 1,
            FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE
        )
    """)

    # 3) dosis óptima de referencia por proceso + producto (g de químico por kg de tela)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dosis_referencia (
            id_dosis INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_proceso TEXT NOT NULL,
            id_producto INTEGER NOT NULL,
            dosis_g_kg REAL NOT NULL,
            UNIQUE (nombre_proceso, id_producto),
            FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE
        )
    """)

    # 4) hashear contraseñas en texto plano (idempotente: salta las ya hasheadas)
    from werkzeug.security import generate_password_hash
    for uid, pwd in conn.execute("SELECT id_usuario, contrasena FROM usuarios").fetchall():
        if pwd and not str(pwd).startswith(("pbkdf2:", "scrypt:")):
            conn.execute("UPDATE usuarios SET contrasena = ? WHERE id_usuario = ?",
                         (generate_password_hash(pwd), uid))

    conn.commit()
