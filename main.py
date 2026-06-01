import webview
import sys
import logging
import threading
import time
import base64
import os

# Importa la instancia 'app' de Flask desde tu archivo app.py
try:
    from app import app
    # Configura Flask para que no muestre mensajes estándar de servidor en la consola
    # Esto es opcional, pero hace que la salida sea más limpia cuando se ejecuta empaquetado.
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.logger.disabled = True
except ImportError as e:
    print(f"Error: No se pudo importar 'app' desde app.py: {e}")
    print("Asegúrate de que app.py esté en el mismo directorio y no tenga errores de sintaxis.")
    sys.exit(1)
except Exception as e:
    print(f"Error inesperado al importar o configurar Flask: {e}")
    sys.exit(1)

class Api:
    def save_file_dialog(self, params):
        """Muestra un diálogo para guardar archivo y retorna la ruta seleccionada"""
        return webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            directory=os.path.expanduser("~"),
            save_filename=params['save_file'],
            file_types=params['file_types']
        )

    def save_file(self, file_path, base64_data):
        """Guarda el archivo en la ruta especificada"""
        try:
            # Decodificar el base64
            file_data = base64.b64decode(base64_data)
            
            # Escribir el archivo
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            return True
        except Exception as e:
            print(f"Error al guardar archivo: {e}")
            return False

if __name__ == '__main__':
    try:
        # Inicia el servidor Flask en un hilo separado
        print("Iniciando el servidor Flask en http://127.0.0.1:5000...")
        flask_thread = threading.Thread(
            target=lambda: app.run(
                host='127.0.0.1',
                port=5000,
                debug=False,
                use_reloader=False
            )
        )
        flask_thread.daemon = True
        flask_thread.start()

        # Espera un momento para asegurarte de que Flask esté listo
        time.sleep(2)

        # Crear la ventana de la aplicación
        print("Iniciando Pywebview...")
        window = webview.create_window(
            'Inventario GYH',
            'http://127.0.0.1:5000',  # Conecta explícitamente a Flask
            width=1280,
            height=800,
            resizable=True,
            text_select=True,  # Permite seleccionar texto dentro de la webview
            js_api=Api()  # Exponer la API de Python a JavaScript
        )

        # Iniciar pywebview
        # debug=True habilita las herramientas de desarrollador (clic derecho -> Inspeccionar)
        # Cambia a debug=False para la versión final distribuida
        webview.start(debug=False)

        print("Pywebview ha terminado.")
        # El programa terminará aquí cuando la ventana se cierre.

    except NameError as e:
        if "'app' is not defined" in str(e):
            print("Error Crítico: La variable 'app' no se encontró. Revisa la importación desde app.py.")
        else:
            print(f"Error de Nombre: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al iniciar Pywebview: {type(e).__name__} - {e}")
        sys.exit(1)