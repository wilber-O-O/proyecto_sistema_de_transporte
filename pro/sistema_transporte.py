"""
====================================================================
  SISTEMA DE TRANSPORTE PÚBLICO
  Menú de consola interactivo
  Requiere: install mysql-connector-python
====================================================================
"""
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime
from decimal import Decimal
import os
import sys
from dotenv import load_dotenv 


load_dotenv()

CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset":  "utf8mb4",
}


#  UTILIDADES DE CONSOLA


LINEA  = "=" * 58
LINEA2 = "-" * 58

def limpiar():
    os.system("cls" if os.name == "nt" else "clear")

def pausar():
    input("\n  Presiona ENTER para continuar...")

def titulo(texto):
    print(f"\n{LINEA}")
    print(f"  {texto}")
    print(LINEA)

def subtitulo(texto):
    print(f"\n{LINEA2}")
    print(f"  {texto}")
    print(LINEA2)

def ok(msg):    print(f"\n  [✓] {msg}")
def error(msg): print(f"\n  [✗] {msg}")
def info(msg):  print(f"\n  [i] {msg}")

def pedir(prompt, requerido=True):
    while True:
        val = input(f"  {prompt}: ").strip()
        if val or not requerido:
            return val
        print("  Este campo es obligatorio.")

def pedir_int(prompt, requerido=True):
    while True:
        val = pedir(prompt, requerido)
        if not val and not requerido:
            return None
        try:
            return int(val)
        except ValueError:
            print("  Ingresa un número entero válido.")

def pedir_float(prompt, requerido=True):
    while True:
        val = pedir(prompt, requerido)
        if not val and not requerido:
            return None
        try:
            v = float(val)
            if v <= 0:
                print("  El valor debe ser mayor a 0.")
                continue
            return v
        except ValueError:
            print("  Ingresa un número válido (ej: 25.50).")

def pedir_fecha(prompt):
    while True:
        val = pedir(f"{prompt} (AAAA-MM-DD, ENTER=hoy)", requerido=False)
        if not val:
            return date.today()
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            print("  Formato incorrecto. Usa AAAA-MM-DD.")

def elegir(opciones: list[str]) -> str:
    for i, op in enumerate(opciones, 1):
        print(f"  [{i}] {op}")
    while True:
        sel = pedir("Elige una opción")
        if sel.isdigit() and 1 <= int(sel) <= len(opciones):
            return opciones[int(sel) - 1]
        print("  Opción no válida.")

def tabla(filas: list[dict], columnas: list[tuple]):
    if not filas:
        info("Sin resultados.")
        return
    # Encabezado
    header = "  "
    sep    = "  "
    for clave, enc, ancho in columnas:
        header += f"{enc:<{ancho}}  "
        sep    += "-" * ancho + "  "
    print(f"\n{sep}")
    print(header)
    print(sep)
    for fila in filas:
        linea = "  "
        for clave, _, ancho in columnas:
            val = str(fila.get(clave, "")).replace("\n", " ")
            linea += f"{val:<{ancho}}  "
        print(linea)
    print(sep)
    print(f"  Total: {len(filas)} registro(s)")


#  CONEXIÓN


def conectar():
    try:
        return mysql.connector.connect(**CONFIG)
    except Error as e:
        error(f"No se pudo conectar a MySQL: {e}")
        return None


#  MÓDULO: USUARIO


def _crear_usuario(nombre, contrasena, correo, numero_tel, direccion):
    sql = """INSERT INTO USUARIO (NOMBRE,CONTRASENA,CORREO,NUMERO_TEL,DIRECCION)
             VALUES (%s,SHA2(%s,256),%s,%s,%s)"""
    conn = conectar()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute(sql, (nombre, contrasena, correo, numero_tel, direccion))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        error(f"crear_usuario: {e}"); conn.rollback(); return None
    finally: cur.close(); conn.close()

def _listar_usuarios():
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT ID_USUARIO,NOMBRE,CORREO,NUMERO_TEL FROM USUARIO ORDER BY NOMBRE")
        return cur.fetchall()
    except Error as e:
        error(f"listar_usuarios: {e}"); return []
    finally: cur.close(); conn.close()

def _obtener_usuario(id_u):
    conn = conectar()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM USUARIO WHERE ID_USUARIO=%s", (id_u,))
        return cur.fetchone()
    except Error as e:
        error(f"obtener_usuario: {e}"); return None
    finally: cur.close(); conn.close()


#  MÓDULO: TARJETA

def _crear_tarjeta(id_usuario, saldo, limite):
    conn = conectar()
    if not conn: 
        return None
    try:
        cur = conn.cursor()
        # Consulta limpia para MySQL (sin RETURNING)
        query = "INSERT INTO TARJETA(SALDO, ESTADO, LIMITE_DIARIO, ID_USUARIO) VALUES(%s, 'ACTIVA', %s, %s)"
        cur.execute(query, (saldo, limite, id_usuario))
        
        # Guardamos el ID que generó MySQL antes del commit
        id_tarjeta = cur.lastrowid  
        
        conn.commit()
        return id_tarjeta  # Esto te devuelve el ID de la tarjeta
        
    except Error as e:
        error(f"crear_tarjeta: {e}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

def _consultar_tarjeta(id_tar):
    conn = conectar()
    if not conn: return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT t.*, u.NOMBRE AS PROPIETARIO
            FROM TARJETA t JOIN USUARIO u ON t.ID_USUARIO=u.ID_USUARIO
            WHERE t.ID_TARJETA=%s""", (id_tar,))
        return cur.fetchone()
    except Error as e:
        error(f"consultar_tarjeta: {e}"); return None
    finally: cur.close(); conn.close()

def _cambiar_estado_tarjeta(id_tar, estado):
    conn = conectar()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE TARJETA SET ESTADO=%s WHERE ID_TARJETA=%s", (estado, id_tar))
        conn.commit(); return cur.rowcount > 0
    except Error as e:
        error(f"cambiar_estado: {e}"); conn.rollback(); return False
    finally: cur.close(); conn.close()

def _tarjetas_de_usuario(id_u):
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT ID_TARJETA,SALDO,ESTADO,LIMITE_DIARIO FROM TARJETA WHERE ID_USUARIO=%s", (id_u,))
        return cur.fetchall()
    except Error as e:
        error(f"tarjetas_usuario: {e}"); return []
    finally: cur.close(); conn.close()


#  MÓDULO: RECARGA


def _recargar(id_tar, monto, tipo_pago, id_canal):
    conn = conectar()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT ESTADO FROM TARJETA WHERE ID_TARJETA=%s", (id_tar,))
        row = cur.fetchone()
        if not row:
            error("Tarjeta no existe."); return False
        if row[0] != "ACTIVA":
            error(f"Tarjeta {row[0]}. No se puede recargar."); return False
        cur.execute(
            "INSERT INTO RECARGA(MONTO,TIPO_DE_PAGO,ID_CANAL,ID_TARJETA) VALUES(%s,%s,%s,%s)",
            (monto, tipo_pago, id_canal, id_tar))
        cur.execute("UPDATE TARJETA SET SALDO=SALDO+%s WHERE ID_TARJETA=%s", (monto, id_tar))
        conn.commit(); return True
    except Error as e:
        error(f"recargar: {e}"); conn.rollback(); return False
    finally: cur.close(); conn.close()


#  MÓDULO: VALIDACIÓN / COBRO


def _registrar_cobro(id_tar, id_lector, monto):
    ahora = datetime.now()
    conn = conectar()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT SALDO,ESTADO FROM TARJETA WHERE ID_TARJETA=%s FOR UPDATE", (id_tar,))
        row = cur.fetchone()
        if not row:
            error("Tarjeta no existe."); return False
        saldo, estado = row
        if estado != "ACTIVA":
            error(f"Tarjeta {estado}."); return False
        if float(saldo) < monto:
            error(f"Saldo insuficiente (Bs {saldo}). Se requieren Bs {monto:.2f}."); return False
        cur.execute(
            "INSERT INTO VALIDACION(ID_TARJETA,ID_LECTOR,FECHA,HORA,MONTO_COBRADO) VALUES(%s,%s,%s,%s,%s)",
            (id_tar, id_lector, ahora.date(), ahora.time(), monto))
        cur.execute("UPDATE TARJETA SET SALDO=SALDO-%s WHERE ID_TARJETA=%s", (monto, id_tar))
        conn.commit(); return True
    except Error as e:
        error(f"registrar_cobro: {e}"); conn.rollback(); return False
    finally: cur.close(); conn.close()

def _historial_cobros(id_tar):
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT v.ID_COBRO,v.FECHA,v.HORA,v.MONTO_COBRADO,a.RUTA_LINEA
            FROM VALIDACION v
            JOIN LECTOR_DE_TARJETA l ON v.ID_LECTOR=l.ID_LECTOR
            JOIN AUTOBUS a ON l.ID_AUTOBUS=a.ID_AUTOBUS
            WHERE v.ID_TARJETA=%s ORDER BY v.FECHA DESC,v.HORA DESC""", (id_tar,))
        return cur.fetchall()
    except Error as e:
        error(f"historial_cobros: {e}"); return []
    finally: cur.close(); conn.close()


#  MÓDULO: AUTOBÚS


def _registrar_bus(ruta, soat, revision):
    conn = conectar()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO AUTOBUS(RUTA_LINEA,SOAT,REVISION_TECNICA) VALUES(%s,%s,%s)",
                    (ruta, soat, revision))
        conn.commit(); return cur.lastrowid
    except Error as e:
        error(f"registrar_bus: {e}"); conn.rollback(); return None
    finally: cur.close(); conn.close()

def _listar_buses():
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT ID_AUTOBUS,RUTA_LINEA,SOAT,REVISION_TECNICA FROM AUTOBUS ORDER BY RUTA_LINEA")
        return cur.fetchall()
    except Error as e:
        error(f"listar_buses: {e}"); return []
    finally: cur.close(); conn.close()

def _agregar_lector(id_bus):
    conn = conectar()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO LECTOR_DE_TARJETA(ID_AUTOBUS) VALUES(%s)", (id_bus,))
        conn.commit(); return cur.lastrowid
    except Error as e:
        error(f"agregar_lector: {e}"); conn.rollback(); return None
    finally: cur.close(); conn.close()

def _listar_lectores():
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT l.ID_LECTOR,a.RUTA_LINEA,a.ID_AUTOBUS
                       FROM LECTOR_DE_TARJETA l JOIN AUTOBUS a ON l.ID_AUTOBUS=a.ID_AUTOBUS
                       ORDER BY a.RUTA_LINEA""")
        return cur.fetchall()
    except Error as e:
        error(f"listar_lectores: {e}"); return []
    finally: cur.close(); conn.close()


#  MÓDULO: CHOFER


def _registrar_chofer(ci, nombre, id_interno, numero, direccion, licencia):
    conn = conectar()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO CHOFER(CI_CHOFER,ID_INTERNO,NOMBRE,NUMERO,DIRECCION,LICENCIA_DE_CONDUCIR)
                       VALUES(%s,%s,%s,%s,%s,%s)""",
                    (ci, id_interno, nombre, numero, direccion, licencia))
        conn.commit(); return True
    except Error as e:
        error(f"registrar_chofer: {e}"); conn.rollback(); return False
    finally: cur.close(); conn.close()

def _listar_choferes():
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT CI_CHOFER,NOMBRE,NUMERO,LICENCIA_DE_CONDUCIR FROM CHOFER ORDER BY NOMBRE")
        return cur.fetchall()
    except Error as e:
        error(f"listar_choferes: {e}"); return []
    finally: cur.close(); conn.close()

def _asignar_turno(ci, id_bus, fecha):
    conn = conectar()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO MANEJA(CI_CHOFER,ID_AUTOBUS,FECHA_TURNO) VALUES(%s,%s,%s)
                       ON DUPLICATE KEY UPDATE FECHA_TURNO=VALUES(FECHA_TURNO)""",
                    (ci, id_bus, fecha))
        conn.commit(); return True
    except Error as e:
        error(f"asignar_turno: {e}"); conn.rollback(); return False
    finally: cur.close(); conn.close()

def _turnos_del_dia(fecha):
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT a.ID_AUTOBUS,a.RUTA_LINEA,c.NOMBRE AS CHOFER,c.CI_CHOFER
                       FROM MANEJA m
                       JOIN AUTOBUS a ON m.ID_AUTOBUS=a.ID_AUTOBUS
                       JOIN CHOFER  c ON m.CI_CHOFER=c.CI_CHOFER
                       WHERE m.FECHA_TURNO=%s ORDER BY a.RUTA_LINEA""", (fecha,))
        return cur.fetchall()
    except Error as e:
        error(f"turnos_del_dia: {e}"); return []
    finally: cur.close(); conn.close()


#  MÓDULO: REPORTES


def _rep_recaudacion(fecha):
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT a.ID_AUTOBUS,a.RUTA_LINEA,
                   COUNT(v.ID_COBRO) AS VIAJES,
                   SUM(v.MONTO_COBRADO) AS RECAUDACION
            FROM VALIDACION v
            JOIN LECTOR_DE_TARJETA l ON v.ID_LECTOR=l.ID_LECTOR
            JOIN AUTOBUS a ON l.ID_AUTOBUS=a.ID_AUTOBUS
            WHERE v.FECHA=%s
            GROUP BY a.ID_AUTOBUS,a.RUTA_LINEA ORDER BY RECAUDACION DESC""", (fecha,))
        return cur.fetchall()
    except Error as e:
        error(f"rep_recaudacion: {e}"); return []
    finally: cur.close(); conn.close()

def _rep_recargas_canal():
    conn = conectar()
    if not conn: return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT CASE WHEN pa.ID_LOCAL IS NOT NULL THEN 'Punto Autorizado'
                        WHEN ap.ID_APP   IS NOT NULL THEN 'Aplicación Oficial'
                        ELSE 'Otro' END AS TIPO_CANAL,
                   COUNT(r.ID_RECARGA) AS CANTIDAD,
                   SUM(r.MONTO)        AS MONTO_TOTAL
            FROM RECARGA r
            JOIN CANAL c ON r.ID_CANAL=c.ID_CANAL
            LEFT JOIN PUNTO_AUTORIZADO  pa ON pa.ID_CANAL=c.ID_CANAL
            LEFT JOIN APLICACION_OFICIAL ap ON ap.ID_CANAL=c.ID_CANAL
            GROUP BY TIPO_CANAL""")
        return cur.fetchall()
    except Error as e:
        error(f"rep_recargas: {e}"); return []
    finally: cur.close(); conn.close()


#  PANTALLAS DEL MENÚ


# ── USUARIOS ──────────────────────────────────────────────────────

def pantalla_usuarios():
    while True:
        limpiar()
        titulo("GESTIÓN DE USUARIOS")
        print("  [1] Registrar nuevo usuario")
        print("  [2] Listar todos los usuarios")
        print("  [3] Ver detalle de usuario")
        print("  [4] Ver tarjetas de un usuario")
        print("  [0] Volver al menú principal")
        op = pedir("Opción")

        if op == "1":
            subtitulo("Nuevo usuario")
            nombre  = pedir("Nombre completo")
            correo  = pedir("Correo electrónico")
            contra  = pedir("Contraseña")
            tel     = pedir("Teléfono (opcional)", requerido=False)
            direc   = pedir("Dirección (opcional)", requerido=False)
            id_u = _crear_usuario(nombre, contra, correo, tel, direc)
            if id_u:
                ok(f"Usuario creado con ID = {id_u}")
            pausar()

        elif op == "2":
            subtitulo("Lista de usuarios")
            tabla(_listar_usuarios(), [
                ("ID_USUARIO", "ID",      4),
                ("NOMBRE",     "Nombre", 25),
                ("CORREO",     "Correo", 28),
                ("NUMERO_TEL", "Teléfono", 12),
            ])
            pausar()

        elif op == "3":
            subtitulo("Detalle de usuario")
            id_u = pedir_int("ID del usuario")
            u = _obtener_usuario(id_u)
            if u:
                print(f"\n  ID        : {u['ID_USUARIO']}")
                print(f"  Nombre    : {u['NOMBRE']}")
                print(f"  Correo    : {u['CORREO']}")
                print(f"  Teléfono  : {u.get('NUMERO_TEL','—')}")
                print(f"  Dirección : {u.get('DIRECCION','—')}")
            else:
                error("Usuario no encontrado.")
            pausar()

        elif op == "4":
            subtitulo("Tarjetas del usuario")
            id_u = pedir_int("ID del usuario")
            tabla(_tarjetas_de_usuario(id_u), [
                ("ID_TARJETA",   "ID Tarjeta", 10),
                ("SALDO",        "Saldo (Bs)", 12),
                ("ESTADO",       "Estado",     12),
                ("LIMITE_DIARIO","Límite/día", 12),
            ])
            pausar()

        elif op == "0":
            break

# ── TARJETAS ──────────────────────────────────────────────────────

def pantalla_tarjetas():
    while True:
        limpiar()
        titulo("GESTIÓN DE TARJETAS")
        print("  [1] Crear nueva tarjeta")
        print("  [2] Consultar tarjeta")
        print("  [3] Recargar tarjeta")
        print("  [4] Bloquear tarjeta")
        print("  [5] Activar tarjeta")
        print("  [6] Ver historial de cobros")
        print("  [0] Volver al menú principal")
        op = pedir("Opción")

        if op == "1":
            subtitulo("Nueva tarjeta")
            id_u   = pedir_int("ID del usuario propietario")
            saldo  = pedir_float("Saldo inicial (Bs)")
            limite = pedir_float("Límite diario (Bs)")
            id_t = _crear_tarjeta(id_u, saldo, limite)
            if id_t:
                ok(f"Tarjeta creada con ID = {id_t}")
            pausar()

        elif op == "2":
            subtitulo("Consultar tarjeta")
            id_t = pedir_int("ID de tarjeta")
            t = _consultar_tarjeta(id_t)
            if t:
                print(f"\n  ID Tarjeta  : {t['ID_TARJETA']}")
                print(f"  Propietario : {t['PROPIETARIO']}")
                print(f"  Saldo       : Bs {t['SALDO']}")
                print(f"  Estado      : {t['ESTADO']}")
                print(f"  Límite/día  : Bs {t['LIMITE_DIARIO']}")
            else:
                error("Tarjeta no encontrada.")
            pausar()

        elif op == "3":
            subtitulo("Recargar tarjeta")
            id_t  = pedir_int("ID de tarjeta")
            monto = pedir_float("Monto a recargar (Bs)")
            print("\n  Tipo de pago:")
            tipo  = elegir(["EFECTIVO", "QR", "TRANSFERENCIA", "TARJETA_DEBITO"])
            id_c  = pedir_int("ID del canal (1=Punto Autorizado, 2=App)")
            if _recargar(id_t, monto, tipo, id_c):
                ok(f"Recarga de Bs {monto:.2f} aplicada correctamente.")
            pausar()

        elif op == "4":
            subtitulo("Bloquear tarjeta")
            id_t = pedir_int("ID de tarjeta")
            if _cambiar_estado_tarjeta(id_t, "BLOQUEADA"):
                ok("Tarjeta bloqueada.")
            else:
                error("No se pudo bloquear.")
            pausar()

        elif op == "5":
            subtitulo("Activar tarjeta")
            id_t = pedir_int("ID de tarjeta")
            if _cambiar_estado_tarjeta(id_t, "ACTIVA"):
                ok("Tarjeta activada.")
            else:
                error("No se pudo activar.")
            pausar()

        elif op == "6":
            subtitulo("Historial de cobros")
            id_t = pedir_int("ID de tarjeta")
            tabla(_historial_cobros(id_t), [
                ("ID_COBRO",      "Cobro",     6),
                ("FECHA",         "Fecha",    12),
                ("HORA",          "Hora",     10),
                ("RUTA_LINEA",    "Ruta",     22),
                ("MONTO_COBRADO", "Monto(Bs)", 10),
            ])
            pausar()

        elif op == "0":
            break

# ── COBROS ────────────────────────────────────────────────────────

def pantalla_cobros():
    while True:
        limpiar()
        titulo("COBRO / VALIDACIÓN DE TARJETA")
        print("  [1] Registrar cobro (tarjeta pasa por lector)")
        print("  [2] Ver lectores disponibles")
        print("  [0] Volver al menú principal")
        op = pedir("Opción")

        if op == "1":
            subtitulo("Registrar cobro")
            info("El cobro se realiza en fecha/hora actual.")
            id_t   = pedir_int("ID de tarjeta")
            id_l   = pedir_int("ID del lector")
            monto  = pedir_float("Monto a cobrar (Bs)")
            t = _consultar_tarjeta(id_t)
            if t:
                info(f"Propietario: {t['PROPIETARIO']}  |  Saldo actual: Bs {t['SALDO']}")
            if _registrar_cobro(id_t, id_l, monto):
                ok("Cobro registrado exitosamente.")
                t2 = _consultar_tarjeta(id_t)
                if t2:
                    info(f"Nuevo saldo: Bs {t2['SALDO']}")
            pausar()

        elif op == "2":
            subtitulo("Lectores disponibles")
            tabla(_listar_lectores(), [
                ("ID_LECTOR",  "ID Lector", 10),
                ("ID_AUTOBUS", "ID Bus",    8),
                ("RUTA_LINEA", "Ruta",      30),
            ])
            pausar()

        elif op == "0":
            break

# ── AUTOBUSES ─────────────────────────────────────────────────────

def pantalla_autobuses():
    while True:
        limpiar()
        titulo("GESTIÓN DE AUTOBUSES")
        print("  [1] Registrar nuevo autobús")
        print("  [2] Listar autobuses")
        print("  [3] Agregar lector a un autobús")
        print("  [0] Volver al menú principal")
        op = pedir("Opción")

        if op == "1":
            subtitulo("Nuevo autobús")
            ruta  = pedir("Ruta/Línea (ej: Linea 3 - Miraflores)")
            soat  = pedir("Número SOAT (opcional)", requerido=False)
            rev   = pedir("Revisión técnica (opcional)", requerido=False)
            id_b = _registrar_bus(ruta, soat, rev)
            if id_b:
                ok(f"Autobús registrado con ID = {id_b}")
                if pedir("¿Agregar lector a este bus? (s/n)", requerido=False).lower() == "s":
                    id_l = _agregar_lector(id_b)
                    if id_l:
                        ok(f"Lector agregado con ID = {id_l}")
            pausar()

        elif op == "2":
            subtitulo("Lista de autobuses")
            tabla(_listar_buses(), [
                ("ID_AUTOBUS",       "ID",    4),
                ("RUTA_LINEA",       "Ruta", 28),
                ("SOAT",             "SOAT", 12),
                ("REVISION_TECNICA", "Rev.Técnica", 14),
            ])
            pausar()

        elif op == "3":
            subtitulo("Agregar lector")
            id_b = pedir_int("ID del autobús")
            id_l = _agregar_lector(id_b)
            if id_l:
                ok(f"Lector creado con ID = {id_l}")
            pausar()

        elif op == "0":
            break

# ── CHOFERES ──────────────────────────────────────────────────────

def pantalla_choferes():
    while True:
        limpiar()
        titulo("GESTIÓN DE CHOFERES")
        print("  [1] Registrar nuevo chofer")
        print("  [2] Listar choferes")
        print("  [3] Asignar turno (chofer → bus)")
        print("  [4] Ver turnos de una fecha")
        print("  [0] Volver al menú principal")
        op = pedir("Opción")

        if op == "1":
            subtitulo("Nuevo chofer")
            ci       = pedir("CI (cédula de identidad)")
            nombre   = pedir("Nombre completo")
            id_int   = pedir("ID interno (opcional)", requerido=False)
            numero   = pedir("Teléfono (opcional)",   requerido=False)
            direc    = pedir("Dirección (opcional)",  requerido=False)
            licencia = pedir("Nro. licencia (opcional)", requerido=False)
            if _registrar_chofer(ci, nombre, id_int, numero, direc, licencia):
                ok(f"Chofer '{nombre}' registrado.")
            pausar()

        elif op == "2":
            subtitulo("Lista de choferes")
            tabla(_listar_choferes(), [
                ("CI_CHOFER",            "CI",       10),
                ("NOMBRE",               "Nombre",   25),
                ("NUMERO",               "Teléfono", 12),
                ("LICENCIA_DE_CONDUCIR", "Licencia", 12),
            ])
            pausar()

        elif op == "3":
            subtitulo("Asignar turno")
            ci     = pedir("CI del chofer")
            id_b   = pedir_int("ID del autobús")
            fecha  = pedir_fecha("Fecha del turno")
            if _asignar_turno(ci, id_b, fecha):
                ok(f"Turno asignado para el {fecha}.")
            pausar()

        elif op == "4":
            subtitulo("Turnos del día")
            fecha = pedir_fecha("Fecha a consultar")
            tabla(_turnos_del_dia(fecha), [
                ("ID_AUTOBUS", "ID Bus", 8),
                ("RUTA_LINEA", "Ruta",  28),
                ("CHOFER",     "Chofer",22),
                ("CI_CHOFER",  "CI",    10),
            ])
            pausar()

        elif op == "0":
            break

# ── REPORTES ──────────────────────────────────────────────────────

def pantalla_reportes():
    while True:
        limpiar()
        titulo("REPORTES")
        print("  [1] Recaudación por autobús (por fecha)")
        print("  [2] Recargas por tipo de canal")
        print("  [0] Volver al menú principal")
        op = pedir("Opción")

        if op == "1":
            subtitulo("Recaudación por autobús")
            fecha = pedir_fecha("Fecha del reporte")
            datos = _rep_recaudacion(fecha)
            tabla(datos, [
                ("ID_AUTOBUS",  "ID Bus",    8),
                ("RUTA_LINEA",  "Ruta",     28),
                ("VIAJES",      "Viajes",    8),
                ("RECAUDACION", "Bs Total", 12),
            ])
            if datos:
                total = sum(float(r["RECAUDACION"] or 0) for r in datos)
                print(f"\n  TOTAL RECAUDADO: Bs {total:.2f}")
            pausar()

        elif op == "2":
            subtitulo("Recargas por canal")
            tabla(_rep_recargas_canal(), [
                ("TIPO_CANAL", "Canal",    22),
                ("CANTIDAD",   "Cantidad", 10),
                ("MONTO_TOTAL","Bs Total", 12),
            ])
            pausar()

        elif op == "0":
            break


#  MENÚ PRINCIPAL


def menu_principal():
    while True:
        limpiar()
        titulo("SISTEMA DE TRANSPORTE PÚBLICO")
        print(f"  Fecha: {date.today().strftime('%d/%m/%Y')}")
        print()
        print("  [1]  Usuarios")
        print("  [2]  Tarjetas")
        print("  [3]  Cobros / Validaciones")
        print("  [4]  Autobuses")
        print("  [5]  Choferes y Turnos")
        print("  [6]  Reportes")
        print()
        print("  [0]  Salir")
        print(LINEA)
        op = pedir("Opción")

        if   op == "1": pantalla_usuarios()
        elif op == "2": pantalla_tarjetas()
        elif op == "3": pantalla_cobros()
        elif op == "4": pantalla_autobuses()
        elif op == "5": pantalla_choferes()
        elif op == "6": pantalla_reportes()
        elif op == "0":
            limpiar()
            print("\n  Hasta luego.\n")
            sys.exit(0)


#  ENTRADA


if __name__ == "__main__":
    # Verificar conexión antes de mostrar el menú
    conn = conectar()
    if not conn:
        print("\n  Revisa la configuración en CONFIG (usuario, contraseña, base de datos).")
        sys.exit(1)
    conn.close()
    menu_principal()
