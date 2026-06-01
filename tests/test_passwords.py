from werkzeug.security import check_password_hash

import migraciones


def test_migracion_hashea_passwords(conn):
    # tras migraciones, las contraseñas del seed ya no son texto plano
    fila = conn.execute("SELECT contrasena FROM usuarios WHERE nombre='Ana Gómez'").fetchone()
    assert fila[0] != "admin123"
    assert check_password_hash(fila[0], "admin123")


def test_migracion_passwords_idempotente(conn):
    migraciones.aplicar_migraciones(conn)  # segunda pasada no re-hashea ni rompe
    fila = conn.execute("SELECT contrasena FROM usuarios WHERE nombre='Ana Gómez'").fetchone()
    assert check_password_hash(fila[0], "admin123")
