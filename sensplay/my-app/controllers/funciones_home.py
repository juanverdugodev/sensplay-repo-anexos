# Para subir archivo tipo foto al servidor
from werkzeug.utils import secure_filename
import uuid  # Modulo de python para crear un string

from conexion.conexionBD import connectionBD  # Conexión a BD
from mysql.connector import Error
import datetime
import pytz # Importa el módulo pytz
import re
import os

from os import remove  # Modulo  para remover archivo
from os import path  # Modulo para obtener la ruta o directorio


import openpyxl  # Para generar el excel
# biblioteca o modulo send_file para forzar la descarga
from flask import send_file, session

# Importaciones de Firebase
import firebase_admin
from firebase_admin import credentials, db 
from firebase_admin.exceptions import FirebaseError 

import random
import string
import requests
import json

# --- Variables de configuración de Firebase ---
FIREBASE_SERVICE_ACCOUNT_KEY_PATH_DOCKER = os.path.join('/python-docker', 'my-app', 'secrets', 'sensplay-98778-firebase-adminsdk-fbsvc-1c5db49eb8.json')
FIREBASE_SERVICE_ACCOUNT_KEY_PATH_LOCAL = os.path.join(os.path.dirname(__file__), '..', 'secrets', 'sensplay-98778-firebase-adminsdk-fbsvc-1c5db49eb8.json')
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://sensplay-98778-default-rtdb.firebaseio.com/')

# --- Variable global para rastrear el estado de inicialización de Firebase ---
firebase_initialized_successfully = False
firebase_initialization_error_message = ""

# Inicializar Firebase Admin SDK si no ha sido inicializado
if not firebase_admin._apps:
    try:
        cred = None 
        
        if os.path.exists(FIREBASE_SERVICE_ACCOUNT_KEY_PATH_DOCKER):
            print(f"Inicializando Firebase con archivo en ruta Docker: {FIREBASE_SERVICE_ACCOUNT_KEY_PATH_DOCKER}")
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH_DOCKER)
        elif os.path.exists(FIREBASE_SERVICE_ACCOUNT_KEY_PATH_LOCAL):
            print(f"Inicializando Firebase con archivo local: {FIREBASE_SERVICE_ACCOUNT_KEY_PATH_LOCAL}")
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH_LOCAL)
        elif os.environ.get('FIREBASE_CONFIG_JSON'):
            print("Inicializando Firebase con variable de entorno FIREBASE_CONFIG_JSON...")
            try:
                cred_dict = json.loads(os.environ.get('FIREBASE_CONFIG_JSON'))
                cred = credentials.Certificate(cred_dict)
            except json.JSONDecodeError as e:
                raise ValueError(f"La variable de entorno 'FIREBASE_CONFIG_JSON' no contiene un JSON válido: {e}")
        else:
            raise FileNotFoundError(
                "No se encontró el archivo de credenciales de Firebase en las rutas esperadas "
                "ni la variable de entorno 'FIREBASE_CONFIG_JSON'. "
                "Firebase no se puede inicializar."
            )

        if cred is None: 
            raise ValueError("No se pudo obtener las credenciales para inicializar Firebase.")

        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DATABASE_URL
        })
        print("✅ Firebase Admin SDK inicializado correctamente.")
        firebase_initialized_successfully = True

    except (FileNotFoundError, ValueError) as e:
        firebase_initialization_error_message = f"Credenciales Firebase inválidas o no encontradas: {e}"
        print(f"❌ Error crítico al inicializar Firebase Admin SDK: {firebase_initialization_error_message}")
    except Exception as e:
        firebase_initialization_error_message = f"Error desconocido al inicializar Firebase: {e}"
        print(f"❌ Error crítico al inicializar Firebase Admin SDK: {firebase_initialization_error_message}")


def actualizar_estado_sesion_firebase(estado, paciente_data,id_sesion_actual=None):
    global firebase_initialized_successfully, firebase_initialization_error_message
    
    if not firebase_initialized_successfully:
        raise FirebaseError(f"Firebase no está inicializado. Razón: {firebase_initialization_error_message}")

    try:
        # Apunta a la referencia RAÍZ de la base de datos
        root_ref = db.reference('/') 
        
        if estado == "activo":
            # Si se proporcionó un id_sesion_actual y paciente_data es un diccionario, agrégalo
            if id_sesion_actual is not None and isinstance(paciente_data, dict):
                paciente_data['id_sesion'] = id_sesion_actual
                print(f"Agregado 'id_sesion': {id_sesion_actual} a los datos del paciente para Firebase.")
            
            # Si el estado es activo, se actualizan ambos campos en la raíz
            data_to_update = {
                'estado_sesion': 'activo',
                'paciente': paciente_data, 
            }
            root_ref.update(data_to_update) # .update() actualiza los nodos hijos existentes o los crea si no existen
            print("Estado de sesión actualizado a ACTIVO y paciente en la raíz de Firebase.")
        elif estado == "inactivo":
            # Si el estado es inactivo, se establece estado_sesion y se ELIMINA el nodo paciente
            # Usamos update para el estado_sesion y luego eliminamos el nodo 'paciente'
            root_ref.update({'estado_sesion': 'inactivo'})
            # Borrar el nodo 'paciente' si existe
            paciente_ref = db.reference('/paciente')
            paciente_ref.delete() 
            print("Estado de sesión actualizado a INACTIVO y paciente eliminado de la raíz de Firebase.")
        else:
            raise ValueError("Estado de sesión no reconocido. Debe ser 'activo' o 'inactivo'.")

    except FirebaseError as e:
        print(f"Error de base de datos Firebase: {e}")
        raise FirebaseError(f"Error de base de datos Firebase: {e}") 
    except Exception as e:
        print(f"Error inesperado al interactuar con Firebase: {e}")
        raise Exception(f"Error inesperado al interactuar con Firebase: {e}") 
        
# ---- REGISTRAR SESIÓN EN LA BASE DE DATOS LOCAL DE USA GCP SQL-NUBE---
def registrar_sesion_db(id_paciente, id_usuario):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor() as cursor:
                # 1. Definir la zona horaria de Ecuador (Guayaquil)
                zona_ecuador = pytz.timezone('America/Guayaquil')

                # 2. Obtener la hora actual en la zona horaria de Ecuador
                fecha_inicio_ecuador = datetime.datetime.now(zona_ecuador).strftime('%Y-%m-%d %H:%M:%S')
                
                query = """
                    INSERT INTO sesiones (id_paciente, id_usuario, fecha_inicio)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(query, (id_paciente, id_usuario, fecha_inicio_ecuador))
                conexion_MySQLdb.commit()
                id_sesion_generado = cursor.lastrowid
                print(f"Registro de sesión exitoso en la base de datos local en la nube para paciente ID: {id_paciente}, usuario ID: {id_usuario} y fecha: {fecha_inicio_ecuador}. ID Sesión: {id_sesion_generado}")

                return id_sesion_generado # ¡Retorna el ID generado!
            
    except Exception as e:
        print(f"Error al registrar sesión en la base de datos local: {e}")
        raise Exception(f"Error al registrar sesión en la base de datos local: {e}")




def guardar_clave_en_firebase(clave):
    """Guarda la clave directamente en Firebase usando REST API"""
    url = "https://sensor-ac7c1-default-rtdb.firebaseio.com/Clave_sesion.json"
    data = json.dumps(clave)
    response = requests.put(url, data=data)
    if response.status_code == 200:
        print(f"✅ Clave enviada a Firebase con REST: {clave}")
    else:
        print(f"❌ Error al enviar clave a Firebase: {response.status_code} - {response.text}")

# Ruta absoluta al JSON de credenciales
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(BASE_DIR, 'sensor-ac7c1-firebase-adminsdk-fbsvc-8e8d1bdcc2.json')

# Inicializar Firebase SOLO una vez
if not firebase_admin._apps:
    cred = credentials.Certificate(json_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://sensor-ac7c1-default-rtdb.firebaseio.com/'
    })
    print("✅ Firebase inicializado correctamente")

def generar_clave(longitud=5):
    clave = ''.join(random.choices(string.ascii_letters + string.digits, k=longitud))
    print(f"🔑 Clave generada: {clave}")
    return clave

def guardar_clave_en_firebase(clave):
    try:
        ref = db.reference('/Clave_sesion')
        ref.set(clave)
        print(f"🔥 Clave enviada a Firebase: {clave}")
    except Exception as e:
        print(f"❌ Error enviando a Firebase: {e}")



def accesosReporte():
    if session['rol'] == 1 :
        try:
            with connectionBD() as conexion_MYSQLdb:
                with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                    querySQL = ("""
                        SELECT a.id_acceso, u.cedula, a.fecha, r.nombre_area, a.clave 
                        FROM accesos a 
                        JOIN usuarios u 
                        JOIN area r
                        WHERE u.id_area = r.id_area AND u.id_usuario = a.id_usuario
                        ORDER BY u.cedula, a.fecha DESC
                                """) 
                    cursor.execute(querySQL)
                    accesosBD=cursor.fetchall()
                return accesosBD
        except Exception as e:
            print(
                f"Errro en la función accesosReporte: {e}")
            return None
    else:
        cedula = session['cedula']
        try:
            with connectionBD() as conexion_MYSQLdb:
                with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                    querySQL = ("""
                        SELECT 
                            a.id_acceso, 
                            u.cedula, 
                            a.fecha,
                            r.nombre_area, 
                            a.clave 
                            FROM accesos a 
                            JOIN usuarios u JOIN area r 
                            WHERE u.id_usuario = a.id_usuario AND u.id_area = r.id_area AND u.cedula = %s
                            ORDER BY u.cedula, a.fecha DESC
                                """) 
                    cursor.execute(querySQL,(cedula,))
                    accesosBD=cursor.fetchall()
                return accesosBD
        except Exception as e:
            print(
                f"Errro en la función accesosReporte: {e}")
            return None


def generarReporteExcel():
    dataAccesos = accesosReporte()
    wb = openpyxl.Workbook()
    hoja = wb.active

    # Agregar la fila de encabezado con los títulos
    cabeceraExcel = ("ID", "CEDULA", "FECHA", "ÁREA", "CLAVE GENERADA")
    hoja.append(cabeceraExcel)

    # Agregar los registros a la hoja
    for registro in dataAccesos:
        hoja.append((
            registro['id_acceso'],
            registro['cedula'],
            registro['fecha'],
            registro['nombre_area'],
            registro['clave']
        ))

    fecha_actual = datetime.datetime.now()
    archivoExcel = f"Reporte_accesos_{session['cedula']}_{fecha_actual.strftime('%Y_%m_%d')}.xlsx"
    carpeta_descarga = "../static/downloads-excel"
    ruta_descarga = os.path.join(os.path.dirname(os.path.abspath(__file__)), carpeta_descarga)

    if not os.path.exists(ruta_descarga):
        os.makedirs(ruta_descarga)
        os.chmod(ruta_descarga, 0o755)

    ruta_archivo = os.path.join(ruta_descarga, archivoExcel)
    wb.save(ruta_archivo)
    print(f"✅ Reporte generado en: {ruta_archivo}")

    return ruta_archivo

def obtener_sesiones_por_cedula_y_fecha(cedula, fecha_str):
    """
    Consulta las sesiones de un paciente por su cédula y una fecha específica.
    Incluye detalles de la sesión, el paciente y el terapeuta.

    Args:
        cedula (str): La cédula del paciente.
        fecha_str (str): La fecha en formato 'YYYY-MM-DD' (ej. '2025-07-17').

    Returns:
        dict: Un diccionario con los resultados de la consulta.
              Cada sesión en la lista 'sesiones' contendrá los detalles necesarios.
              Ej: {
                  "registros": True,
                  "sesiones": [
                      {
                          "id_sesion": 1,
                          "fecha_inicio": "2025-07-17 09:00:00",
                          "fecha_fin": "2025-07-17 10:00:00",
                          "terapeuta": "Nombre Apellido Terapeuta",
                          "paciente_nombre": "Juan",
                          "paciente_apellido": "Pérez",
                          "paciente_edad": 30, # Incluido para el encabezado del HTML
                          "paciente_genero": "Masculino", # Incluido para el encabezado del HTML
                          "estado": "Finalizada"
                      },
                      ...
                  ]
              }
              Ej: {"registros": False, "mensaje": "Paciente no encontrado."}
    """
    conn = None
    try:
        conn = connectionBD()
        cursor = conn.cursor(dictionary=True)

        # Paso 1: Obtener el id_paciente para asegurar que la cédula existe
        # Asume que la tabla de pacientes se llama 'pacientes' (plural)
        query_paciente_id = "SELECT id_paciente FROM pacientes WHERE cedula = %s"
        cursor.execute(query_paciente_id, (cedula,))
        paciente_id_result = cursor.fetchone()

        if not paciente_id_result:
            return {"registros": False, "mensaje": "Paciente no encontrado."}

        id_paciente = paciente_id_result['id_paciente']

        # Paso 2: Consultar las sesiones, uniendo con pacientes, genero y usuarios
        # para obtener todos los detalles requeridos en una sola consulta.
        query_sesiones = """
        SELECT
            s.id_sesion,
            s.fecha_inicio,
            s.fecha_fin,
            CONCAT(u.nombre_usuario, ' ', u.apellido_usuario) AS terapeuta,
            p.nombres AS paciente_nombre,
            p.apellidos AS paciente_apellido,
            p.edad AS paciente_edad,
            g.tipo_genero AS paciente_genero,
            IF(s.fecha_fin IS NULL, 'Activa', 'Finalizada') AS estado
        FROM
            sesiones s
        INNER JOIN
            pacientes p ON s.id_paciente = p.id_paciente
        INNER JOIN
            genero g ON p.id_genero = g.id_genero
        INNER JOIN
            usuarios u ON s.id_usuario = u.id_usuario
        WHERE
            s.id_paciente = %s AND DATE(s.fecha_fin) = %s
        ORDER BY
            s.fecha_inicio DESC
        """
        
        cursor.execute(query_sesiones, (id_paciente, fecha_str))
        sesiones = cursor.fetchall()

        if sesiones:
            return {
                "registros": True,
                "sesiones": sesiones # Cada elemento de la lista ya contiene todos los detalles
            }
        else:
            return {
                "registros": False,
                "mensaje": "No se encontraron sesiones para esta fecha."
            }

    except Error as e:
        print(f"❌ Error de base de datos MySQL en obtener_sesiones_por_cedula_y_fecha: {e}")
        return {"registros": False, "mensaje": f"Error en la base de datos al consultar sesiones: {e}"}
    except Exception as e:
        print(f"❌ Error inesperado en obtener_sesiones_por_cedula_y_fecha: {e}")
        return {"registros": False, "mensaje": f"Ocurrió un error inesperado: {e}"}
    finally:
        if conn:
            conn.close()


# --------------------- Método de Gráficas de Salto ----------------------
def obtener_datos_salto_por_sesion(sesion_id):
    """
    Consulta y clasifica los saltos del trampolín, obtiene presión del balón
    y calcula tiempo de uso de ambos dispositivos.
    """
    # Inicializar datos
    trampolin_counts = [0, 0, 0]  # Muy leve, Normal, Brusco
    balon_presion = [0, 0, 0, 0, 0, 0]  # S1-S6
    tiempo_trampolin = 0  # en minutos
    tiempo_balon = 0  # en minutos

    # Rangos de clasificación de saltos
    RANGO_MUY_LEVE = (10.0, 11.0)
    RANGO_NORMAL = (8.0, 9.0)
    RANGO_BRUSCO = (5.0, 7.0)

    try:
        with connectionBD() as conexion:
            with conexion.cursor(dictionary=True) as cursor:
                # === Clasificar saltos (log_trampolin) ===
                cursor.execute("""
                    SELECT sensor, fecha_registro
                    FROM log_trampolin
                    WHERE id_sesion = %s
                    ORDER BY fecha_registro ASC;
                """, (sesion_id,))
                trampolin_logs = cursor.fetchall()

                for log in trampolin_logs:
                    profundidad = float(log['sensor'])
                    if RANGO_MUY_LEVE[0] <= profundidad <= RANGO_MUY_LEVE[1]:
                        trampolin_counts[0] += 1
                    elif RANGO_NORMAL[0] <= profundidad <= RANGO_NORMAL[1]:
                        trampolin_counts[1] += 1
                    elif RANGO_BRUSCO[0] <= profundidad <= RANGO_BRUSCO[1]:
                        trampolin_counts[2] += 1

                if trampolin_logs:
                    inicio_trampolin = trampolin_logs[0]['fecha_registro']
                    fin_trampolin = trampolin_logs[-1]['fecha_registro']
                    tiempo_trampolin = (fin_trampolin - inicio_trampolin).total_seconds() / 60

                # === Datos del balón (sensor_balon) ===
                cursor.execute("""
                    SELECT S1, S2, S3, S4, S5, S6
                    FROM sensor_balon
                    WHERE id_sesion = %s;
                """, (sesion_id,))
                row_balon = cursor.fetchone()
                if row_balon:
                    balon_presion = [float(row_balon[k]) if row_balon[k] else 0 for k in row_balon]

                # === Tiempo de uso del balón (log_balon) ===
                cursor.execute("""
                    SELECT fecha_registro
                    FROM log_balon
                    WHERE id_sesion = %s
                    ORDER BY fecha_registro ASC;
                """, (sesion_id,))
                balon_logs = cursor.fetchall()

                if balon_logs:
                    inicio_balon = balon_logs[0]['fecha_registro']
                    fin_balon = balon_logs[-1]['fecha_registro']
                    tiempo_balon = (fin_balon - inicio_balon).total_seconds() / 60

    except Exception as e:
        print(f"❌ Error en obtener_datos_salto_por_sesion: {e}")
        return {
            'trampolin': [0, 0, 0],
            'balon': [0, 0, 0, 0, 0, 0],
            'tiempo_trampolin': 0,
            'tiempo_balon': 0
        }

    return {
        'trampolin': trampolin_counts,
        'balon': balon_presion,
        'tiempo_trampolin': round(tiempo_trampolin, 2),
        'tiempo_balon': round(tiempo_balon, 2)
    }





# --- Funciones de tu base de datos local (ej. MySQL) ---
def obtener_paciente_por_cedula(cedula):
    try:
        with connectionBD() as conexion:
            with conexion.cursor(dictionary=True) as cursor:
                query = """
                    SELECT p.id_paciente, p.cedula, p.nombres, p.apellidos, p.edad, g.tipo_genero AS genero
                    FROM pacientes p
                    INNER JOIN genero g ON p.id_genero = g.id_genero
                    WHERE p.cedula = %s
                """
                cursor.execute(query, (cedula,))
                paciente = cursor.fetchone() # Obtener el resultado
                return paciente # <--- Simplemente devuelve el diccionario completo.
                                #     Si la consulta es 'dictionary=True', ya incluirá 'cedula'.
    except Exception as e:
        print(f"❌ Error al buscar paciente por cédula en BD local: {e}")
        return None


# Lista de Pacientes
def lista_pacientesBD():
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = """
                    SELECT p.id_paciente, p.cedula, p.nombres, p.apellidos, p.edad, g.tipo_genero
                    FROM pacientes p
                    INNER JOIN genero g ON p.id_genero = g.id_genero
                """
                cursor.execute(querySQL)
                pacientesBD = cursor.fetchall()
        return pacientesBD
    except Exception as e:
        print(f"Error en lista_pacientesBD : {e}")
        return []

def eliminar_pacienteBD(id_paciente):
    try:
        with connectionBD() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("DELETE FROM pacientes WHERE id_paciente = %s", (id_paciente,))
                conexion.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar paciente: {e}")
        return False


def buscarAreaBD(search):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as mycursor:
                querySQL = ("""
                        SELECT 
                            a.id_area,
                            a.nombre_area
                        FROM area AS a
                        WHERE a.nombre_area LIKE %s 
                        ORDER BY a.id_area DESC
                    """)
                search_pattern = f"%{search}%"  # Agregar "%" alrededor del término de búsqueda
                mycursor.execute(querySQL, (search_pattern,))
                resultado_busqueda = mycursor.fetchall()
                return resultado_busqueda

    except Exception as e:
        print(f"Ocurrió un error en def buscarEmpleadoBD: {e}")
        return []


# Lista de Usuarios creados
def lista_usuariosBD():
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT id_usuario, cedula, nombre_usuario, apellido_usuario, id_area, id_rol FROM usuarios"
                cursor.execute(querySQL,)
                usuariosBD = cursor.fetchall()
        return usuariosBD
    except Exception as e:
        print(f"Error en lista_usuariosBD : {e}")
        return []

def lista_areasBD():
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT id_area, nombre_area FROM area"
                cursor.execute(querySQL,)
                areasBD = cursor.fetchall()
        return areasBD
    except Exception as e:
        print(f"Error en lista_areas : {e}")
        return []

# Eliminar usuario
# Eliminar usuario
def eliminarUsuario(id):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = "DELETE FROM usuarios WHERE id_usuario=%s"
                cursor.execute(querySQL, (id,))
                conexion_MySQLdb.commit()
                return cursor.rowcount > 0
    except Exception as e:
        print(f"Error en eliminarUsuario : {e}")
        return False


def eliminarArea(id):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as cursor:
                querySQL = "DELETE FROM area WHERE id_area=%s"
                cursor.execute(querySQL, (id,))
                conexion_MySQLdb.commit()
                resultado_eliminar = cursor.rowcount
        return resultado_eliminar
    except Exception as e:
        print(f"Error en eliminarArea : {e}")
        return []
    
def dataReportes():
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                querySQL = """
                SELECT a.id_acceso, u.cedula, a.fecha, r.nombre_area, a.clave 
                FROM accesos a 
                JOIN usuarios u 
                JOIN area r
                WHERE u.id_area = r.id_area AND u.id_usuario = a.id_usuario
                ORDER BY u.cedula, a.fecha DESC
                """
                cursor.execute(querySQL)
                reportes = cursor.fetchall()
        return reportes
    except Exception as e:
        print(f"Error en listaAccesos : {e}")
        return []

def lastAccessBD(id):
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT a.id_acceso, u.cedula, a.fecha, a.clave FROM accesos a JOIN usuarios u WHERE u.id_usuario = a.id_usuario AND u.cedula=%s ORDER BY a.fecha DESC LIMIT 1"
                cursor.execute(querySQL,(id,))
                reportes = cursor.fetchone()
                print(reportes)
        return reportes
    except Exception as e:
        print(f"Error en lastAcceso : {e}")
        return []
import random
import string
def crearClave():
    caracteres = string.ascii_letters + string.digits  # Letras mayúsculas, minúsculas y dígitos
    longitud = 6  # Longitud de la clave

    clave = ''.join(random.choice(caracteres) for _ in range(longitud))
    print("La clave generada es:", clave)
    return clave

    
def lista_rolesBD():
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                querySQL = "SELECT * FROM rol"
                cursor.execute(querySQL)
                roles = cursor.fetchall()
                return roles
    except Exception as e:
        print(f"Error en select roles : {e}")
        return []
##CREAR AREA
def guardarArea(area_name):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as mycursor:
                    sql = "INSERT INTO area (nombre_area) VALUES (%s)"
                    valores = (area_name,)
                    mycursor.execute(sql, valores)
                    conexion_MySQLdb.commit()
                    resultado_insert = mycursor.rowcount
                    return resultado_insert 
        
    except Exception as e:
        return f'Se produjo un error en crear Area: {str(e)}' 
    
##ACTUALIZAR AREA
def actualizarArea(area_id, area_name):
    try:
        with connectionBD() as conexion_MySQLdb:
            with conexion_MySQLdb.cursor(dictionary=True) as mycursor:
                sql = """UPDATE area SET nombre_area = %s WHERE id_area = %s"""
                valores = (area_name, area_id)
                mycursor.execute(sql, valores)
                conexion_MySQLdb.commit()
                resultado_update = mycursor.rowcount
                return resultado_update 
        
    except Exception as e:
        return f'Se produjo un error al actualizar el área: {str(e)}'
    
    #--------consulta de datos de los roles-----------:

    
#--------------------- metodo de graficas ----------------------
def obtenerroles():
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                query = """
                    SELECT r.nombre_rol
                    FROM rol r
                    ORDER BY r.nombre_rol ASC
                """
                cursor.execute(query)
                roles = cursor.fetchall()
        return roles
    except Exception as e:
        print(f"Error en obtenerroles: {e}")
        return []
    
#------------------------ area de graficas -----------------------
def obtener_areas():
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                query = """
                    SELECT nombre_area, numero_personas
                    FROM area
                    ORDER BY nombre_area ASC
                """
                cursor.execute(query)
                areas = cursor.fetchall()
        return areas
    except Exception as e:
        print(f"Error en obtener_areas: {e}")
        return []
    #------------------------ entrada de accesos --------------------------
def obtener_accesos_por_fecha(fecha_inicio, fecha_fin):
    try:
        with connectionBD() as conexion_MYSQLdb:
            with conexion_MYSQLdb.cursor(dictionary=True) as cursor:
                query = """
                    SELECT clave, COUNT(id_acceso) AS cantidad
                    FROM accesos
                    WHERE fecha BETWEEN %s AND %s
                    GROUP BY clave
                    ORDER BY clave ASC
                """
                cursor.execute(query, (fecha_inicio, fecha_fin))
                accesos = cursor.fetchall()
        return accesos
    except Exception as e:
        print(f"Error en obtener_accesos_por_fecha: {e}")
        return []

    #------------------------ formulario pacientes --------------------------
def guardarPacienteBD(cedula, nombres, apellidos, edad, id_genero):
    try:
        with connectionBD() as conexion:
            with conexion.cursor() as cursor:
                # Verificar si la cédula ya existe
                cursor.execute("SELECT COUNT(*) FROM pacientes WHERE cedula = %s", (cedula,))
                if cursor.fetchone()[0] > 0:
                    return "duplicado"  # Cédula ya existe

                # Insertar nuevo paciente
                cursor.execute("""
                    INSERT INTO pacientes (cedula, nombres, apellidos, edad, id_genero)
                    VALUES (%s, %s, %s, %s, %s)
                """, (cedula, nombres, apellidos, edad, id_genero))
                conexion.commit()
                return "ok"
    except Exception as e:
        print("❌ Error al guardar paciente en BD:", e)
        return "error"



def obtenerGeneros():
    try:
        with connectionBD() as conexion:
            with conexion.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT id_genero, tipo_genero FROM genero")
                return cursor.fetchall()
    except Exception as e:
        print("❌ Error al obtener géneros:", e)
        return []
