"""Envío de correo por SMTP, compartido por los módulos que notifican al usuario.

Las variables ``SMTP_*`` son opcionales. Si no hay ``SMTP_HOST`` configurado no
se envía nada y la función devuelve ``False``: quien llama decide qué hacer, que
normalmente es escribir el mensaje en la consola para poder probar el flujo sin
un servidor de correo. Ninguna credencial se escribe en el código.
"""

import os
import smtplib
from email.message import EmailMessage


def hay_correo_configurado() -> bool:
    """¿Hay un servidor SMTP al que escribirle?"""
    return bool(os.getenv('SMTP_HOST', ''))


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """Envía un correo de texto. Devuelve si salió o no, sin lanzar excepción.

    Un fallo del servidor de correo no debe tumbar la operación que lo pidió:
    la respuesta a una PQR queda guardada aunque el correo no salga.
    """
    if not hay_correo_configurado() or not destinatario:
        return False

    mensaje = EmailMessage()
    mensaje['Subject'] = asunto
    mensaje['From'] = os.getenv('SMTP_FROM') or os.getenv('SMTP_USER', 'no-reply@simonsc.com')
    mensaje['To'] = destinatario
    mensaje.set_content(cuerpo)

    host = os.getenv('SMTP_HOST', '')
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
        print(f'[correo] No se pudo enviar el correo a {destinatario}: {error}')
        return False
