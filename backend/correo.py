"""Envío de correo por SMTP, compartido por los módulos que notifican al usuario.

Se configura con las variables ``SMTP_*``. Para los proveedores conocidos basta
escribir ``SMTP_USER`` y ``SMTP_PASSWORD``: el servidor se deduce del dominio del
correo, que es donde más se equivoca quien configura esto por primera vez. Con
Gmail la contraseña **no** es la de la cuenta sino una contraseña de aplicación.

Si no hay nada configurado no se envía y se devuelve el motivo en español, para
que la pantalla pueda decir qué falta en lugar de fallar en silencio. Ninguna
credencial se escribe en el código: todas salen del entorno o de ``backend/.env``.
"""

import os
import smtplib
from collections import namedtuple
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

# ``enviado`` dice si salió; ``motivo`` explica en español por qué no, y queda
# vacío cuando sí salió.
ResultadoCorreo = namedtuple('ResultadoCorreo', 'enviado motivo')

NOMBRE_REMITENTE = 'SimonC Realidad Virtual'

# Servidor y puerto de los proveedores más comunes, para no tener que escribir
# SMTP_HOST a mano. El puerto 587 es el de STARTTLS en todos ellos.
PROVEEDORES = {
    'gmail.com': ('smtp.gmail.com', 587),
    'googlemail.com': ('smtp.gmail.com', 587),
    'outlook.com': ('smtp-mail.outlook.com', 587),
    'hotmail.com': ('smtp-mail.outlook.com', 587),
    'live.com': ('smtp-mail.outlook.com', 587),
    'yahoo.com': ('smtp.mail.yahoo.com', 587),
    'yahoo.es': ('smtp.mail.yahoo.com', 587),
}


def _variable(nombre: str) -> str:
    return os.getenv(nombre, '').strip()


def _dominio(correo: str) -> str:
    return correo.rsplit('@', 1)[-1].lower() if '@' in correo else ''


def servidor_de_correo() -> tuple[str, int]:
    """Servidor y puerto a usar, deduciendo el servidor cuando no está escrito."""
    host = _variable('SMTP_HOST')
    puerto = 587
    if not host:
        host, puerto = PROVEEDORES.get(_dominio(_variable('SMTP_USER')), ('', 587))

    escrito = _variable('SMTP_PORT')
    if escrito.isdigit() and int(escrito) > 0:
        puerto = int(escrito)
    return host, puerto


def remitente() -> str:
    """Cabecera ``From``. Gmail exige que sea la misma cuenta que se autentica."""
    direccion = _variable('SMTP_FROM') or _variable('SMTP_USER')
    if not direccion:
        return formataddr((NOMBRE_REMITENTE, 'no-reply@simonsc.com'))
    nombre, solo_correo = parseaddr(direccion)
    return formataddr((nombre or NOMBRE_REMITENTE, solo_correo or direccion))


def revisar_configuracion() -> str:
    """Qué falta para poder enviar correo. Cadena vacía si no falta nada."""
    usuario = _variable('SMTP_USER')
    if not _variable('SMTP_HOST') and not usuario:
        return (
            'No hay servidor de correo configurado: falta SMTP_USER, el correo '
            'desde el que se envían los mensajes.'
        )

    host, _ = servidor_de_correo()
    if not host:
        return (
            f'Falta SMTP_HOST: no reconozco el proveedor de «{usuario}», '
            'así que no sé a qué servidor de correo conectarme.'
        )
    if usuario and not _variable('SMTP_PASSWORD'):
        return (
            'Falta SMTP_PASSWORD. Con Gmail no es la contraseña de la cuenta, '
            'sino una contraseña de aplicación de 16 letras.'
        )
    return ''


def hay_correo_configurado() -> bool:
    """¿Hay un servidor SMTP al que escribirle?"""
    return not revisar_configuracion()


def _usa_ssl(puerto: int) -> bool:
    """El puerto 465 habla TLS desde el saludo; el 587 lo negocia con STARTTLS."""
    escrito = _variable('SMTP_USE_SSL').lower()
    if escrito in ('true', '1', 'si', 'sí'):
        return True
    if escrito in ('false', '0', 'no'):
        return False
    return puerto == 465


def _armar(destinatario: str, asunto: str, cuerpo: str, html: str | None) -> EmailMessage:
    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = remitente()
    mensaje['To'] = destinatario
    mensaje.set_content(cuerpo)
    if html:
        # El texto plano queda como alternativa para los lectores que no
        # muestran HTML, así el correo se lee en cualquier cliente.
        mensaje.add_alternative(html, subtype='html')
    return mensaje


def _sin_credenciales(texto: str) -> str:
    """Nunca devolver la contraseña dentro de un mensaje de error."""
    clave = _variable('SMTP_PASSWORD')
    return texto.replace(clave, '***') if clave else texto


def _motivo_de_rechazo(error: smtplib.SMTPAuthenticationError, host: str) -> str:
    if host == 'smtp.gmail.com':
        return (
            'Gmail rechazó el usuario o la contraseña. Tiene que ser una '
            'contraseña de aplicación (16 letras, creada en la cuenta de Google '
            'con la verificación en dos pasos activada), no la contraseña normal.'
        )
    return f'El servidor de correo rechazó el usuario o la contraseña ({error.smtp_code}).'


def enviar_correo_detalle(destinatario: str, asunto: str, cuerpo: str, html: str | None = None) -> ResultadoCorreo:
    """Envía un correo y devuelve si salió y, si no, por qué.

    Nunca lanza excepción: un fallo del servidor de correo no debe tumbar la
    operación que lo pidió (la respuesta a una PQR queda guardada igual).
    """
    destinatario = (destinatario or '').strip()
    if not destinatario:
        return ResultadoCorreo(False, 'No hay a quién enviarle: la cuenta no tiene correo registrado.')

    falta = revisar_configuracion()
    if falta:
        return ResultadoCorreo(False, falta)

    host, puerto = servidor_de_correo()
    usuario = _variable('SMTP_USER')
    clave = os.getenv('SMTP_PASSWORD', '')
    mensaje = _armar(destinatario, asunto, cuerpo, html)

    try:
        if _usa_ssl(puerto):
            conexion = smtplib.SMTP_SSL(host, puerto, timeout=20)
        else:
            conexion = smtplib.SMTP(host, puerto, timeout=20)
        with conexion as servidor:
            if not _usa_ssl(puerto) and _variable('SMTP_USE_TLS').lower() != 'false':
                servidor.starttls()
            if usuario:
                servidor.login(usuario, clave)
            servidor.send_message(mensaje)
        return ResultadoCorreo(True, '')
    except smtplib.SMTPAuthenticationError as error:
        return ResultadoCorreo(False, _motivo_de_rechazo(error, host))
    except (smtplib.SMTPException, OSError) as error:
        detalle = _sin_credenciales(str(error)) or type(error).__name__
        return ResultadoCorreo(False, f'No se pudo hablar con {host}:{puerto}. Dice: {detalle}')
