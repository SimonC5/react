"""Recuperación de contraseña por correo con enlace de un solo uso.

El correo se envía por SMTP cuando las variables ``SMTP_*`` están configuradas.
Si no lo están (el caso habitual en desarrollo) el enlace se escribe en la
consola del backend, de forma que el flujo se puede probar igual. El token
nunca viaja en la respuesta HTTP: eso permitiría a cualquiera cambiar la
contraseña de otra persona.
"""

import hashlib
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

try:
    from .core import get_db_connection, hash_password
except ImportError:
    from core import get_db_connection, hash_password

router = APIRouter(prefix='/api/auth', tags=['auth'])

VIGENCIA_MINUTOS = 60
MENSAJE_GENERICO = 'Si el correo existe, recibirás instrucciones para recuperar tu cuenta.'

RECUPERACION_SCHEMA = '''
CREATE TABLE IF NOT EXISTS recuperaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expira_en TEXT NOT NULL,
    usado INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_recuperaciones_usuario ON recuperaciones (usuario_id);
'''


class SolicitudRecuperacion(BaseModel):
    email: EmailStr


class CambioDeClave(BaseModel):
    token: str
    password: str


def init_recuperacion_db(conn) -> None:
    conn.executescript(RECUPERACION_SCHEMA)
    conn.commit()


def _ahora() -> datetime:
    """UTC sin zona: el formato que entienden por igual SQLite y MySQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _texto(momento: datetime) -> str:
    return momento.isoformat(sep=' ')


def _huella(token: str) -> str:
    """Solo se guarda el hash: si alguien lee la tabla no puede usar el enlace."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _frontend_url() -> str:
    return os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')


def _enviar_correo(destinatario: str, enlace: str) -> bool:
    host = os.getenv('SMTP_HOST', '')
    if not host:
        return False

    mensaje = EmailMessage()
    mensaje['Subject'] = 'Recuperación de contraseña - SimonC'
    mensaje['From'] = os.getenv('SMTP_FROM') or os.getenv('SMTP_USER', 'no-reply@simonsc.com')
    mensaje['To'] = destinatario
    mensaje.set_content(
        'Recibimos una solicitud para cambiar tu contraseña.\n\n'
        f'Abre este enlace para crear una nueva (vence en {VIGENCIA_MINUTOS} minutos):\n{enlace}\n\n'
        'Si no fuiste tú, puedes ignorar este mensaje.'
    )

    puerto = int(os.getenv('SMTP_PORT', '587'))
    usuario = os.getenv('SMTP_USER', '')
    clave = os.getenv('SMTP_PASSWORD', '')
    try:
        with smtplib.SMTP(host, puerto, timeout=15) as servidor:
            if os.getenv('SMTP_USE_TLS', 'true').lower() == 'true':
                servidor.starttls()
            if usuario:
                servidor.login(usuario, clave)
            servidor.send_message(mensaje)
        return True
    except (smtplib.SMTPException, OSError) as error:
        print(f'[recuperacion] No se pudo enviar el correo: {error}')
        return False


@router.post('/recover')
def solicitar_recuperacion(payload: SolicitudRecuperacion):
    """Genera el enlace de recuperación. Responde igual exista o no el correo."""
    email = str(payload.email).strip().lower()
    conn = get_db_connection()
    try:
        usuario = conn.execute(
            'SELECT id, name, email FROM usuarios WHERE email = ? AND active = 1', (email,)
        ).fetchone()
        if usuario is None:
            return {'message': MENSAJE_GENERICO}

        ahora = _ahora()
        token = secrets.token_urlsafe(32)
        conn.execute('UPDATE recuperaciones SET usado = 1 WHERE usuario_id = ? AND usado = 0', (usuario['id'],))
        conn.execute(
            'INSERT INTO recuperaciones (usuario_id, token_hash, expira_en, usado, creado_en) VALUES (?, ?, ?, 0, ?)',
            (
                usuario['id'],
                _huella(token),
                _texto(ahora + timedelta(minutes=VIGENCIA_MINUTOS)),
                _texto(ahora),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    enlace = f'{_frontend_url()}/reset-password?token={token}'
    if not _enviar_correo(email, enlace):
        # Sin SMTP configurado el enlace se imprime aquí para poder probar el flujo.
        print(f'[recuperacion] Enlace para {email}: {enlace}')

    return {'message': MENSAJE_GENERICO}


@router.post('/reset-password')
def cambiar_clave(payload: CambioDeClave):
    clave = payload.password
    if len(clave) < 8 or not any(c.isalpha() for c in clave) or not any(c.isdigit() for c in clave):
        raise HTTPException(status_code=400, detail='La contraseña debe tener al menos 8 caracteres, letras y números.')

    conn = get_db_connection()
    try:
        fila = conn.execute(
            'SELECT id, usuario_id, expira_en FROM recuperaciones WHERE token_hash = ? AND usado = 0',
            (_huella(payload.token),),
        ).fetchone()
        if fila is None:
            raise HTTPException(status_code=400, detail='El enlace de recuperación no es válido o ya fue usado.')
        if datetime.fromisoformat(str(fila['expira_en'])) < _ahora():
            raise HTTPException(status_code=400, detail='El enlace de recuperación venció. Solicita uno nuevo.')

        conn.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (hash_password(clave), fila['usuario_id']))
        conn.execute('UPDATE recuperaciones SET usado = 1 WHERE id = ?', (fila['id'],))
        conn.commit()
    finally:
        conn.close()

    return {'message': 'Contraseña actualizada. Ya puedes iniciar sesión.'}
