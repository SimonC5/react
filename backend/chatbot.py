"""Chatbot de atención al cliente conectado a un servicio de Inteligencia Artificial.

La clave del proveedor se lee de variables de entorno (``IA_API_KEY`` u
``OPENAI_API_KEY``) y nunca se expone en la respuesta ni se guarda en el
repositorio. Si no hay clave configurada, el chatbot responde con información
real del catálogo para que el módulo siga siendo usable.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

try:
    from .core import get_current_user, get_db_connection
    from .comercial import now_iso
except ImportError:
    from core import get_current_user, get_db_connection
    from comercial import now_iso

router = APIRouter(prefix='/api/chatbot', tags=['chatbot'])

IA_API_URL = os.getenv('IA_API_URL', 'https://api.openai.com/v1/chat/completions')

# ``IA_MODEL`` admite varios modelos separados por coma. Se intentan en orden:
# los planes gratuitos devuelven 503 ("high demand") cuando el modelo de moda
# está saturado, y en ese caso otro modelo de la misma clave suele contestar sin
# problema. Con un solo modelo escrito, la lista tiene un solo elemento.
IA_MODELOS = [modelo.strip() for modelo in os.getenv('IA_MODEL', 'gpt-4o-mini').split(',') if modelo.strip()]
IA_MODEL = IA_MODELOS[0] if IA_MODELOS else 'gpt-4o-mini'
IA_TIMEOUT = float(os.getenv('IA_TIMEOUT', '20'))
# Segundos que se pueden gastar en total probando modelos, para no dejar al
# cliente esperando mientras se recorre la lista entera.
IA_PRESUPUESTO = float(os.getenv('IA_PRESUPUESTO', '35'))
# Errores que valen la pena reintentar con otro modelo: saturación, cupo por
# minuto, caídas pasajeras del proveedor y modelos que esa clave no tiene.
CODIGOS_REINTENTABLES = {404, 408, 429, 500, 502, 503, 504}
HISTORIAL_MAXIMO = 10

INSTRUCCIONES = (
    'Eres el asistente virtual de SimonC, una tienda de gafas y servicios de realidad virtual. '
    'Respondes en español, con amabilidad y al grano. '
    'Cuando te pregunten qué hay, qué venden, cuáles tienen o por precios, enumera los artículos del '
    'catálogo uno por línea con su nombre y su precio, empezando por los que encajen con lo que pidió. '
    'Nunca contestes que hay "una amplia variedad" sin nombrarlos: el cliente quiere ver los nombres. '
    'Para todo lo demás responde en pocas frases. '
    'Ayudas a resolver preguntas frecuentes, orientas sobre los productos y servicios, explicas el proceso '
    'de compra y, cuando el cliente tiene una queja o un reclamo, le indicas que puede radicar una PQR desde '
    'su panel. No inventes precios, modelos ni promociones: usa únicamente el catálogo que recibes.'
)


class MensajeEntrada(BaseModel):
    mensaje: str
    conversacionId: Optional[int] = None


def api_key() -> str:
    return os.getenv('IA_API_KEY') or os.getenv('OPENAI_API_KEY') or ''


def _precio(valor: Any) -> str:
    """Precio como lo muestra el sitio, para que el chatbot no lo escriba distinto."""
    return f'$ {float(valor or 0):,.0f}'.replace(',', '.')


def _catalogo(conn) -> str:
    productos = conn.execute('SELECT name, description, price FROM productos WHERE active = 1 LIMIT 20').fetchall()
    servicios = conn.execute('SELECT name, description, price FROM servicios WHERE active = 1 LIMIT 20').fetchall()
    lineas = [f"- Producto: {fila['name']} ({_precio(fila['price'])}). {fila['description']}" for fila in productos]
    lineas += [f"- Servicio: {fila['name']} ({_precio(fila['price'])}). {fila['description']}" for fila in servicios]
    return '\n'.join(lineas) or 'El catálogo aún no tiene productos ni servicios activos.'


def _respuesta_local(mensaje: str, catalogo: str) -> str:
    """Respuesta de respaldo cuando no hay API Key configurada."""
    texto = mensaje.lower()
    if any(palabra in texto for palabra in ('precio', 'cuánto', 'cuanto', 'costo', 'valor', 'tarifa')):
        return f'Estos son los precios vigentes de nuestro catálogo:\n{catalogo}'
    if any(palabra in texto for palabra in ('queja', 'reclamo', 'pqr', 'problema', 'demora')):
        return (
            'Lamento el inconveniente. Puedes radicar una PQR desde tu panel, en la sección "PQR": '
            'registra el tipo, el asunto y la descripción, y podrás consultar el estado con el número de radicado.'
        )
    if any(palabra in texto for palabra in ('comprar', 'compra', 'pedido', 'contratar', 'cotizar')):
        return (
            'Para iniciar una compra elige el producto o servicio que te interese y un asesor registra la venta; '
            'después recibirás la factura en PDF desde la sección de facturas.'
        )
    if any(palabra in texto for palabra in ('factura', 'facturas', 'descargar')):
        return 'Puedes consultar y descargar tus facturas en PDF desde el panel, en la sección "Facturación".'
    if any(palabra in texto for palabra in ('hola', 'buenas', 'buenos días', 'buenas tardes')):
        return '¡Hola! Soy el asistente de SimonC. Puedo orientarte sobre productos, servicios, facturas y PQR.'
    return (
        'Con gusto te ayudo. Estos son los productos y servicios que ofrecemos:\n'
        f'{catalogo}\n'
        'Si tu solicitud es una queja o un reclamo, radícala como PQR desde tu panel.'
    )


def _motivo_del_proveedor(exc: urllib.error.HTTPError) -> str:
    """Explica en una línea por qué falló el proveedor de IA.

    Un número de error suelto no dice nada: lo habitual es que el modelo de
    ``IA_MODEL`` no exista para esa clave, o que ``IA_API_URL`` apunte a otro
    proveedor. El texto del proveedor lo aclara, así que se reenvía recortado y
    con la clave tachada por si acaso viniera repetida en la respuesta.
    """
    try:
        crudo = exc.read().decode('utf-8', 'replace')
    except Exception:  # noqa: BLE001 - si no se puede leer, basta con el código
        return ''

    try:
        datos = json.loads(crudo)
        if isinstance(datos, list):
            datos = datos[0] if datos else {}
        error = datos.get('error') if isinstance(datos, dict) else None
        mensaje = error.get('message') if isinstance(error, dict) else None
        crudo = mensaje or crudo
    except (json.JSONDecodeError, AttributeError, IndexError):
        pass

    crudo = ' '.join(crudo.split())
    clave = api_key()
    if clave:
        crudo = crudo.replace(clave, '***')
    if len(crudo) > 200:
        crudo = f'{crudo[:200]}...'
    return f'Dice: {crudo}' if crudo else ''


class FalloDeIA(Exception):
    """Un intento fallido contra el proveedor, con el motivo ya legible."""

    def __init__(self, motivo: str, reintentable: bool):
        super().__init__(motivo)
        self.motivo = motivo
        self.reintentable = reintentable


def _pedir_al_modelo(modelo: str, historial: list[dict[str, str]], catalogo: str) -> str:
    """Un intento contra un modelo concreto del proveedor."""
    cuerpo = json.dumps({
        'model': modelo,
        'messages': [
            {'role': 'system', 'content': f'{INSTRUCCIONES}\n\nCatálogo disponible:\n{catalogo}'},
            *historial,
        ],
        'temperature': 0.4,
        # Holgado a propósito: algunos modelos gastan parte del cupo en razonar
        # antes de escribir, y si se queda corto devuelven la respuesta vacía.
        'max_tokens': 2000,
    }).encode('utf-8')

    peticion = urllib.request.Request(
        IA_API_URL,
        data=cuerpo,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key()}'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(peticion, timeout=IA_TIMEOUT) as respuesta:
            datos = json.loads(respuesta.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        motivo = f'El servicio de Inteligencia Artificial respondió con error {exc.code}.'
        detalle = _motivo_del_proveedor(exc)
        raise FalloDeIA(
            f'{motivo} {detalle}'.strip(),
            reintentable=exc.code in CODIGOS_REINTENTABLES,
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FalloDeIA(
            'No fue posible contactar el servicio de Inteligencia Artificial.',
            reintentable=True,
        ) from exc

    opciones = datos.get('choices') or []
    contenido = (opciones[0].get('message', {}).get('content') if opciones else '') or ''
    if not contenido.strip():
        raise FalloDeIA(
            'El servicio de Inteligencia Artificial no devolvió respuesta.',
            reintentable=True,
        )
    return contenido.strip()


def _consultar_ia(historial: list[dict[str, str]], catalogo: str) -> str:
    """Pide la respuesta al proveedor, probando los modelos de ``IA_MODEL`` en orden.

    Los planes gratuitos se saturan: el modelo más pedido devuelve 503 y otro de
    la misma clave contesta a la primera. Por eso, ante un error pasajero se
    pasa al siguiente modelo en lugar de rendirse. Si el error es de la clave o
    de la petición, no tiene sentido insistir y se corta de una vez.
    """
    inicio = time.monotonic()
    ultimo = 'No hay ningún modelo de Inteligencia Artificial configurado.'

    for indice, modelo in enumerate(IA_MODELOS):
        if indice and time.monotonic() - inicio > IA_PRESUPUESTO:
            break
        try:
            return _pedir_al_modelo(modelo, historial, catalogo)
        except FalloDeIA as fallo:
            ultimo = fallo.motivo
            if not fallo.reintentable:
                break

    raise HTTPException(status_code=502, detail=ultimo)


@router.get('/estado')
def estado_del_servicio(_usuario: dict[str, Any] = Depends(get_current_user)):
    """Informa si hay clave configurada, sin revelarla nunca."""
    return {
        'iaHabilitada': bool(api_key()),
        'modelo': IA_MODEL if api_key() else None,
        'mensaje': (
            'Chatbot conectado al servicio de Inteligencia Artificial.'
            if api_key()
            else 'Sin API Key configurada: el chatbot responde con la información del catálogo.'
        ),
    }


@router.get('/conversaciones')
def listar_conversaciones(usuario: dict[str, Any] = Depends(get_current_user), limite: int = Query(20, ge=1, le=100)):
    conn = get_db_connection()
    try:
        filas = conn.execute(
            'SELECT * FROM conversaciones WHERE usuario_id = ? ORDER BY updated_at DESC LIMIT ?',
            (usuario.get('id'), limite),
        ).fetchall()
        return {
            'conversaciones': [
                {'id': fila['id'], 'titulo': fila['titulo'], 'creada': fila['created_at'], 'actualizada': fila['updated_at']}
                for fila in filas
            ]
        }
    finally:
        conn.close()


@router.get('/conversaciones/{conversacion_id}')
def obtener_conversacion(conversacion_id: int, usuario: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        conversacion = conn.execute('SELECT * FROM conversaciones WHERE id = ?', (conversacion_id,)).fetchone()
        if conversacion is None:
            raise HTTPException(status_code=404, detail='La conversación no existe.')
        if conversacion['usuario_id'] != usuario.get('id'):
            raise HTTPException(status_code=403, detail='No tienes permisos para ver esta conversación.')
        mensajes = conn.execute(
            'SELECT rol, contenido, created_at FROM mensajes WHERE conversacion_id = ? ORDER BY id',
            (conversacion_id,),
        ).fetchall()
        return {
            'conversacionId': conversacion_id,
            'mensajes': [
                {'rol': fila['rol'], 'contenido': fila['contenido'], 'fecha': fila['created_at']} for fila in mensajes
            ],
        }
    finally:
        conn.close()


@router.post('/mensajes')
def enviar_mensaje(payload: MensajeEntrada, usuario: dict[str, Any] = Depends(get_current_user)):
    """Guarda el mensaje del cliente, consulta a la IA y devuelve la respuesta."""
    texto = payload.mensaje.strip()
    if not texto:
        raise HTTPException(status_code=400, detail='Escribe un mensaje para el asistente.')
    if len(texto) > 1000:
        raise HTTPException(status_code=400, detail='El mensaje es demasiado largo (máximo 1000 caracteres).')

    momento = now_iso()
    conn = get_db_connection()
    try:
        conversacion_id = payload.conversacionId
        if conversacion_id is not None:
            conversacion = conn.execute('SELECT * FROM conversaciones WHERE id = ?', (conversacion_id,)).fetchone()
            if conversacion is None:
                raise HTTPException(status_code=404, detail='La conversación no existe.')
            if conversacion['usuario_id'] != usuario.get('id'):
                raise HTTPException(status_code=403, detail='No tienes permisos para continuar esta conversación.')
        else:
            cursor = conn.execute(
                'INSERT INTO conversaciones (usuario_id, titulo, created_at, updated_at) VALUES (?,?,?,?)',
                (usuario.get('id'), texto[:60], momento, momento),
            )
            conversacion_id = cursor.lastrowid

        conn.execute(
            'INSERT INTO mensajes (conversacion_id, rol, contenido, created_at) VALUES (?,?,?,?)',
            (conversacion_id, 'usuario', texto, momento),
        )
        conn.commit()

        previos = conn.execute(
            'SELECT rol, contenido FROM mensajes WHERE conversacion_id = ? ORDER BY id DESC LIMIT ?',
            (conversacion_id, HISTORIAL_MAXIMO),
        ).fetchall()
        historial = [
            {'role': 'user' if fila['rol'] == 'usuario' else 'assistant', 'content': fila['contenido']}
            for fila in reversed(previos)
        ]
        catalogo = _catalogo(conn)

        aviso = ''
        if api_key():
            try:
                respuesta = _consultar_ia(historial, catalogo)
                origen = 'ia'
            except HTTPException as fallo:
                # Si el proveedor de IA falla, el cliente igual merece una
                # respuesta: se contesta con el catálogo y el motivo técnico
                # viaja aparte, para poder diagnosticarlo sin dejar la pregunta
                # sin contestar.
                respuesta = _respuesta_local(texto, catalogo)
                origen = 'catalogo'
                aviso = str(fallo.detail)
        else:
            respuesta = _respuesta_local(texto, catalogo)
            origen = 'catalogo'

        conn.execute(
            'INSERT INTO mensajes (conversacion_id, rol, contenido, created_at) VALUES (?,?,?,?)',
            (conversacion_id, 'asistente', respuesta, now_iso()),
        )
        conn.execute('UPDATE conversaciones SET updated_at = ? WHERE id = ?', (now_iso(), conversacion_id))
        conn.commit()

        salida = {'conversacionId': conversacion_id, 'respuesta': respuesta, 'origen': origen}
        if aviso:
            salida['aviso'] = aviso
        return salida
    finally:
        conn.close()
