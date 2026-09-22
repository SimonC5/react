"""Piezas compartidas por los módulos del backend: base de datos, JWT y roles.

Vive aparte de ``main.py`` para que los módulos comerciales (ventas, facturas,
reportes, dashboards, PQR y chatbot) puedan reutilizar la conexión y las
dependencias de autenticación sin importaciones circulares.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlsplit
from typing import Any, Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, Header, status
from passlib.context import CryptContext

def _sufijo_del_hosting() -> str:
    """Dominio del hosting, deducido del nombre público de esta misma API.

    Render publica en ``RENDER_EXTERNAL_HOSTNAME`` el dominio real del servicio
    ("simonc-api.onrender.com"), así que de ahí sale el ".onrender.com" que le
    falta a un nombre interno.
    """
    propio = os.getenv('RENDER_EXTERNAL_HOSTNAME', '') or os.getenv('RENDER_EXTERNAL_URL', '')
    propio = propio.split('://')[-1].split('/')[0].strip()
    punto = propio.find('.')
    return propio[punto:] if punto > 0 else ''


def dominio_publico(valor: str) -> str:
    """Deja una dirección como la escribe el navegador: https://dominio.

    Al enlazar dos servicios, Render entrega el **nombre interno** del otro
    ("simonc-web"), que no es una dirección de internet: el navegador manda
    "https://simonc-web.onrender.com" y nada coincide. El síntoma (todo falla
    por CORS, o el enlace del correo no abre) no apunta a la causa, así que se
    corrige aquí: se le pone el esquema, se le quita la barra final y, si le
    falta el dominio del hosting, se le agrega.
    """
    direccion = str(valor or '').strip().rstrip('/')
    if not direccion:
        return ''
    esquema, _, resto = direccion.partition('://')
    if not resto:
        esquema, resto = 'https', direccion
    dominio, barra, ruta = resto.partition('/')
    nombre, dos_puntos, puerto = dominio.partition(':')
    if '.' not in nombre and nombre.lower() != 'localhost':
        dominio = f'{nombre}{_sufijo_del_hosting()}{dos_puntos}{puerto}'
    return f'{esquema}://{dominio}{barra}{ruta}'


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'simonsc.db'

# Carga backend/.env antes de leer cualquier variable de entorno, para que la
# clave de IA y las credenciales de correo funcionen sin definirlas a mano en
# el sistema. Las variables reales del entorno tienen prioridad sobre el
# archivo, que es lo que necesita el despliegue en Railway.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / '.env', override=False)
except ImportError:  # python-dotenv es opcional en entornos mínimos
    pass

SECRET_KEY = os.getenv('JWT_SECRET', 'simonsc-development-secret-change-me')
ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRES_IN', '120').replace('h', '')) * 60 if os.getenv('JWT_EXPIRES_IN', '').endswith('h') else 120

pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith('$2'):
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    return pwd_context.verify(password, stored_hash)


DB_ENGINE = (
    os.getenv('DB_ENGINE')
    or ('mysql' if os.getenv('DATABASE_URL', '').startswith('mysql') else 'sqlite')
).strip().lower()


def usa_mysql() -> bool:
    return DB_ENGINE in ('mysql', 'mariadb')


def _parametros_mysql() -> dict[str, Any]:
    """Datos de conexión al MySQL de XAMPP o del servicio desplegado."""
    url = os.getenv('DATABASE_URL', '')
    if url.startswith('mysql'):
        partes = urlsplit(url)
        return {
            'host': partes.hostname or '127.0.0.1',
            'port': partes.port or 3306,
            'user': unquote(partes.username or 'root'),
            'password': unquote(partes.password or ''),
            'database': partes.path.lstrip('/') or 'simonsc',
        }
    return {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'simonsc'),
    }


class Fila(dict):
    """Fila que se deja leer por nombre y por posición, como ``sqlite3.Row``."""

    def __getitem__(self, clave):
        if isinstance(clave, int):
            return list(self.values())[clave]
        return super().__getitem__(clave)


def _normalizar(valor: Any) -> Any:
    """Deja los valores de MySQL con la misma pinta que los de SQLite."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, datetime):
        return valor.replace(microsecond=0).isoformat(sep=' ')
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, timedelta):
        return str(valor)
    if isinstance(valor, (bytes, bytearray)):
        return valor.decode('utf-8', 'replace')
    return valor


# FOUND_ROWS hace que un UPDATE informe las filas que coincidieron, no solo las
# que cambiaron de valor, que es lo que hace SQLite. Sin esto, desactivar algo
# que ya estaba desactivado respondía "no encontrado".
CLIENT_FOUND_ROWS = 2
_OPCIONES_MYSQL: dict[str, Any] = {'autocommit': False, 'client_flags': [CLIENT_FOUND_ROWS]}


def _traducir(consulta: str) -> str:
    """Pasa el SQL escrito para SQLite al dialecto de MySQL."""
    return consulta.replace('INSERT OR IGNORE', 'INSERT IGNORE').replace('?', '%s')


class _CursorMySQL:
    """Resultado ya leído, con la interfaz que usa el resto del backend.

    Las filas se traen enteras y el cursor se cierra en el acto. Con la
    extensión en C del conector, dejar filas sin leer y lanzar otra consulta
    revienta con "Unread result found", así que no se deja nada pendiente.
    """

    def __init__(self, filas: list[dict[str, Any]], lastrowid: Optional[int], rowcount: int = -1):
        self._filas = [Fila((k, _normalizar(v)) for k, v in fila.items()) for fila in filas]
        self.lastrowid = lastrowid
        # El backend mira "rowcount" para saber si un UPDATE o un DELETE
        # encontró la fila y, si no, responder 404.
        self.rowcount = rowcount
        self._siguiente = 0

    def fetchone(self) -> Optional[Fila]:
        if self._siguiente >= len(self._filas):
            return None
        fila = self._filas[self._siguiente]
        self._siguiente += 1
        return fila

    def fetchall(self) -> list[Fila]:
        pendientes = self._filas[self._siguiente:]
        self._siguiente = len(self._filas)
        return pendientes

    def __iter__(self):
        return iter(self.fetchall())


class ConexionMySQL:
    """Conexión MySQL que se comporta como la de ``sqlite3``."""

    def __init__(self, conexion):
        self._conexion = conexion

    def execute(self, consulta: str, parametros: Any = ()) -> _CursorMySQL:
        cursor = self._conexion.cursor(dictionary=True, buffered=True)
        try:
            if parametros:
                cursor.execute(_traducir(consulta), tuple(parametros))
            else:
                # Sin parámetros no se interpola, así que un '%' del SQL no estorba.
                cursor.execute(_traducir(consulta))
            filas = cursor.fetchall() if getattr(cursor, 'with_rows', False) else []
            return _CursorMySQL(filas, cursor.lastrowid, cursor.rowcount)
        finally:
            cursor.close()

    def executescript(self, guion: str) -> None:
        for sentencia in filtrar_sentencias(guion):
            cursor = self._conexion.cursor(buffered=True)
            try:
                cursor.execute(sentencia)
            finally:
                cursor.close()

    def commit(self) -> None:
        self._conexion.commit()

    def close(self) -> None:
        self._conexion.close()


def filtrar_sentencias(guion: str) -> list[str]:
    """Separa un script SQL en sentencias, ignorando comentarios y vacíos."""
    limpio = '\n'.join(
        linea for linea in guion.splitlines() if not linea.strip().startswith('--')
    )
    return [sentencia.strip() for sentencia in limpio.split(';') if sentencia.strip()]


ER_BAD_DB_ERROR = 1049


def _crear_base_mysql(parametros: dict[str, Any], nombre: str) -> None:
    """Crea la base cuando todavía no existe, antes de crear las tablas.

    Sin esto habría que crearla a mano en phpMyAdmin: la conexión pide una
    base concreta y falla con 1049 si no está.
    """
    import mysql.connector

    if '`' in nombre:
        raise RuntimeError(f'Nombre de base de datos inválido: {nombre!r}')

    servidor = mysql.connector.connect(**parametros, autocommit=True)
    try:
        cursor = servidor.cursor()
        try:
            cursor.execute(
                f'CREATE DATABASE IF NOT EXISTS `{nombre}` '
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
            )
        finally:
            cursor.close()
    finally:
        servidor.close()


def get_db_connection():
    if usa_mysql():
        import mysql.connector

        parametros = _parametros_mysql()
        nombre = parametros.pop('database')
        try:
            conexion = mysql.connector.connect(**parametros, database=nombre, **_OPCIONES_MYSQL)
        except mysql.connector.Error as error:
            if getattr(error, 'errno', None) != ER_BAD_DB_ERROR:
                raise
            _crear_base_mysql(parametros, nombre)
            conexion = mysql.connector.connect(**parametros, database=nombre, **_OPCIONES_MYSQL)
        return ConexionMySQL(conexion)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def create_access_token(subject: dict[str, Any]) -> str:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {'exp': expire, **subject}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token inválido o expirado.') from exc


def get_current_user(authorization: Optional[str] = Header(None)):
    if authorization is None or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token requerido.')
    token = authorization.replace('Bearer ', '', 1)
    payload = decode_token(token)
    user_email = payload.get('email')
    if not user_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token inválido.')

    conn = get_db_connection()
    try:
        user = conn.execute(
            '''
            SELECT u.*, r.name AS role
            FROM usuarios u
            JOIN roles r ON r.id = u.role_id
            WHERE u.email = ?
            ''',
            (user_email,),
        ).fetchone()
    finally:
        conn.close()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Usuario no encontrado.')
    return dict(user)


def require_roles(*roles: str):
    def dependency(current_user: dict[str, Any] = Depends(get_current_user)):
        if current_user.get('role') not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='No tienes permisos para esta acción.')
        return current_user

    return dependency


def aplicar_schema_sql(conn) -> None:
    """Crea las tablas de MySQL a partir de ``backend/schema.sql``."""
    ruta = BASE_DIR / 'schema.sql'
    if not ruta.exists():
        raise RuntimeError('Falta backend/schema.sql, necesario para crear las tablas en MySQL.')

    for sentencia in filtrar_sentencias(ruta.read_text(encoding='utf-8')):
        cabeza = sentencia.lstrip().upper()
        # La base de datos la elige la conexión: el script no debe cambiarla.
        if cabeza.startswith('CREATE DATABASE') or cabeza.startswith('USE '):
            continue
        conn.execute(sentencia)
    conn.commit()
