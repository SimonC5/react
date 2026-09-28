"""Recuperación de contraseña por correo con enlace de un solo uso.

El correo se envía por SMTP cuando las variables ``SMTP_*`` están configuradas
(ver ``correo.py``: con Gmail basta ``SMTP_USER`` y ``SMTP_PASSWORD``). Si no lo
están, el enlace se escribe en la consola del backend, de forma que el flujo se
puede probar igual. El token nunca viaja en la respuesta HTTP: eso permitiría a
cualquiera cambiar la contraseña de otra persona.

La respuesta de ``/recover`` es idéntica exista o no el correo, para que nadie
pueda averiguar qué cuentas hay registradas. Sí dice si **el servidor** de correo
está configurado, que es un dato del servidor y no de la cuenta consultada.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

try:
    from .core import dominio_publico, get_db_connection, hash_password, require_roles
    from .correo import (
        enviar_correo_detalle,
        hay_correo_configurado,
        remitente,
        revisar_configuracion,
        servidor_de_correo,
    )
except ImportError:
    from core import dominio_publico, get_db_connection, hash_password, require_roles
    from correo import (
        enviar_correo_detalle,
        hay_correo_configurado,
        remitente,
        revisar_configuracion,
        servidor_de_correo,
    )

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


class PruebaDeCorreo(BaseModel):
    email: EmailStr


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
    # El enlace va a un correo: tiene que ser la dirección pública, no el
    # nombre interno con el que se hablan los servicios del hosting.
    return dominio_publico(os.getenv('FRONTEND_URL', '')) or 'http://localhost:5173'


def _cuerpo_html(enlace: str) -> str:
    """Versión con botón, que es como se ve el correo en Gmail."""
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#1e293b;line-height:1.5">'
        '<h2 style="color:#0e7490;margin:0 0 12px">Recuperación de contraseña</h2>'
        '<p>Recibimos una solicitud para cambiar la contraseña de tu cuenta en '
        '<strong>SimonC Realidad Virtual</strong>.</p>'
        f'<p style="margin:24px 0"><a href="{enlace}" '
        'style="background:#0891b2;color:#ffffff;padding:12px 22px;border-radius:9999px;'
        'text-decoration:none;font-weight:bold">Crear una contraseña nueva</a></p>'
        f'<p style="font-size:13px;color:#475569">El enlace vence en {VIGENCIA_MINUTOS} minutos '
        'y solo se puede usar una vez. Si el botón no funciona, copia esta dirección:<br>'
        f'<span style="word-break:break-all">{enlace}</span></p>'
        '<p style="font-size:13px;color:#475569">Si no fuiste tú, puedes ignorar este mensaje: '
        'tu contraseña actual sigue siendo válida.</p>'
        '</div>'
    )


def _enviar_enlace(destinatario: str, enlace: str):
    """Manda el enlace de recuperación. Devuelve el resultado con su motivo."""
    return enviar_correo_detalle(
        destinatario,
        'Recuperación de contraseña - SimonC',
        'Recibimos una solicitud para cambiar tu contraseña.\n\n'
        f'Abre este enlace para crear una nueva (vence en {VIGENCIA_MINUTOS} minutos):\n{enlace}\n\n'
        'Si no fuiste tú, puedes ignorar este mensaje.',
        _cuerpo_html(enlace),
    )


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
            # Se responde lo mismo que si la cuenta existiera: así nadie puede
            # usar esta pantalla para averiguar qué correos están registrados.
            return {'message': MENSAJE_GENERICO, 'correoConfigurado': hay_correo_configurado()}

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
    resultado = _enviar_enlace(email, enlace)
    if not resultado.enviado:
        # Sin correo configurado (o si falla) el enlace se imprime aquí para
        # poder probar el flujo, junto con el motivo del fallo.
        print(f'[recuperacion] No salió el correo para {email}: {resultado.motivo}')
        print(f'[recuperacion] Enlace para {email}: {enlace}')

    return {'message': MENSAJE_GENERICO, 'correoConfigurado': hay_correo_configurado()}


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


@router.get('/correo-estado', dependencies=[Depends(require_roles('Administrador'))])
def estado_del_correo():
    """Diagnóstico del servidor de correo, para el panel del administrador."""
    falta = revisar_configuracion()
    host, puerto = servidor_de_correo()
    return {
        'configurado': not falta,
        'motivo': falta,
        'servidor': f'{host}:{puerto}' if host else '',
        'remitente': remitente() if not falta else '',
    }


@router.post('/probar-correo', dependencies=[Depends(require_roles('Administrador'))])
def probar_correo(payload: PruebaDeCorreo):
    """Manda un correo de prueba para comprobar la configuración sin adivinar."""
    destino = str(payload.email).strip()
    resultado = _enviar_enlace_de_prueba(destino)
    if resultado.enviado:
        return {'enviado': True, 'message': f'Correo de prueba enviado a {destino}. Revisa la bandeja de entrada y el correo no deseado.'}
    return {'enviado': False, 'message': resultado.motivo}


def _enviar_enlace_de_prueba(destino: str):
    return enviar_correo_detalle(
        destino,
        'Prueba de correo - SimonC',
        'Este es un correo de prueba de SimonC Realidad Virtual.\n\n'
        'Si lo estás leyendo, el servidor de correo quedó bien configurado y los '
        'enlaces para recuperar la contraseña van a llegar sin problema.',
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#1e293b;line-height:1.5">'
        '<h2 style="color:#0e7490;margin:0 0 12px">El correo funciona</h2>'
        '<p>Este es un correo de prueba de <strong>SimonC Realidad Virtual</strong>.</p>'
        '<p>Si lo estás leyendo, el servidor de correo quedó bien configurado y los '
        'enlaces para recuperar la contraseña van a llegar sin problema.</p></div>',
    )
