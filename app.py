import os
import sys
import shutil  # Añadir shutil para copiar archivos
from flask import Flask, send_from_directory, g, request, jsonify, send_file
from flask_cors import CORS
import xlsxwriter
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
from io import BytesIO
import re
import sqlite3
import migraciones
import sostenibilidad

# Inicialización de la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'gyhdenimtex'  # Clave estática como lo pediste
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Función para obtener la ruta correcta (empaquetada o no)
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # Si está empaquetado con PyInstaller, usa la carpeta temporal _MEIPASS
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Configuración de la base de datos LOCAL SQLite
# Directorio donde se almacenará la base de datos persistente (junto al ejecutable)
if getattr(sys, 'frozen', False):
    # Si está empaquetado, usa el directorio del ejecutable
    PERSISTENT_DIR = os.path.dirname(sys.executable)
else:
    # Si no está empaquetado, usa el directorio del script
    PERSISTENT_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(PERSISTENT_DIR, "gyh_local.db")

# Copiar la base de datos desde _MEIPASS a PERSISTENT_DIR si no existe
if getattr(sys, 'frozen', False):
    source_db_path = resource_path("gyh_local.db")
    if not os.path.exists(DATABASE_PATH):
        try:
            print(f"Copiando base de datos desde {source_db_path} a {DATABASE_PATH}")
            shutil.copy2(source_db_path, DATABASE_PATH)
        except Exception as e:
            print(f"Error al copiar la base de datos: {e}")
            # Si falla la copia, el programa seguirá intentando usar DATABASE_PATH,
            # pero SQLite creará una nueva base de datos vacía si no existe.

# Aplicar migraciones idempotentes al arrancar
try:
    _mig_conn = sqlite3.connect(DATABASE_PATH)
    migraciones.aplicar_migraciones(_mig_conn)
    _mig_conn.close()
except Exception as e:
    print(f"Error al aplicar migraciones: {e}")

# Funciones de conexión a la base de datos
def get_db_connection():
    if 'db' not in g:
        if not os.path.exists(DATABASE_PATH):
            print(f"Base de datos no encontrada en {DATABASE_PATH}. Esto no debería suceder después de la copia.")
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row  # Para devolver filas como diccionarios
    return g.db

@app.teardown_appcontext
def close_db_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Ruta para servir el archivo index.html
@app.route('/')
def serve_index():
    return send_from_directory(resource_path('.'), 'index.html')

# Ruta para servir otros archivos estáticos (HTML, CSS, JS, imágenes, etc.)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(resource_path('.'), path)

# Decorador para requerir token en las rutas protegidas
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                print("Formato de Authorization inválido")
                return jsonify({'error': 'Formato de Authorization inválido, se esperaba "Bearer <token>"'}), 401
        
        if not token:
            print("Token faltante")
            return jsonify({'error': 'Token faltante'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data.get('user')
            if not current_user:
                print("Estructura de token inválida: falta el campo 'user'")
                return jsonify({'error': 'Estructura de token inválida: falta el campo "user"'}), 401
        except jwt.ExpiredSignatureError:
            print("Token expirado")
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            print("Token inválido")
            return jsonify({'error': 'Token inválido'}), 401
        except Exception as e:
            print(f"Error al validar el token: {str(e)}")
            return jsonify({'error': f'Error al validar el token: {str(e)}'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated
# Ruta de autenticación
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()
    nombre = data.get('nombre')
    contrasena = data.get('contrasena')

    if not nombre or not contrasena:
        return jsonify({'error': 'Por favor, ingresa tu nombre de usuario y contraseña.'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id_usuario, nombre, contrasena, rol, email FROM usuarios WHERE nombre = ?', (nombre,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['contrasena'], contrasena):
            user_dict = {
                'id': user['id_usuario'],
                'nombre': user['nombre'],
                'rol': user['rol'],
                'email': user['email']
            }
            token = jwt.encode({
                'user': user_dict,
                'exp': datetime.utcnow() + timedelta(days=365)
            }, app.config['SECRET_KEY'], algorithm='HS256')
            return jsonify({'user': user_dict, 'token': token})
        else:
            print(f"Credenciales inválidas para usuario: {nombre}")
            return jsonify({'error': 'El nombre de usuario o la contraseña son incorrectos. Por favor, verifica tus datos.'}), 401
    except Exception as e:
        print(f"Error en la base de datos: {e}")
        return jsonify({'error': 'Hubo un problema al intentar iniciar sesión. Intenta de nuevo más tarde.'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/inventario', methods=['GET'])
@token_required
def get_inventario(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_producto, producto, cantidad, unit_id, unidad, type_id, tipo AS type, 
                   precio, stock_minimo, stock_maximo, id_proveedor, proveedor,
                   estado_verificacion, lote, es_toxico, es_corrosivo, es_inflamable
            FROM vista_inventario
            ORDER BY id_producto
        """)
        productos = cursor.fetchall()
        return jsonify([{
            'id': row['id_producto'],
            'product': row['producto'],
            'quantity': row['cantidad'],
            'unit_id': row['unit_id'],
            'unit': row['unidad'],
            'type_id': row['type_id'],
            'type': row['type'],
            'precio': row['precio'],
            'stock_minimo': row['stock_minimo'],
            'stock_maximo': row['stock_maximo'],
            'id_proveedor': row['id_proveedor'],
            'proveedor': row['proveedor'],
            'estado_verificacion': row['estado_verificacion'],
            'lote': row['lote'],
            'es_toxico': bool(row['es_toxico']),
            'es_corrosivo': bool(row['es_corrosivo']),
            'es_inflamable': bool(row['es_inflamable'])
        } for row in productos])
    except Exception as e:
        print(f"Error al cargar inventario: {e}")
        return jsonify({'error': 'No se pudo cargar el inventario. Intenta de nuevo más tarde.'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/inventario', methods=['POST'])
@token_required
def add_producto(current_user):
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO productos (nombre, id_tipo, cantidad, id_unidad, precio, stock_minimo, stock_maximo, id_proveedor, estado_verificacion, lote, es_toxico, es_corrosivo, es_inflamable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('nombre'),
            data.get('id_tipo', 1),  # Valor por defecto si no se envía
            data.get('cantidad'),
            data.get('id_unidad'),
            data.get('precio'),
            data.get('stock_minimo'),
            data.get('stock_maximo'),
            data.get('id_proveedor'),
            data.get('estado_verificacion', 'Pendiente'),
            data.get('lote', ''),
            data.get('es_toxico', 0),
            data.get('es_corrosivo', 0),
            data.get('es_inflamable', 0)
        ))
        product_id = cursor.lastrowid
        conn.commit()
        return jsonify({'message': 'Producto agregado correctamente', 'id': product_id}), 201
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error al agregar producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/inventario/<int:id>', methods=['PUT'])
@token_required
def update_producto(current_user, id):
    try:
        data = request.get_json()

        field_mapping = {
            'nombre': 'nombre',
            'quantity': 'cantidad',
            'precio': 'precio',
            'id_proveedor': 'id_proveedor',
            'id_tipo': 'id_tipo',
            'id_unidad': 'id_unidad',
            'stock_minimo': 'stock_minimo',
            'stock_maximo': 'stock_maximo',
            'lote': 'lote',
            'estado_verificacion': 'estado_verificacion',
            'es_toxico': 'es_toxico',
            'es_corrosivo': 'es_corrosivo',
            'es_inflamable': 'es_inflamable'
        }

        mapped_data = {field_mapping.get(key, key): value for key, value in data.items()}
        print(f"Datos mapeados: {mapped_data}")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM productos WHERE id_producto = ?', (id,))
        producto_actual = cursor.fetchone()
        if not producto_actual:
            conn.close()
            return jsonify({'error': 'Producto no encontrado'}), 404

        columns = [desc[0] for desc in cursor.description]
        producto_actual_dict = dict(zip(columns, producto_actual))
        print(f"Producto actual: {producto_actual_dict}")

        update_fields = []
        update_values = []
        cantidad_anterior = producto_actual_dict['cantidad'] or 0
        for key, value in mapped_data.items():
            if key in producto_actual_dict and value is not None:
                current_value = producto_actual_dict[key]
                if current_value is None:
                    current_value = ''
                if key in ['es_toxico', 'es_corrosivo', 'es_inflamable']:
                    value = 1 if value else 0
                    current_value = 1 if current_value else 0
                if str(current_value) != str(value):
                    update_fields.append(f"{key} = ?")
                    update_values.append(value)

        if not update_fields:
            conn.close()
            print("No se detectaron cambios para actualizar.")
            return jsonify({'message': 'No se realizaron cambios'}), 200

        update_fields.append("fecha_actualizacion = ?")
        update_values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        update_values.append(id)

        query = f"UPDATE productos SET {', '.join(update_fields)} WHERE id_producto = ?"
        print(f"Consulta UPDATE: {query}")
        print(f"Valores para UPDATE: {update_values}")
        cursor.execute(query, update_values)
        conn.commit()

        descripcion_cambios = []
        cantidad_modificada = 0.0
        for key, value in mapped_data.items():
            if key in producto_actual_dict and value is not None:
                current_value = producto_actual_dict[key]
                if current_value is None:
                    current_value = ''
                if key in ['es_toxico', 'es_corrosivo', 'es_inflamable']:
                    value = 1 if value else 0
                    current_value = 1 if current_value else 0
                if str(current_value) != str(value):
                    if key == 'cantidad':
                        try:
                            cantidad_anterior = float(current_value) if current_value else 0.0
                            cantidad_nueva = float(value)
                            cantidad_modificada = cantidad_nueva - cantidad_anterior
                        except (ValueError, TypeError) as e:
                            print(f"Error al calcular cantidad_modificada: {e}")
                            cantidad_modificada = 0.0
                    descripcion_cambios.append(f"{key} de {current_value} a {value}")

        if descripcion_cambios:
            descripcion = f"Modificación de {', '.join(descripcion_cambios)}"
            print(f"Registrando movimiento: {descripcion}")
            cursor.execute('''
                INSERT INTO movimientos_inventario (id_producto, id_usuario, tipo_movimiento, cantidad, precio, fecha_movimiento, descripcion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                id,
                current_user['id'],
                'Modificación',
                cantidad_modificada,
                producto_actual_dict['precio'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                descripcion
            ))
            conn.commit()

        conn.close()
        print("Producto actualizado correctamente.")
        return jsonify({
            'message': 'Producto actualizado correctamente',
            'cantidad_anterior': cantidad_anterior
        }), 200

    except Exception as e:
        print(f"Error al actualizar producto: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': f'Error al actualizar producto: {str(e)}'}), 500

@app.route('/api/inventario/<int:id>', methods=['GET'])
@token_required
def get_producto(current_user, id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_producto, producto, cantidad, unit_id, unidad, type_id, tipo AS type, 
                   precio, stock_minimo, stock_maximo, id_proveedor, proveedor,
                   estado_verificacion, lote, es_toxico, es_corrosivo, es_inflamable
            FROM vista_inventario
            WHERE id_producto = ?
        """, (id,))
        product = cursor.fetchone()
        if product:
            return jsonify({
                'id': product['id_producto'],
                'product': product['producto'],
                'quantity': product['cantidad'],
                'unit_id': product['unit_id'],
                'unit': product['unidad'],
                'type_id': product['type_id'],
                'type': product['type'],
                'precio': product['precio'],
                'stock_minimo': product['stock_minimo'],
                'stock_maximo': product['stock_maximo'],
                'id_proveedor': product['id_proveedor'],
                'proveedor': product['proveedor'],
                'estado_verificacion': product['estado_verificacion'],
                'lote': product['lote'],
                'es_toxico': bool(product['es_toxico']),
                'es_corrosivo': bool(product['es_corrosivo']),
                'es_inflamable': bool(product['es_inflamable'])
            })
        return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        print(f"Error al obtener producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Rutas para manejar proveedores
@app.route('/api/proveedores', methods=['GET', 'OPTIONS'])
def get_proveedores():
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_get_proveedores(current_user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM proveedores')
            proveedores = cursor.fetchall()
            return jsonify([dict(row) for row in proveedores]), 200
        except Exception as e:
            print(f"Error al obtener proveedores: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    return protected_get_proveedores()

@app.route('/api/proveedores/<int:id>', methods=['GET', 'OPTIONS'])
def get_proveedor(id):
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_get_proveedor(current_user, id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM proveedores WHERE id_proveedor = ?', (id,))
            proveedor = cursor.fetchone()
            if not proveedor:
                return jsonify({'error': 'Proveedor no encontrado'}), 404
            return jsonify(dict(proveedor)), 200
        except Exception as e:
            print(f"Error al obtener proveedor: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    return protected_get_proveedor(id)

@app.route('/api/proveedores', methods=['POST', 'OPTIONS'])
def create_proveedor():
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_create_proveedor(current_user):
        try:
            data = request.get_json()
            nombre = data.get('nombre')
            contacto = data.get('contacto')
            telefono = data.get('telefono')
            email = data.get('email')

            if not all([nombre, contacto, telefono, email]):
                return jsonify({'error': 'Todos los campos son obligatorios'}), 400

            email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(email_regex, email):
                return jsonify({'error': 'Formato de email inválido'}), 400

            telefono_regex = r'^\+?\d{9,15}$'
            if not re.match(telefono_regex, telefono):
                return jsonify({'error': 'Formato de teléfono inválido. Debe contener entre 9 y 15 dígitos, opcionalmente con un "+" al inicio.'}), 400

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT id_proveedor FROM proveedores WHERE email = ?', (email,))
            if cursor.fetchone():
                return jsonify({'error': 'El email ya está registrado para otro proveedor'}), 400

            cursor.execute('''
                INSERT INTO proveedores (nombre, contacto, telefono, email)
                VALUES (?, ?, ?, ?)
            ''', (nombre, contacto, telefono, email))

            conn.commit()
            return jsonify({'message': 'Proveedor creado exitosamente'}), 201
        except Exception as e:
            print(f"Error al crear proveedor: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    return protected_create_proveedor()

@app.route('/api/proveedores/<int:id>', methods=['PUT', 'OPTIONS'])
def update_proveedor(id):
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_update_proveedor(current_user, id):
        try:
            data = request.get_json()
            nombre = data.get('nombre')
            contacto = data.get('contacto')
            telefono = data.get('telefono')
            email = data.get('email')

            if not all([nombre, contacto, telefono, email]):
                return jsonify({'error': 'Todos los campos son obligatorios'}), 400

            email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(email_regex, email):
                return jsonify({'error': 'Formato de email inválido'}), 400

            telefono_regex = r'^\+?\d{9,15}$'
            if not re.match(telefono_regex, telefono):
                return jsonify({'error': 'Formato de teléfono inválido. Debe contener entre 9 y 15 dígitos, opcionalmente con un "+" al inicio.'}), 400

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT id_proveedor FROM proveedores WHERE email = ? AND id_proveedor != ?', (email, id))
            if cursor.fetchone():
                return jsonify({'error': 'El email ya está registrado para otro proveedor'}), 400

            cursor.execute('''
                UPDATE proveedores
                SET nombre = ?, contacto = ?, telefono = ?, email = ?
                WHERE id_proveedor = ?
            ''', (nombre, contacto, telefono, email, id))

            if cursor.rowcount == 0:
                return jsonify({'error': 'Proveedor no encontrado'}), 404

            conn.commit()
            return jsonify({'message': 'Proveedor actualizado exitosamente'}), 200
        except Exception as e:
            print(f"Error al actualizar proveedor: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    return protected_update_proveedor(id)

@app.route('/api/proveedores/<int:id>', methods=['DELETE', 'OPTIONS'])
def delete_proveedor(id):
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_delete_proveedor(current_user, id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT id_producto FROM productos WHERE id_proveedor = ?', (id,))
            if cursor.fetchone():
                return jsonify({'error': 'No se puede eliminar el proveedor porque está asociado a productos'}), 400

            cursor.execute('DELETE FROM proveedores WHERE id_proveedor = ?', (id,))

            if cursor.rowcount == 0:
                return jsonify({'error': 'Proveedor no encontrado'}), 404

            conn.commit()
            return jsonify({'message': 'Proveedor eliminado exitosamente'}), 200
        except Exception as e:
            print(f"Error al eliminar proveedor: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    return protected_delete_proveedor(id)

# Rutas para manejar procesos guardados
@app.route('/api/procesos_guardados', methods=['GET', 'OPTIONS'])
def get_procesos_guardados():
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_get_procesos_guardados(current_user):
        try:
            conn = get_db_connection()
            procesos = conn.execute('SELECT id_proceso_guardado, nombre_proceso, maquina_predeterminada, tiempo_estimado, descripcion FROM procesos_guardados ORDER BY id_proceso_guardado').fetchall()
            procesos_list = [{
                'id_proceso_guardado': row['id_proceso_guardado'],
                'nombre_proceso': row['nombre_proceso'],
                'maquina_predeterminada': row['maquina_predeterminada'],
                'tiempo_estimado': row['tiempo_estimado'],
                'descripcion': row['descripcion']
            } for row in procesos]
            return jsonify(procesos_list)
        except Exception as e:
            print(f"Error al cargar procesos guardados: {type(e).__name__} - {str(e)}")
            return jsonify({'error': f"{type(e).__name__}: {str(e)}"}), 500
        finally:
            if 'conn' in locals():
                conn.close()

    return protected_get_procesos_guardados()

@app.route('/api/prototipos', methods=['GET', 'POST', 'OPTIONS'])
def handle_prototipos():
    if request.method == 'OPTIONS':
        return '', 200
    return protected_prototipos()

@token_required
def protected_prototipos(current_user):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("Conexión a la base de datos establecida correctamente")  # Depuración

        if request.method == 'GET':
            # Obtener todos los prototipos
            print("Obteniendo todos los prototipos...")
            cursor.execute('SELECT * FROM prototipos WHERE id_usuario = ? ORDER BY id_prototipo', (current_user['id'],))
            prototipos = cursor.fetchall()
            print(f"Prototipos obtenidos: {[dict(row) for row in prototipos]}")  # Depuración
            prototipos_list = []

            # Depurar el contenido de la tabla etapas
            print("Depurando contenido de la tabla etapas...")
            cursor.execute('SELECT * FROM etapas_prototipos')  # Ajustamos el nombre de la tabla a etapas_prototipos
            todas_etapas = cursor.fetchall()
            todas_etapas_list = [dict(row) for row in todas_etapas]
            print(f"Contenido completo de la tabla etapas_prototipos: {todas_etapas_list}")

            for prototipo in prototipos:
                # Obtener las etapas de cada prototipo
                print(f"Buscando etapas para el prototipo {prototipo['id_prototipo']}")
                cursor.execute('SELECT * FROM etapas_prototipos WHERE id_prototipo = ?', (prototipo['id_prototipo'],))
                etapas = cursor.fetchall()
                print(f"Etapas para prototipo {prototipo['id_prototipo']}: {[dict(row) for row in etapas]}")  # Depuración
                etapas_list = []
                stock_suficiente = True
                stock_detalles = []

                # Verificar stock para cada etapa
                for etapa in etapas:
                    print(f"Verificando stock para producto {etapa['id_producto']} en etapa {etapa['id_etapa_prototipo']}")
                    cursor.execute('SELECT id_producto, nombre, cantidad FROM productos WHERE id_producto = ?', (etapa['id_producto'],))
                    producto = cursor.fetchone()
                    print(f"Producto {etapa['id_producto']} para etapa {etapa['id_etapa_prototipo']}: {producto}")  # Depuración

                    if not producto:
                        print(f"Advertencia: Producto con ID {etapa['id_producto']} no encontrado para etapa {etapa['id_etapa_prototipo']}")
                        cantidad_disponible = 0
                    else:
                        cantidad_disponible = float(producto['cantidad'])

                    cantidad_requerida = float(etapa['cantidad_requerida'])

                    etapa_dict = {
                        'id_etapa_prototipo': etapa['id_etapa_prototipo'],
                        'id_proceso': etapa['id_proceso'],
                        'id_producto': etapa['id_producto'],
                        'cantidad_requerida': cantidad_requerida,
                        'tiempo': int(etapa['tiempo']),
                        'nombre_proceso': etapa['nombre_proceso'],
                        'nombre_producto': etapa['nombre_producto'],
                        'stock_disponible': cantidad_disponible,
                        'stock_suficiente': cantidad_requerida <= cantidad_disponible
                    }
                    etapas_list.append(etapa_dict)

                    if cantidad_requerida > cantidad_disponible:
                        stock_suficiente = False
                        stock_detalles.append({
                            'producto': etapa['nombre_producto'],
                            'cantidad_requerida': cantidad_requerida,
                            'cantidad_disponible': cantidad_disponible
                        })

                # Agregar el prototipo a la lista
                prototipos_list.append({
                    'id_prototipo': prototipo['id_prototipo'],
                    'nombre': prototipo['nombre'],
                    'responsable': prototipo['responsable'],
                    'notas': prototipo['notas'],
                    'estado': prototipo['estado'],
                    'fecha_creacion': prototipo['fecha_creacion'],
                    'id_usuario': prototipo['id_usuario'],
                    'etapas': etapas_list,
                    'stock_suficiente': stock_suficiente,
                    'stock_detalles': stock_detalles
                })

            print(f"Prototipos listos para enviar: {prototipos_list}")
            return jsonify(prototipos_list), 200

        elif request.method == 'POST':
            data = request.get_json()
            print(f"Datos recibidos para crear prototipo: {data}")

            # Validar datos
            if not data or 'nombre' not in data or 'responsable' not in data or 'estado' not in data or 'etapas' not in data:
                print("Error: Faltan campos requeridos en los datos")
                return jsonify({'error': 'Nombre, responsable, estado y etapas son requeridos'}), 400

            nombre = data['nombre']
            responsable = data['responsable']
            notas = data.get('notas', '')
            estado = data['estado']
            etapas = data['etapas']

            # Validar etapas
            if not isinstance(etapas, list):
                print("Error: Las etapas deben ser una lista")
                return jsonify({'error': 'Las etapas deben ser una lista'}), 400
            if len(etapas) == 0:
                print("Error: Se requiere al menos una etapa")
                return jsonify({'error': 'Se requiere al menos una etapa'}), 400

            for etapa in etapas:
                required_keys = ['id_proceso', 'id_producto', 'cantidad_requerida', 'tiempo', 'nombre_proceso', 'nombre_producto']
                if not all(key in etapa for key in required_keys):
                    print(f"Error: Faltan datos en una etapa: {etapa}")
                    return jsonify({'error': 'Faltan datos en una etapa'}), 400
                if not isinstance(etapa['cantidad_requerida'], (int, float)) or etapa['cantidad_requerida'] <= 0:
                    print(f"Error: Cantidad inválida en etapa: {etapa['cantidad_requerida']}")
                    return jsonify({'error': 'La cantidad debe ser mayor que 0'}), 400
                if not isinstance(etapa['tiempo'], int) or etapa['tiempo'] <= 0:
                    print(f"Error: Tiempo inválido en etapa: {etapa['tiempo']}")
                    return jsonify({'error': 'El tiempo debe ser un entero mayor que 0'}), 400

            # Verificar stock disponible
            for etapa in etapas:
                print(f"Verificando stock para producto {etapa['id_producto']}")
                cursor.execute('SELECT id_producto, nombre, cantidad FROM productos WHERE id_producto = ?', (etapa['id_producto'],))
                producto = cursor.fetchone()
                print(f"Producto encontrado: {producto}")
                if not producto:
                    print(f"Error: Producto con ID {etapa['id_producto']} no encontrado")
                    return jsonify({
                        'error': f"Producto con ID {etapa['id_producto']} no encontrado",
                        'nombre_enviado': etapa['nombre_producto']
                    }), 404
                cantidad_disponible = float(producto['cantidad'])
                print(f"Cantidad disponible para {producto['nombre']}: {cantidad_disponible}")
                if etapa['cantidad_requerida'] > cantidad_disponible:
                    print(f"Error: Stock insuficiente para producto {etapa['nombre_producto']} (disponible: {cantidad_disponible}, requerido: {etapa['cantidad_requerida']})")
                    return jsonify({
                        'error': f"No hay suficiente stock para el producto {etapa['nombre_producto']}",
                        'detalle': f"Disponible: {cantidad_disponible}, Requerido: {etapa['cantidad_requerida']}"
                    }), 400

            # Insertar prototipo
            print("Insertando nuevo prototipo...")
            cursor.execute(
                '''
                INSERT INTO prototipos (nombre, responsable, notas, estado, id_usuario, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (nombre, responsable, notas, estado, current_user['id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            id_prototipo = cursor.lastrowid
            print(f"Prototipo creado con ID: {id_prototipo}")

            # Insertar etapas
            for etapa in etapas:
                print(f"Insertando etapa: {etapa}")
                cursor.execute(
                    '''
                    INSERT INTO etapas_prototipos (id_prototipo, id_proceso, id_producto, cantidad_requerida, tiempo, nombre_proceso, nombre_producto)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (id_prototipo, etapa['id_proceso'], etapa['id_producto'], etapa['cantidad_requerida'],
                     etapa['tiempo'], etapa['nombre_proceso'], etapa['nombre_producto'])
                )

            # Descontar cantidades del inventario
            for etapa in etapas:
                print(f"Descontando {etapa['cantidad_requerida']} unidades del producto {etapa['id_producto']}")
                cursor.execute(
                    'UPDATE productos SET cantidad = cantidad - ? WHERE id_producto = ?',
                    (etapa['cantidad_requerida'], etapa['id_producto'])
                )

            # Insertar en historial de estados
            print("Insertando en historial de estados...")
            cursor.execute(
                '''
                INSERT INTO historial_estados_prototipos (id_prototipo, estado_anterior, estado_nuevo, fecha_cambio, usuario_cambio)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (id_prototipo, None, estado, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_user['nombre'])
            )

            # Confirmar la transacción
            conn.commit()
            print(f"Prototipo {id_prototipo} creado con éxito")

            return jsonify({'message': 'Prototipo creado correctamente', 'id_prototipo': id_prototipo}), 201

    except Exception as e:
        if conn:
            conn.rollback()
            print("Transacción revertida debido a un error")
        print(f"Error al manejar prototipos: {type(e).__name__} - {str(e)}")
        return jsonify({'error': f"Error: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()
            print("Conexión a la base de datos cerrada")



@app.route('/api/inventario/all', methods=['GET', 'OPTIONS'])
def handle_inventario_all():
    if request.method == 'OPTIONS':
        return '', 200
    return protected_inventario_all()

@token_required
def protected_inventario_all(current_user):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("Obteniendo todos los productos (sin filtro de verificación)...")
        cursor.execute('SELECT * FROM productos')
        productos = cursor.fetchall()
        productos_list = [dict(row) for row in productos]
        print(f"Productos devueltos por /api/inventario/all: {productos_list}")
        return jsonify(productos_list), 200
    except Exception as e:
        print(f"Error al obtener inventario completo: {type(e).__name__} - {str(e)}")
        return jsonify({'error': f"Error: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()
            print("Conexión a la base de datos cerrada")

@app.route('/api/prototipos/<int:id_prototipo>', methods=['GET', 'PUT', 'OPTIONS'])
def get_prototipo(id_prototipo):
    # Manejar solicitudes OPTIONS sin autenticación
    if request.method == 'OPTIONS':
        return '', 200

    # Aplicar autenticación para otras solicitudes (GET, PUT)
    @token_required
    def protected_get_prototipo(current_user, id_prototipo):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            print("Conexión a la base de datos establecida correctamente")  # Depuración

            # Buscar el prototipo
            print(f"Buscando prototipo con ID: {id_prototipo}")
            cursor.execute('SELECT * FROM prototipos WHERE id_prototipo = ?', (id_prototipo,))
            prototipo = cursor.fetchone()
            if not prototipo:
                print(f"Prototipo con ID {id_prototipo} no encontrado")
                return jsonify({'error': 'Prototipo no encontrado'}), 404
            print(f"Prototipo encontrado: {prototipo}")

            # Verificar permisos
            print(f"ID de usuario del prototipo: {prototipo['id_usuario']}, ID de usuario del token: {current_user['id']}")
            if prototipo['id_usuario'] != current_user['id']:
                print("Error: El usuario no tiene permiso para acceder a este prototipo")
                return jsonify({'error': 'No tienes permiso para acceder a este prototipo'}), 403

            if request.method == 'GET':
                # Obtener las etapas
                print(f"Buscando etapas para el prototipo {id_prototipo}")
                cursor.execute('SELECT * FROM etapas_prototipos WHERE id_prototipo = ?', (id_prototipo,))
                etapas = cursor.fetchall()
                etapas_list = [{
                    'id_etapa_prototipo': etapa['id_etapa_prototipo'],
                    'id_proceso': etapa['id_proceso'],
                    'id_producto': etapa['id_producto'],
                    'cantidad_requerida': float(etapa['cantidad_requerida']),  # Asegurarse de que sea float
                    'tiempo': int(etapa['tiempo']),  # Asegurarse de que sea int
                    'nombre_proceso': etapa['nombre_proceso'],
                    'nombre_producto': etapa['nombre_producto']
                } for etapa in etapas]
                print(f"Etapas encontradas: {len(etapas_list)}")

                # Construir la respuesta
                response = {
                    'prototipo': {
                        'id_prototipo': prototipo['id_prototipo'],
                        'nombre': prototipo['nombre'],
                        'responsable': prototipo['responsable'],
                        'notas': prototipo['notas'],
                        'estado': prototipo['estado'],
                        'fecha_creacion': prototipo['fecha_creacion']
                    },
                    'etapas': etapas_list
                }
                return jsonify(response), 200

            elif request.method == 'PUT':
                data = request.get_json()
                print(f"Datos recibidos para actualizar prototipo {id_prototipo}: {data}")

                # Validar datos
                if not data or 'nombre' not in data or 'responsable' not in data or 'estado' not in data or 'etapas' not in data:
                    print("Error: Faltan campos requeridos en los datos")
                    return jsonify({'error': 'Nombre, responsable, estado y etapas son requeridos'}), 400

                nombre = data['nombre']
                responsable = data['responsable']
                notas = data.get('notas', '')
                estado = data['estado']
                etapas = data['etapas']

                # Validar etapas
                if not isinstance(etapas, list):
                    print("Error: Las etapas deben ser una lista")
                    return jsonify({'error': 'Las etapas deben ser una lista'}), 400
                if len(etapas) == 0:
                    print("Error: Se requiere al menos una etapa")
                    return jsonify({'error': 'Se requiere al menos una etapa'}), 400

                for etapa in etapas:
                    required_keys = ['id_proceso', 'id_producto', 'cantidad_requerida', 'tiempo', 'nombre_proceso', 'nombre_producto']
                    if not all(key in etapa for key in required_keys):
                        print(f"Error: Faltan datos en una etapa: {etapa}")
                        return jsonify({'error': 'Faltan datos en una etapa'}), 400
                    if not isinstance(etapa['cantidad_requerida'], (int, float)) or etapa['cantidad_requerida'] <= 0:
                        print(f"Error: Cantidad inválida en etapa: {etapa['cantidad_requerida']}")
                        return jsonify({'error': 'La cantidad debe ser mayor que 0'}), 400
                    if not isinstance(etapa['tiempo'], int) or etapa['tiempo'] <= 0:
                        print(f"Error: Tiempo inválido en etapa: {etapa['tiempo']}")
                        return jsonify({'error': 'El tiempo debe ser un entero mayor que 0'}), 400

                # Verificar stock disponible
                for etapa in etapas:
                    print(f"Verificando stock para producto {etapa['id_producto']}")
                    try:
                        cursor.execute('SELECT * FROM productos WHERE id_producto = ?', (etapa['id_producto'],))
                        producto = cursor.fetchone()
                        print(f"Resultado completo de la consulta para id_producto {etapa['id_producto']}: {producto}")
                        if not producto:
                            print(f"Intentando buscar con 'id' en lugar de 'id_producto'...")
                            cursor.execute('SELECT * FROM productos WHERE id_producto = ?', (etapa['id_producto'],))
                            producto = cursor.fetchone()
                            print(f"Resultado con 'id_producto': {producto}")
                        if not producto:
                            print(f"Error: Producto con ID {etapa['id_producto']} no encontrado en la base de datos")
                            return jsonify({
                                'error': f"Producto con ID {etapa['id_producto']} no encontrado",
                                'nombre_enviado': etapa['nombre_producto']
                            }), 404
                        producto_dict = dict(producto)
                        print(f"Producto convertido a diccionario: {producto_dict}")
                        cantidad_disponible = float(producto_dict.get('cantidad', producto_dict.get('quantity', 0)))
                        nombre_producto = producto_dict.get('nombre', producto_dict.get('product', 'Desconocido'))
                        print(f"Cantidad disponible para {nombre_producto}: {cantidad_disponible}")
                        if etapa['cantidad_requerida'] > cantidad_disponible:
                            print(f"Error: Stock insuficiente para producto {etapa['nombre_producto']} (disponible: {cantidad_disponible}, requerido: {etapa['cantidad_requerida']})")
                            return jsonify({
                                'error': f"No hay suficiente stock para el producto {etapa['nombre_producto']}",
                                'detalle': f"Disponible: {cantidad_disponible}, Requerido: {etapa['cantidad_requerida']}"
                            }), 400
                    except Exception as e:
                        print(f"Error al verificar stock para id_producto {etapa['id_producto']}: {type(e).__name__} - {str(e)}")
                        return jsonify({'error': f"Error al verificar stock: {str(e)}"}), 500

                # Obtener el estado actual del prototipo
                estado_anterior = prototipo['estado']
                print(f"Estado anterior del prototipo: {estado_anterior}, Nuevo estado: {estado}")

                # Actualizar prototipo
                print(f"Actualizando prototipo {id_prototipo}...")
                cursor.execute(
                    'UPDATE prototipos SET nombre = ?, responsable = ?, notas = ?, estado = ? WHERE id_prototipo = ?',
                    (nombre, responsable, notas, estado, id_prototipo)
                )
                print("Prototipo actualizado en la base de datos")

                # Eliminar etapas existentes
                print(f"Eliminando etapas existentes para el prototipo {id_prototipo}")
                cursor.execute('DELETE FROM etapas_prototipos WHERE id_prototipo = ?', (id_prototipo,))
                print("Etapas existentes eliminadas")

                # Insertar nuevas etapas
                for etapa in etapas:
                    print(f"Insertando etapa: {etapa}")
                    cursor.execute(
                        '''
                        INSERT INTO etapas_prototipos (id_prototipo, id_proceso, id_producto, cantidad_requerida, tiempo, nombre_proceso, nombre_producto)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (id_prototipo, etapa['id_proceso'], etapa['id_producto'], etapa['cantidad_requerida'],
                         etapa['tiempo'], etapa['nombre_proceso'], etapa['nombre_producto'])
                    )

                # Insertar en historial de estados (si el estado cambió)
                if estado_anterior != estado:
                    print("Insertando en historial de estados...")
                    cursor.execute(
                        '''
                        INSERT INTO historial_estados_prototipos (id_prototipo, estado_anterior, estado_nuevo, fecha_cambio, usuario_cambio)
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (id_prototipo, estado_anterior, estado, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_user['nombre'])
                    )
                    print("Historial de estados actualizado")

                # Confirmar la transacción
                conn.commit()
                print(f"Prototipo {id_prototipo} actualizado con éxito")

                return jsonify({'message': 'Prototipo actualizado correctamente'}), 200

        except Exception as e:
            if conn:
                conn.rollback()
                print("Transacción revertida debido a un error")
            print(f"Error al manejar prototipo: {type(e).__name__} - {str(e)}")
            return jsonify({'error': f"Error: {str(e)}"}), 500
        finally:
            if conn:
                conn.close()
                print("Conexión a la base de datos cerrada")

    return protected_get_prototipo(id_prototipo)

# Rutas para manejar tipos de producto
@app.route('/api/tipos_producto', methods=['GET'])
@token_required
def get_tipos_producto(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id_tipo, nombre FROM tipos_producto')
        tipos = cursor.fetchall()
        return jsonify([{'id_tipo': row['id_tipo'], 'nombre': row['nombre']} for row in tipos])
    except Exception as e:
        print(f"Error al cargar tipos de producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/tipos_producto', methods=['POST'])
@token_required
def add_tipo_producto(current_user):
    data = request.get_json()
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error': 'Nombre es requerido'}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tipos_producto (nombre) VALUES (?)', (nombre,))
        conn.commit()
        return jsonify({'message': 'Tipo de producto agregado'})
    except Exception as e:
        print(f"Error al agregar tipo de producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Rutas para verificar productos
@app.route('/api/verificar', methods=['POST'])
@token_required
def verificar_producto(current_user):
    data = request.get_json()
    id_producto = data.get('id_producto')
    estado_verificacion = data.get('estado_verificacion')

    if not id_producto or not estado_verificacion:
        return jsonify({'error': 'ID de producto y estado son requeridos'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM productos WHERE id_producto = ?", (id_producto,))
        producto = cursor.fetchone()
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        cursor.execute("""
            UPDATE productos 
            SET estado_verificacion = ?, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id_producto = ?
        """, (estado_verificacion, id_producto))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        cursor.execute("""
            INSERT INTO movimientos_inventario (id_producto, id_usuario, tipo_movimiento, cantidad, fecha_movimiento, descripcion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            id_producto,
            current_user['id'],
            'Verificación',
            0,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            f"Producto marcado como {estado_verificacion}"
        ))
        conn.commit()
        
        return jsonify({
            'message': 'Producto verificado correctamente',
            'producto': producto['nombre']
        })
    except Exception as e:
        print(f"Error al verificar producto: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Rutas para reportes
@app.route('/api/reportes', methods=['GET', 'OPTIONS'])
def get_reportes():
    if request.method == 'OPTIONS':
        return '', 200

    @token_required
    def protected_get_reportes(current_user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            start_date = request.args.get('startDate')
            end_date = request.args.get('endDate')
            date_filter = ""
            date_params = []
            if start_date and end_date:
                try:
                    # Validar formato de fechas (YYYY-MM-DD)
                    datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.strptime(end_date, '%Y-%m-%d')
                    date_filter = "WHERE fecha_movimiento BETWEEN ? AND ?"
                    date_params = [start_date, end_date]
                except ValueError:
                    return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400

            # Resumen del Inventario
            query_inventario = '''
                SELECT * FROM vista_inventario
                WHERE estado_verificacion = 'Verificado'
            '''
            cursor.execute(query_inventario)
            inventario = cursor.fetchall()

            total_productos = len(inventario)
            valor_total = 0
            productos_list = []
            for item in inventario:
                try:
                    cantidad = float(item['cantidad']) if item['cantidad'] is not None else 0
                    precio = float(item['precio']) if item['precio'] is not None else 0
                    valor_total += cantidad * precio
                    productos_list.append({
                        'nombre': item['producto'],
                        'cantidad': cantidad,
                        'precio': precio,
                        'stock_minimo': float(item['stock_minimo']) if item['stock_minimo'] is not None else 0,
                        'stock_maximo': float(item['stock_maximo']) if item['stock_maximo'] is not None else 0,
                        'es_toxico': bool(item['es_toxico']),
                        'es_corrosivo': bool(item['es_corrosivo']),
                        'es_inflamable': bool(item['es_inflamable'])
                    })
                except (ValueError, TypeError) as e:
                    print(f"Error al procesar producto {item['producto']}: {e}")
                    continue

            productos_bajo_stock = [
                {
                    'nombre': row['nombre'],
                    'cantidad': row['cantidad'],
                    'stock_minimo': row['stock_minimo']
                }
                for row in productos_list if row['cantidad'] < row['stock_minimo']
            ]

            productos_especiales = [
                {
                    'nombre': row['nombre'],
                    'toxico': row['es_toxico'],
                    'corrosivo': row['es_corrosivo'],
                    'inflamable': row['es_inflamable']
                }
                for row in productos_list if row['es_toxico'] or row['es_corrosivo'] or row['es_inflamable']
            ]

            # Análisis de Movimientos
            total_movimientos_query = f'''
                SELECT COUNT(*) as count
                FROM movimientos_inventario
                {date_filter}
            '''
            cursor.execute(total_movimientos_query, date_params)
            total_movimientos_result = cursor.fetchone()
            total_movimientos = total_movimientos_result['count'] if total_movimientos_result else 0

            movimientos_por_tipo_query = f'''
                SELECT tipo_movimiento, COUNT(*) as cantidad
                FROM movimientos_inventario
                {date_filter}
                GROUP BY tipo_movimiento
            '''
            cursor.execute(movimientos_por_tipo_query, date_params)
            movimientos_por_tipo = cursor.fetchall()
            movimientos_por_tipo_list = [
                {'tipo_movimiento': row['tipo_movimiento'], 'cantidad': row['cantidad']}
                for row in movimientos_por_tipo
            ]

            ultimos_movimientos_query = f'''
                SELECT m.id_producto, m.id_usuario, u.nombre as usuario, m.tipo_movimiento, m.cantidad, m.fecha_movimiento, m.descripcion, p.nombre as nombre_producto
                FROM movimientos_inventario m
                LEFT JOIN productos p ON m.id_producto = p.id_producto
                LEFT JOIN usuarios u ON m.id_usuario = u.id_usuario
                {date_filter}
                ORDER BY m.fecha_movimiento DESC
                LIMIT 10
            '''
            cursor.execute(ultimos_movimientos_query, date_params)
            ultimos_movimientos = cursor.fetchall()
            ultimos_movimientos_list = [
                {
                    'id_producto': row['id_producto'],
                    'nombre_producto': row['nombre_producto'],
                    'usuario': row['usuario'] if row['usuario'] else 'N/A',
                    'tipo_movimiento': row['tipo_movimiento'],
                    'cantidad': float(row['cantidad']) if row['cantidad'] is not None else 0,
                    'fecha_movimiento': row['fecha_movimiento'],
                    'descripcion': row['descripcion'] if row['descripcion'] else 'N/A'
                }
                for row in ultimos_movimientos
            ]

            # Estadísticas Adicionales
            cursor.execute('''
                SELECT pr.nombre, COUNT(p.id_producto) as total_productos
                FROM proveedores pr
                LEFT JOIN productos p ON pr.id_proveedor = p.id_proveedor
                GROUP BY pr.id_proveedor, pr.nombre
                ORDER BY total_productos DESC
                LIMIT 5
            ''')
            proveedores_mas_productos = cursor.fetchall()
            proveedores_mas_productos_list = [
                {'nombre': row['nombre'], 'total_productos': row['total_productos']}
                for row in proveedores_mas_productos
            ]

            cursor.execute('''
                SELECT t.nombre, COUNT(p.id_producto) as total_productos
                FROM tipos_producto t
                LEFT JOIN productos p ON t.id_tipo = p.id_tipo
                GROUP BY t.id_tipo, t.nombre
                ORDER BY total_productos DESC
                LIMIT 5
            ''')
            tipos_mas_comunes = cursor.fetchall()
            tipos_mas_comunes_list = [
                {'nombre': row['nombre'], 'total_productos': row['total_productos']}
                for row in tipos_mas_comunes
            ]

            cursor.execute('''
                SELECT p.nombre, COUNT(m.id_movimiento) as total_salidas
                FROM productos p
                LEFT JOIN movimientos_inventario m ON p.id_producto = m.id_producto
                WHERE m.tipo_movimiento = 'Salida'
                GROUP BY p.id_producto, p.nombre
                ORDER BY total_salidas DESC
                LIMIT 5
            ''')
            productos_mayor_rotacion = cursor.fetchall()
            productos_mayor_rotacion_list = [
                {'nombre': row['nombre'], 'total_salidas': row['total_salidas']}
                for row in productos_mayor_rotacion
            ]

            # Productos más utilizados (basado en etapas de prototipos)
            cursor.execute('''
                SELECT ep.nombre_producto, SUM(ep.cantidad_requerida) as total_requerido
                FROM etapas_prototipos ep
                JOIN prototipos p ON ep.id_prototipo = p.id_prototipo
                GROUP BY ep.id_producto, ep.nombre_producto
                ORDER BY total_requerido DESC
                LIMIT 5
            ''')
            productos_mas_utilizados = cursor.fetchall()
            productos_mas_utilizados_list = [
                {'nombre_producto': row['nombre_producto'], 'total_requerido': float(row['total_requerido'])}
                for row in productos_mas_utilizados
            ]

            # Gráficos
            cursor.execute('''
                SELECT t.nombre, COUNT(p.id_producto) as cantidad
                FROM tipos_producto t
                LEFT JOIN productos p ON t.id_tipo = p.id_tipo
            ''')
            distribucion_tipos = cursor.fetchall()
            distribucion_tipos_list = [
                {'nombre': row['nombre'], 'cantidad': row['cantidad']}
                for row in distribucion_tipos
            ]

            movimientos_por_dia_query = f'''
                SELECT DATE(fecha_movimiento) as dia, COUNT(*) as cantidad
                FROM movimientos_inventario
                {date_filter}
                GROUP BY DATE(fecha_movimiento)
                ORDER BY dia DESC
                LIMIT 30
            '''
            cursor.execute(movimientos_por_dia_query, date_params)
            movimientos_por_dia = cursor.fetchall()
            movimientos_por_dia_list = [
                {'dia': row['dia'], 'cantidad': row['cantidad']}
                for row in movimientos_por_dia
            ]

            return jsonify({
                'resumen_inventario': {
                    'total_productos': total_productos,
                    'valor_total': float(valor_total),
                    'productos': productos_list,  # Añadimos la lista de productos
                    'productos_bajo_stock': productos_bajo_stock,
                    'productos_especiales': productos_especiales
                },
                'analisis_movimientos': {
                    'total_movimientos': total_movimientos,
                    'movimientos_por_tipo': movimientos_por_tipo_list,
                    'ultimos_movimientos': ultimos_movimientos_list
                },
                'estadisticas_adicionales': {
                    'proveedores_mas_productos': proveedores_mas_productos_list,
                    'tipos_mas_comunes': tipos_mas_comunes_list,
                    'productos_mayor_rotacion': productos_mayor_rotacion_list,
                    'productos_mas_utilizados': productos_mas_utilizados_list  # Añadimos productos más utilizados
                },
                'graficos': {
                    'distribucion_tipos': distribucion_tipos_list,
                    'movimientos_por_dia': movimientos_por_dia_list
                }
            }), 200

        except Exception as e:
            print(f"Error al generar reporte: {str(e)}")
            return jsonify({'error': str(e)}), 500

        finally:
            if 'conn' in locals():
                conn.close()

    return protected_get_reportes()

@app.route('/api/reportes/export', methods=['GET', 'OPTIONS'])
def export_reporte():
    if request.method == 'OPTIONS':
        return '', 200
    
    @token_required
    def protected_export_reporte(current_user):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Obtener datos de los productos con sus relaciones
            cursor.execute('''
                SELECT 
                    p.id_producto,
                    p.nombre,
                    p.cantidad,
                    u.abreviatura as unidad,
                    p.stock_minimo,
                    p.stock_maximo,
                    p.precio,
                    p.estado_verificacion,
                    pr.nombre as proveedor_nombre,
                    t.nombre as tipo_nombre,
                    p.lote,
                    p.es_toxico,
                    p.es_corrosivo,
                    p.es_inflamable
                FROM productos p
                LEFT JOIN unidades_medida u ON p.id_unidad = u.id_unidad
                LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor
                LEFT JOIN tipos_producto t ON p.id_tipo = t.id_tipo
            ''')
            productos = cursor.fetchall()
            
            # Convertir los datos a un formato adecuado para pandas
            data = []
            for item in productos:
                data.append({
                    'ID': item[0],  # id_producto
                    'Nombre': item[1],  # nombre
                    'Cantidad': item[2],  # cantidad
                    'Unidad': item[3],  # unidad
                    'Stock Mínimo': item[4],  # stock_minimo
                    'Stock Máximo': item[5],  # stock_maximo
                    'Precio': item[6],  # precio
                    'Estado': item[7],  # estado_verificacion
                    'Proveedor': item[8],  # proveedor_nombre
                    'Tipo': item[9],  # tipo_nombre
                    'Lote': item[10],  # lote
                    'Es Tóxico': 'Sí' if item[11] else 'No',  # es_toxico
                    'Es Corrosivo': 'Sí' if item[12] else 'No',  # es_corrosivo
                    'Es Inflamable': 'Sí' if item[13] else 'No'  # es_inflamable
                })
            
            # Crear un archivo Excel en memoria con xlsxwriter (sin pandas)
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Inventario')

            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })

            columnas = list(data[0].keys()) if data else []
            for col_num, value in enumerate(columnas):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)
            for fila, item in enumerate(data, start=1):
                for col_num, value in enumerate(columnas):
                    worksheet.write(fila, col_num, item.get(value))
            workbook.close()
            
            output.seek(0)
            
            # Generar nombre de archivo con fecha
            fecha_actual = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            nombre_archivo = f'Reporte_Avanzado_{fecha_actual}.xlsx'
            
            # Configurar la respuesta
            response = send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=nombre_archivo
            )
            
            # Agregar headers necesarios
            response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
            
            return response
            
        except Exception as e:
            print(f"Error al exportar reporte: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            conn.close()
    
    return protected_export_reporte()

# Rutas para manejar lotes
@app.route('/api/lotes', methods=['GET', 'POST', 'OPTIONS'])
@token_required
def handle_lotes(current_user):
    if request.method == 'OPTIONS':
        return '', 200

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'GET':
            print("Solicitud GET recibida para /api/lotes")
            cursor.execute('SELECT * FROM lotes ORDER BY id_lote')
            lotes = cursor.fetchall()
            lotes_list = [{
                'id_lote': row['id_lote'],
                'numero_lote': row['numero_lote'],
                'estado_actual': row['estado_actual']
            } for row in lotes]
            return jsonify(lotes_list)

        elif request.method == 'POST':
            data = request.get_json()
            numero_lote = data.get('numero_lote')
            etapas = data.get('etapas')

            if not numero_lote or not etapas:
                return jsonify({'error': 'Número de lote y etapas son requeridos'}), 400

            cursor.execute('SELECT id_lote FROM lotes WHERE numero_lote = ?', (numero_lote,))
            if cursor.fetchone():
                return jsonify({'error': 'El número de lote ya existe'}), 400

            for etapa in etapas:
                productos_requeridos = etapa.get('productos_requeridos', {})
                for producto_nombre, cantidad in productos_requeridos.items():
                    cursor.execute('SELECT id_producto, nombre, cantidad FROM productos WHERE nombre = ?', (producto_nombre,))
                    producto = cursor.fetchone()
                    if not producto:
                        conn.rollback()
                        return jsonify({'error': f'Producto {producto_nombre} no encontrado'}), 404
                    if producto['cantidad'] < cantidad:
                        conn.rollback()
                        return jsonify({'error': f'No hay suficiente {producto_nombre} en inventario. Disponible: {producto["cantidad"]}, Requerido: {cantidad}'}), 400

            cursor.execute('INSERT INTO lotes (numero_lote, estado_actual) VALUES (?, ?)', 
                          (numero_lote, 'Iniciado'))
            id_lote = cursor.lastrowid

            for etapa in etapas:
                cursor.execute("""
                    INSERT INTO etapas_lotes (id_lote, numero_etapa, nombre_etapa, tiempo_estimado, maquina_utilizada, estado_etapa)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_lote, etapa['numero_etapa'], etapa['nombre_etapa'], etapa['tiempo_estimado'], 
                      etapa['maquina_utilizada'], 'Pendiente'))

                id_etapa_lote = cursor.lastrowid
                productos_requeridos = etapa.get('productos_requeridos', {})
                for producto_nombre, cantidad in productos_requeridos.items():
                    cursor.execute('SELECT id_producto FROM productos WHERE nombre = ?', (producto_nombre,))
                    producto = cursor.fetchone()
                    if not producto:
                        conn.rollback()
                        return jsonify({'error': f'Producto {producto_nombre} no encontrado al insertar en etapas_productos'}), 404
                    cursor.execute("""
                        INSERT INTO etapas_productos (id_etapa_lote, id_producto, nombre_producto, cantidad_requerida)
                        VALUES (?, ?, ?, ?)
                    """, (id_etapa_lote, producto['id_producto'], producto_nombre, cantidad))

            conn.commit()
            print(f"Lote {id_lote} creado con éxito")
            return jsonify({'message': 'Lote creado correctamente', 'id': id_lote}), 201

    except Exception as e:
        conn.rollback()
        print(f"Error al manejar lotes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/lotes/<int:id_lote>', methods=['GET', 'PUT'])
@token_required
def get_lote(id_lote, current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'GET':
            cursor.execute('SELECT * FROM lotes WHERE id_lote = ?', (id_lote,))
            lote = cursor.fetchone()
            if not lote:
                return jsonify({'error': 'Lote no encontrado'}), 404

            cursor.execute('SELECT * FROM etapas_lotes WHERE id_lote = ? ORDER BY numero_etapa', (id_lote,))
            etapas = cursor.fetchall()

            etapas_list = []
            for etapa in etapas:
                cursor.execute('SELECT nombre_producto, cantidad_requerida FROM etapas_productos WHERE id_etapa_lote = ?', (etapa['id_etapa_lote'],))
                productos = cursor.fetchall()
                productos_requeridos = {row['nombre_producto']: row['cantidad_requerida'] for row in productos}

                etapas_list.append({
                    'id_etapa_lote': etapa['id_etapa_lote'],
                    'numero_etapa': etapa['numero_etapa'],
                    'nombre_etapa': etapa['nombre_etapa'],
                    'tiempo_estimado': etapa['tiempo_estimado'],
                    'tiempo_restante': etapa['tiempo_restante'],
                    'maquina_utilizada': etapa['maquina_utilizada'],
                    'estado_etapa': etapa['estado_etapa'],
                    'productos_requeridos': productos_requeridos
                })

            return jsonify({
                'lote': {
                    'id_lote': lote['id_lote'],
                    'numero_lote': lote['numero_lote'],
                    'estado_actual': lote['estado_actual']
                },
                'etapas': etapas_list
            })

        elif request.method == 'PUT':
            data = request.get_json()
            numero_lote = data.get('numero_lote')
            etapas = data.get('etapas')

            if not numero_lote or not etapas:
                return jsonify({'error': 'Número de lote y etapas son requeridos'}), 400

            cursor.execute('SELECT * FROM lotes WHERE id_lote = ?', (id_lote,))
            if not cursor.fetchone():
                return jsonify({'error': 'Lote no encontrado'}), 404

            cursor.execute('SELECT id_lote FROM lotes WHERE numero_lote = ? AND id_lote != ?', (numero_lote, id_lote))
            if cursor.fetchone():
                return jsonify({'error': 'El número de lote ya existe'}), 400

            for etapa in etapas:
                print(f"Verificando stock para producto {etapa['id_producto']}")
                try:
                    cursor.execute('SELECT cantidad, nombre FROM productos WHERE id_producto = ?', (etapa['id_producto'],))
                    producto = cursor.fetchone()
                    print(f"Resultado de la consulta para id_producto {etapa['id_producto']}: {producto}")
                    if not producto:
                        print(f"Error: Producto con ID {etapa['id_producto']} no encontrado en la base de datos")
                        return jsonify({
                            'error': f"Producto con ID {etapa['id_producto']} no encontrado",
                            'nombre_enviado': etapa['nombre_producto']
                        }), 404
                    cantidad_disponible = float(producto['cantidad'])
                    print(f"Cantidad disponible para {producto['nombre']}: {cantidad_disponible}")
                    if etapa['cantidad_requerida'] > cantidad_disponible:
                        print(f"Error: Stock insuficiente para producto {etapa['nombre_producto']} (disponible: {cantidad_disponible}, requerido: {etapa['cantidad_requerida']})")
                        return jsonify({
                            'error': f"No hay suficiente stock para el producto {etapa['nombre_producto']}",
                            'detalle': f"Disponible: {cantidad_disponible}, Requerido: {etapa['cantidad_requerida']}"
                        }), 400

                except Exception as e:
                        print(f"Error inesperado al verificar stock: {type(e).__name__} - {str(e)}")
                        return jsonify({'error': f"Error inesperado: {str(e)}"}), 500

            cursor.execute('UPDATE lotes SET numero_lote = ?, estado_actual = ? WHERE id_lote = ?', 
                          (numero_lote, 'Iniciado', id_lote))

            cursor.execute('DELETE FROM etapas_lotes WHERE id_lote = ?', (id_lote,))
            cursor.execute('DELETE FROM etapas_productos WHERE id_etapa_lote IN (SELECT id_etapa_lote FROM etapas_lotes WHERE id_lote = ?)', (id_lote,))

            for etapa in etapas:
                cursor.execute("""
                    INSERT INTO etapas_lotes (id_lote, numero_etapa, nombre_etapa, tiempo_estimado, maquina_utilizada, estado_etapa)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_lote, etapa['numero_etapa'], etapa['nombre_etapa'], etapa['tiempo_estimado'], 
                      etapa['maquina_utilizada'], 'Pendiente'))
                id_etapa_lote = cursor.lastrowid
                productos_requeridos = etapa.get('productos_requeridos', {})
                for producto_nombre, cantidad in productos_requeridos.items():
                    cursor.execute('SELECT id_producto FROM productos WHERE nombre = ?', (producto_nombre,))
                    producto = cursor.fetchone()
                    if not producto:
                        conn.rollback()
                        return jsonify({'error': f'Producto {producto_nombre} no encontrado al insertar en etapas_productos'}), 404
                    cursor.execute("""
                        INSERT INTO etapas_productos (id_etapa_lote, id_producto, nombre_producto, cantidad_requerida)
                        VALUES (?, ?, ?, ?)
                    """, (id_etapa_lote, producto['id_producto'], producto_nombre, cantidad))

            conn.commit()
            print(f"Lote {id_lote} actualizado con éxito")
            return jsonify({'message': 'Lote actualizado correctamente'}), 200

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error al manejar lote {id_lote}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Rutas para manejar etapas de lotes
@app.route('/api/lotes/<int:id_lote>/etapas/<int:id_etapa_lote>', methods=['PUT'])
@token_required
def update_etapa_lote(id_lote, id_etapa_lote, current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        data = request.get_json()
        estado_etapa = data.get('estado_etapa')
        tiempo_restante = data.get('tiempo_restante')

        if not estado_etapa:
            return jsonify({'error': 'Estado de la etapa es requerido'}), 400

        cursor.execute('SELECT * FROM etapas_lotes WHERE id_etapa_lote = ? AND id_lote = ?', (id_etapa_lote, id_lote))
        etapa = cursor.fetchone()
        if not etapa:
            return jsonify({'error': 'Etapa no encontrada'}), 404

        cursor.execute('SELECT * FROM lotes WHERE id_lote = ?', (id_lote,))
        lote = cursor.fetchone()
        if not lote:
            return jsonify({'error': 'Lote no encontrado'}), 404

        update_fields = []
        update_values = []

        if estado_etapa:
            update_fields.append("estado_etapa = ?")
            update_values.append(estado_etapa)
        if tiempo_restante is not None:
            update_fields.append("tiempo_restante = ?")
            update_values.append(tiempo_restante)

        if not update_fields:
            return jsonify({'message': 'No se proporcionaron datos para actualizar'}), 200

        update_values.append(id_etapa_lote)
        update_values.append(id_lote)

        query = f"UPDATE etapas_lotes SET {', '.join(update_fields)} WHERE id_etapa_lote = ? AND id_lote = ?"
        cursor.execute(query, update_values)

        cursor.execute('SELECT * FROM etapas_lotes WHERE id_lote = ? AND estado_etapa != "Completada"', (id_lote,))
        etapas_pendientes = cursor.fetchall()
        nuevo_estado_lote = "Completado" if not etapas_pendientes else "En Progreso"
        cursor.execute('UPDATE lotes SET estado_actual = ? WHERE id_lote = ?', (nuevo_estado_lote, id_lote))

        conn.commit()
        return jsonify({'message': 'Etapa actualizada correctamente', 'estado_lote': nuevo_estado_lote})

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error al actualizar etapa {id_etapa_lote}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Rutas para manejar unidades
@app.route('/api/unidades', methods=['GET'])
@token_required
def get_unidades(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id_unidad, nombre FROM unidades_medida')  # Cambiado de 'unidades' a 'unidades_medida'
        unidades = cursor.fetchall()
        return jsonify([{'id_unidad': row['id_unidad'], 'nombre': row['nombre']} for row in unidades])
    except Exception as e:
        print(f"Error al cargar unidades: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/unidades', methods=['POST'])
@token_required
def add_unidad(current_user):
    data = request.get_json()
    nombre = data.get('nombre')
    if not nombre:
        return jsonify({'error': 'Nombre es requerido'}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO unidades_medida (nombre) VALUES (?)', (nombre,))  # Cambiado de 'unidades' a 'unidades_medida'
        conn.commit()
        return jsonify({'message': 'Unidad agregada'})
    except Exception as e:
        print(f"Error al agregar unidad: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Rutas para manejar usuarios
@app.route('/api/usuarios', methods=['GET'])
@token_required
def get_usuarios(current_user):
    if current_user['rol'] != 'Administrador':
        return jsonify({'error': 'No tienes permiso para acceder a esta ruta'}), 403
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id_usuario, nombre, rol FROM usuarios')
        usuarios = cursor.fetchall()
        return jsonify([{
            'id_usuario': row['id_usuario'],
            'nombre': row['nombre'],
            'rol': row['rol']
        } for row in usuarios])
    except Exception as e:
        print(f"Error al cargar usuarios: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/usuarios', methods=['POST'])
@token_required
def add_usuario(current_user):
    if current_user['rol'] != 'admin':
        return jsonify({'error': 'No tienes permiso para acceder a esta ruta'}), 403

    data = request.get_json()
    nombre = data.get('nombre')
    contrasena = data.get('contrasena')
    rol = data.get('rol', 'usuario')

    if not nombre or not contrasena:
        return jsonify({'error': 'Nombre y contraseña son requeridos'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nombre = ?', (nombre,))
        if cursor.fetchone():
            return jsonify({'error': 'El nombre de usuario ya existe'}), 400

        cursor.execute('INSERT INTO usuarios (nombre, contrasena, rol) VALUES (?, ?, ?)',
                       (nombre, generate_password_hash(contrasena), rol))
        conn.commit()
        return jsonify({'message': 'Usuario creado correctamente'})
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/usuarios/<int:id>', methods=['PUT'])
@token_required
def update_usuario(current_user, id):
    if current_user['rol'] != 'admin':
        return jsonify({'error': 'No tienes permiso para acceder a esta ruta'}), 403

    data = request.get_json()
    nombre = data.get('nombre')
    contrasena = data.get('contrasena')
    rol = data.get('rol')

    if not nombre or not rol:
        return jsonify({'error': 'Nombre y rol son requeridos'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE id_usuario = ?', (id,))
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        cursor.execute('SELECT * FROM usuarios WHERE nombre = ? AND id_usuario != ?', (nombre, id))
        if cursor.fetchone():
            return jsonify({'error': 'El nombre de usuario ya existe'}), 400

        if contrasena:
            # Guardar la contraseña en texto plano
            cursor.execute('UPDATE usuarios SET nombre = ?, contrasena = ?, rol = ? WHERE id_usuario = ?', 
                           (nombre, contrasena, rol, id))
        else:
            cursor.execute('UPDATE usuarios SET nombre = ?, rol = ? WHERE id_usuario = ?', 
                           (nombre, rol, id))
        conn.commit()
        return jsonify({'message': 'Usuario actualizado correctamente'})
    except Exception as e:
        print(f"Error al actualizar usuario: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
@token_required
def delete_usuario(current_user, id):
    if current_user['rol'] != 'admin':
        return jsonify({'error': 'No tienes permiso para acceder a esta ruta'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE id_usuario = ?', (id,))
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        if usuario['id_usuario'] == current_user['id']:
            return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400

        cursor.execute('DELETE FROM usuarios WHERE id_usuario = ?', (id,))
        conn.commit()
        return jsonify({'message': 'Usuario eliminado correctamente'})
    except Exception as e:
        print(f"Error al eliminar usuario: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Ruta para manejar el dashboard
@app.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total de productos
        cursor.execute('SELECT COUNT(*) as total FROM productos WHERE estado_verificacion = "Verificado"')
        total_productos = cursor.fetchone()['total']

        # Productos bajo stock
        cursor.execute('''
            SELECT COUNT(*) as bajo_stock
            FROM productos
            WHERE cantidad < stock_minimo AND estado_verificacion = "Verificado"
        ''')
        productos_bajo_stock = cursor.fetchone()['bajo_stock']

        # Total de movimientos (últimos 30 días)
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM movimientos_inventario
            WHERE fecha_movimiento >= ?
        ''', (datetime.now() - timedelta(days=30),))
        total_movimientos = cursor.fetchone()['total']

        # Total de prototipos
        cursor.execute('SELECT COUNT(*) as total FROM prototipos WHERE id_usuario = ?', (current_user['id'],))
        total_prototipos = cursor.fetchone()['total']

        # Prototipos por estado
        cursor.execute('''
            SELECT estado, COUNT(*) as cantidad
            FROM prototipos
            WHERE id_usuario = ?
            GROUP BY estado
        ''', (current_user['id'],))
        prototipos_por_estado = cursor.fetchall()
        prototipos_por_estado_list = [
            {'estado': row['estado'], 'cantidad': row['cantidad']}
            for row in prototipos_por_estado
        ]

        return jsonify({
            'total_productos': total_productos,
            'productos_bajo_stock': productos_bajo_stock,
            'total_movimientos': total_movimientos,
            'total_prototipos': total_prototipos,
            'prototipos_por_estado': prototipos_por_estado_list
        })
    except Exception as e:
        print(f"Error al cargar datos del dashboard: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/optimizador/lote/<int:id_lote>', methods=['GET'])
@token_required
def api_optimizador_lote(current_user, id_lote):
    try:
        conn = get_db_connection()
        return jsonify(sostenibilidad.compute_lote_optimizacion(conn, id_lote))
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Error en optimizador de lote: {e}")
        return jsonify({'error': 'No se pudo calcular la optimización'}), 500


@app.route('/api/optimizador/acumulado', methods=['GET'])
@token_required
def api_optimizador_acumulado(current_user):
    try:
        conn = get_db_connection()
        return jsonify(sostenibilidad.compute_acumulado_global(conn))
    except Exception as e:
        print(f"Error en acumulado global: {e}")
        return jsonify({'error': 'No se pudo calcular el acumulado'}), 500


@app.route('/api/sostenibilidad/kpis', methods=['GET'])
@token_required
def api_sostenibilidad_kpis(current_user):
    try:
        conn = get_db_connection()
        return jsonify(sostenibilidad.compute_kpis(conn))
    except Exception as e:
        print(f"Error en KPIs: {e}")
        return jsonify({'error': 'No se pudieron calcular los KPIs'}), 500


@app.route('/api/sostenibilidad/graficas', methods=['GET'])
@token_required
def api_sostenibilidad_graficas(current_user):
    try:
        conn = get_db_connection()
        return jsonify(sostenibilidad.compute_graficas(conn))
    except Exception as e:
        print(f"Error en graficas: {e}")
        return jsonify({'error': 'No se pudieron calcular las graficas'}), 500


@app.route('/api/prediccion/consumo', methods=['GET'])
@token_required
def api_prediccion_consumo(current_user):
    try:
        conn = get_db_connection()
        productos = conn.execute(
            "SELECT id_producto, nombre, cantidad, stock_minimo FROM productos"
        ).fetchall()
        resultado = []
        for p in productos:
            pred = sostenibilidad.predecir_consumo(conn, p['id_producto'])
            pred['nombre'] = p['nombre']
            pred['stock_actual'] = p['cantidad']
            pred['stock_minimo'] = p['stock_minimo']
            pred['reordenar'] = bool(
                pred['proyeccion'] > 0 and p['cantidad'] is not None
                and float(p['cantidad']) <= float(pred['proyeccion'])
            )
            resultado.append(pred)
        return jsonify(resultado)
    except Exception as e:
        print(f"Error en predicción de consumo: {e}")
        return jsonify({'error': 'No se pudo calcular la predicción'}), 500


@app.route('/api/factores_ambientales', methods=['GET'])
@token_required
def api_get_factores(current_user):
    try:
        conn = get_db_connection()
        rows = conn.execute("""
            SELECT f.id_factor, f.id_producto, p.nombre AS producto,
                   f.agua_l_por_kg, f.co2_kg_por_kg, f.carga_efluente_gdqo_por_kg,
                   f.eco_score, f.fuente, f.es_estimacion
            FROM factores_ambientales f
            LEFT JOIN productos p ON p.id_producto = f.id_producto
            ORDER BY f.id_producto
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        print(f"Error al obtener factores: {e}")
        return jsonify({'error': 'No se pudieron obtener los coeficientes'}), 500


@app.route('/api/factores_ambientales', methods=['POST'])
@token_required
def api_post_factor(current_user):
    if current_user.get('rol') != 'Administrador':
        return jsonify({'error': 'Solo el Administrador puede editar coeficientes'}), 403
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO factores_ambientales
                (id_producto, agua_l_por_kg, co2_kg_por_kg, carga_efluente_gdqo_por_kg,
                 eco_score, fuente, es_estimacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_producto) DO UPDATE SET
                agua_l_por_kg=excluded.agua_l_por_kg,
                co2_kg_por_kg=excluded.co2_kg_por_kg,
                carga_efluente_gdqo_por_kg=excluded.carga_efluente_gdqo_por_kg,
                eco_score=excluded.eco_score,
                fuente=excluded.fuente,
                es_estimacion=excluded.es_estimacion
        """, (
            data.get('id_producto'), data.get('agua_l_por_kg', 0),
            data.get('co2_kg_por_kg', 0), data.get('carga_efluente_gdqo_por_kg', 0),
            data.get('eco_score', 'C'), data.get('fuente'), data.get('es_estimacion', 1),
        ))
        conn.commit()
        return jsonify({'message': 'Coeficiente guardado'}), 201
    except Exception as e:
        print(f"Error al guardar factor: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/factores_ambientales/<int:id_producto>', methods=['PUT'])
@token_required
def api_put_factor(current_user, id_producto):
    if current_user.get('rol') != 'Administrador':
        return jsonify({'error': 'Solo el Administrador puede editar coeficientes'}), 403
    data = request.get_json()
    try:
        conn = get_db_connection()
        cur = conn.execute("""
            UPDATE factores_ambientales
            SET agua_l_por_kg = ?, co2_kg_por_kg = ?, carga_efluente_gdqo_por_kg = ?,
                eco_score = ?, fuente = ?, es_estimacion = ?
            WHERE id_producto = ?
        """, (
            data.get('agua_l_por_kg', 0), data.get('co2_kg_por_kg', 0),
            data.get('carga_efluente_gdqo_por_kg', 0), data.get('eco_score', 'C'),
            data.get('fuente'), data.get('es_estimacion', 1), id_producto,
        ))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({'error': 'No existe coeficiente para ese producto'}), 404
        return jsonify({'message': 'Coeficiente actualizado'}), 200
    except Exception as e:
        print(f"Error al actualizar factor: {e}")
        return jsonify({'error': str(e)}), 500


# Iniciar el servidor Flask (esto no se ejecutará cuando PyWebView lo inicie)
if __name__ == '__main__':
    app.run(debug=True)


               