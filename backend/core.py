"""Piezas compartidas por los módulos del backend: base de datos, JWT y roles.

Vive aparte de ``main.py`` para que los módulos comerciales (ventas, facturas,
reportes, dashboards, PQR y chatbot) puedan reutilizar la conexión y las
dependencias de autenticación sin importaciones circulares.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, Header, status
from passlib.context import CryptContext

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


def get_db_connection() -> sqlite3.Connection:
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
