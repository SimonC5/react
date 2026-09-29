"""Envío de correo, compartido por los módulos que notifican al usuario.

Hay dos formas de enviar y el programa escoge sola la que esté configurada:

1. **Por API web** (``EMAIL_API_KEY``), que viaja por HTTPS como cualquier
   página. Es la única que funciona en el plan gratuito de Render, que desde
   septiembre de 2025 bloquea el tráfico de salida a los puertos de SMTP.
2. **Por SMTP** (``SMTP_USER`` y ``SMTP_PASSWORD``), que sirve en el computador
   de uno y en los planes de pago. Para los proveedores conocidos el servidor se
   deduce del dominio del correo, que es donde más se equivoca quien configura
   esto por primera vez; con Gmail la contraseña **no** es la de la cuenta sino
   una contraseña de aplicación.

Si no hay nada configurado no se envía y se devuelve el motivo en español, para
que la pantalla pueda decir qué falta en lugar de fallar en silencio. Ninguna
credencial se escribe en el código: todas salen del entorno o de ``backend/.env``.
"""

import json
import os
import smtplib
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

# ``enviado`` dice si salió; ``motivo`` explica en español por qué no, y queda
# vacío cuando sí salió.
ResultadoCorreo = namedtuple('ResultadoCorreo', 'enviado motivo')

NOMBRE_REMITENTE = 'SimonC Realidad Virtual'
ESPERA = 20

# Brevo (antes Sendinblue): plan gratuito de 300 correos al día y el remitente
# se verifica con un solo correo, sin necesidad de tener un dominio propio.
URL_API_POR_DEFECTO = 'https://api.brevo.com/v3/smtp/email'

# Servidor y puerto de los proveedores de SMTP más comunes, para no tener que
# escribir SMTP_HOST a mano. El puerto 587 es el de STARTTLS en todos ellos.
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


def _en_render() -> bool:
    """Render marca sus servicios con esta variable."""
    return bool(_variable('RENDER') or _variable('RENDER_EXTERNAL_HOSTNAME'))


def via() -> str:
    """Por dónde se va a enviar: ``api``, ``smtp``, o nada si falta configurar."""
    if _variable('EMAIL_API_KEY'):
        return 'api'
    if _variable('SMTP_HOST') or _variable('SMTP_USER'):
        return 'smtp'
    return ''


def servidor_de_correo() -> tuple[str, int]:
    """Servidor y puerto de SMTP, deduciendo el servidor cuando no está escrito."""
    host = _variable('SMTP_HOST')
    puerto = 587
    if not host:
        host, puerto = PROVEEDORES.get(_dominio(_variable('SMTP_USER')), ('', 587))

    escrito = _variable('SMTP_PORT')
    if escrito.isdigit() and int(escrito) > 0:
        puerto = int(escrito)
    return host, puerto


def _direccion_del_remitente() -> str:
    return _variable('EMAIL_FROM') or _variable('SMTP_FROM') or _variable('SMTP_USER')


def remitente() -> str:
    """Cabecera ``From``. Gmail exige que sea la misma cuenta que se autentica."""
    direccion = _direccion_del_remitente()
    if not direccion:
        return formataddr((NOMBRE_REMITENTE, 'no-reply@simonsc.com'))
    nombre, solo_correo = parseaddr(direccion)
    return formataddr((nombre or NOMBRE_REMITENTE, solo_correo or direccion))


def _falta_para_la_api() -> str:
    if not _direccion_del_remitente():
        return (
            'Falta EMAIL_FROM: el correo verificado en el proveedor, que es el '
            'que aparece como remitente de los mensajes.'
        )
    return ''


def _falta_para_smtp() -> str:
    usuario = _variable('SMTP_USER')
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


def revisar_configuracion() -> str:
    """Qué falta para poder enviar correo. Cadena vacía si no falta nada."""
    camino = via()
    if not camino:
        return (
            'No hay forma de enviar correo configurada: falta EMAIL_API_KEY (la '
            'recomendada, y la única que funciona en el plan gratuito de Render) '
            'o, para enviar por SMTP, SMTP_USER.'
        )
    return _falta_para_la_api() if camino == 'api' else _falta_para_smtp()


def advertencia() -> str:
    """Avisos que no impiden enviar pero explican por qué no va a llegar."""
    if via() == 'smtp' and _en_render():
        return (
            'Render bloquea la salida a los puertos de SMTP en el plan gratuito, '
            'así que desde el sitio publicado este correo no va a salir. Para que '
            'salga hay que usar EMAIL_API_KEY, que viaja por web.'
        )
    return ''


def hay_correo_configurado() -> bool:
    """¿Hay por dónde enviar?"""
    return not revisar_configuracion()


def _sin_credenciales(texto: str) -> str:
    """Nunca devolver una clave dentro de un mensaje de error."""
    for nombre in ('SMTP_PASSWORD', 'EMAIL_API_KEY'):
        clave = _variable(nombre)
        if clave:
            texto = texto.replace(clave, '***')
    return texto


# --- Envío por API web -----------------------------------------------------

def _motivo_de_la_api(error: urllib.error.HTTPError, servicio: str) -> str:
    try:
        detalle = json.loads(error.read().decode('utf-8', 'replace'))
        dice = str(detalle.get('message') or detalle)
    except (ValueError, OSError):
        dice = error.reason or ''

    if error.code in (401, 403):
        return f'{servicio} no aceptó la clave (error {error.code}). Revisa que EMAIL_API_KEY esté completa y activa.'
    if error.code == 400 and 'sender' in dice.lower():
        return (
            f'{servicio} no reconoce el remitente «{_direccion_del_remitente()}». '
            'Hay que verificar ese correo en la cuenta del proveedor antes de poder enviar desde él.'
        )
    return f'{servicio} respondió error {error.code}. Dice: {_sin_credenciales(dice)}'


def _enviar_por_api(destinatario: str, asunto: str, cuerpo: str, html: str | None) -> ResultadoCorreo:
    url = _variable('EMAIL_API_URL') or URL_API_POR_DEFECTO
    servicio = urllib.parse.urlparse(url).hostname or 'el proveedor de correo'
    nombre, direccion = parseaddr(_direccion_del_remitente())

    datos = {
        'sender': {'name': nombre or NOMBRE_REMITENTE, 'email': direccion},
        'to': [{'email': destinatario}],
        'subject': asunto,
        'textContent': cuerpo,
    }
    if html:
        datos['htmlContent'] = html

    peticion = urllib.request.Request(
        url,
        data=json.dumps(datos).encode('utf-8'),
        headers={
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': _variable('EMAIL_API_KEY'),
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(peticion, timeout=ESPERA) as respuesta:
            respuesta.read()
        return ResultadoCorreo(True, '')
    except urllib.error.HTTPError as error:
        return ResultadoCorreo(False, _motivo_de_la_api(error, servicio))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        detalle = _sin_credenciales(str(error)) or type(error).__name__
        return ResultadoCorreo(False, f'No se pudo hablar con {servicio}. Dice: {detalle}')


# --- Envío por SMTP --------------------------------------------------------

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


def _motivo_de_rechazo(error: smtplib.SMTPAuthenticationError, host: str) -> str:
    if host == 'smtp.gmail.com':
        return (
            'Gmail rechazó el usuario o la contraseña. Tiene que ser una '
            'contraseña de aplicación (16 letras, creada en la cuenta de Google '
            'con la verificación en dos pasos activada), no la contraseña normal.'
        )
    return f'El servidor de correo rechazó el usuario o la contraseña ({error.smtp_code}).'


def _enviar_por_smtp(destinatario: str, asunto: str, cuerpo: str, html: str | None) -> ResultadoCorreo:
    host, puerto = servidor_de_correo()
    usuario = _variable('SMTP_USER')
    clave = os.getenv('SMTP_PASSWORD', '')
    mensaje = _armar(destinatario, asunto, cuerpo, html)

    try:
        if _usa_ssl(puerto):
            conexion = smtplib.SMTP_SSL(host, puerto, timeout=ESPERA)
        else:
            conexion = smtplib.SMTP(host, puerto, timeout=ESPERA)
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
        aviso = advertencia()
        return ResultadoCorreo(False, f'No se pudo hablar con {host}:{puerto}. Dice: {detalle}{" " + aviso if aviso else ""}')


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

    if via() == 'api':
        return _enviar_por_api(destinatario, asunto, cuerpo, html)
    return _enviar_por_smtp(destinatario, asunto, cuerpo, html)
