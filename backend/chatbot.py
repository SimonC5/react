"""Chatbot de atención al cliente conectado a un servicio de Inteligencia Artificial.

La clave del proveedor se lee de variables de entorno (``IA_API_KEY`` u
``OPENAI_API_KEY``) y nunca se expone en la respuesta ni se guarda en el
repositorio. Si no hay clave configurada, el chatbot responde con información
real del catálogo para que el módulo siga siendo usable.
"""

import json
import os
import re
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
# Un modelo cargado puede tardar bastante en escribir la primera palabra, y
# cortarle a los 20 segundos dejaba la pregunta sin responder sin que hiciera
# falta.
IA_TIMEOUT = float(os.getenv('IA_TIMEOUT', '30'))
# Segundos que se pueden gastar en total probando modelos, para no dejar al
# cliente esperando mientras se recorre la lista entera.
IA_PRESUPUESTO = float(os.getenv('IA_PRESUPUESTO', '55'))
# Errores que valen la pena reintentar con otro modelo: saturación, cupo por
# minuto, caídas pasajeras del proveedor y modelos que esa clave no tiene.
CODIGOS_REINTENTABLES = {404, 408, 429, 500, 502, 503, 504}
# De esos, los que son del momento y no del modelo: el mismo modelo puede
# contestar bien un rato después. Un 404 no está aquí porque el modelo no
# existe para esa clave y esperar no lo hace aparecer.
CODIGOS_PASAJEROS = {408, 429, 500, 502, 503, 504}
# Vueltas completas a la lista de modelos. El plan gratuito de Google avisa que
# la saturación "usually is temporary", y en la práctica basta con esperar unos
# segundos y volver a pedir: con una sola vuelta una racha corta de 503 dejaba
# la pregunta sin respuesta de IA aunque no hubiera nada roto.
IA_VUELTAS = max(1, int(os.getenv('IA_VUELTAS', '2')))
# Espera antes de volver a intentar con los modelos que estaban saturados.
IA_ESPERA_ENTRE_VUELTAS = float(os.getenv('IA_ESPERA_ENTRE_VUELTAS', '2'))
# Modelos de reserva de Google AI Studio, que es el proveedor que usa el
# proyecto. Si alguien deja un solo modelo escrito a mano (en la pestaña
# Environment del hosting, por ejemplo) y justo ese está saturado o tarda de
# más, sin reserva la pregunta se queda sin respuesta de IA aunque la misma
# clave tenga otros modelos libres. Van primero los livianos, que contestan
# rápido.
MODELOS_DE_RESERVA = (
    'gemini-flash-lite-latest',
    'gemini-flash-latest',
    'gemini-3.8-flash',
)
HISTORIAL_MAXIMO = 10


def _cadena_de_modelos() -> list[str]:
    """Modelos a intentar, en orden: los configurados y luego los de reserva.

    La reserva solo se agrega cuando el proveedor es Google, porque son nombres
    suyos; con otro proveedor se respeta exactamente lo que diga ``IA_MODEL``.
    """
    cadena = list(IA_MODELOS)
    if 'generativelanguage.googleapis.com' in IA_API_URL:
        cadena += [modelo for modelo in MODELOS_DE_RESERVA if modelo not in cadena]
    return cadena

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
    """Respuesta de respaldo cuando la IA no está disponible.

    No pretende contestar cualquier cosa como lo haría el modelo: lo que hace es
    reconocer los temas por los que de verdad pregunta un cliente de la tienda y
    responder con lo que el sistema sí sabe, para que nadie se quede sin nada.
    """
    texto = mensaje.lower()

    def menciona(*palabras: str) -> bool:
        return any(palabra in texto for palabra in palabras)

    if menciona('precio', 'cuánto', 'cuanto', 'costo', 'cuesta', 'valor', 'tarifa', 'vale'):
        return f'Estos son los precios vigentes de nuestro catálogo:\n{catalogo}'
    if menciona('queja', 'reclamo', 'pqr', 'petición', 'peticion', 'problema', 'demora', 'falla', 'dañad'):
        return (
            'Lamento el inconveniente. Puedes radicar una PQR desde tu panel, en la sección "PQR": '
            'registra el tipo, el asunto y la descripción, y luego consultas el estado con el número de radicado.'
        )
    if menciona('garant', 'devol', 'cambio', 'repar'):
        return (
            'Todos los visores se venden con garantía, y en el catálogo tenemos el servicio de garantía '
            'extendida si quieres ampliarla. Para un caso puntual radica una PQR desde tu panel y le hacemos '
            'seguimiento con número de radicado.'
        )
    if menciona('carrito', 'compr', 'pedido', 'contratar', 'cotiz', 'adquir'):
        return (
            'Puedes comprar tú mismo: agrega lo que quieras al carrito desde el catálogo, inicia sesión y '
            'confirma el pedido. La factura se emite sola y te queda en la sección "Mis facturas".'
        )
    if menciona('factura', 'facturas', 'descargar', 'recibo', 'pdf'):
        return 'Puedes consultar y descargar tus facturas en PDF desde el panel, en la sección "Mis facturas".'
    if menciona('instal', 'configur', 'capacit', 'soporte', 'servicio'):
        return f'Además de los visores ofrecemos servicios de instalación, capacitación y soporte:\n{catalogo}'
    if menciona('recomien', 'recomend', 'cuál me', 'cual me', 'mejor', 'sirve para', 'para jugar', 'para empresa'):
        return (
            'Con gusto. Estos son los visores y servicios que tenemos, con su descripción y su precio, para '
            f'que compares:\n{catalogo}'
        )
    if menciona('contacto', 'teléfono', 'telefono', 'correo', 'horario', 'ubicad', 'dirección', 'direccion'):
        return (
            'En la página de Contacto están nuestros datos y el formulario para escribirnos. Si tu caso es un '
            'reclamo, radícalo como PQR desde tu panel para hacerle seguimiento.'
        )
    if menciona('hola', 'buenas', 'buenos días', 'buenos dias', 'buenas tardes', 'qué tal', 'que tal'):
        return (
            '¡Hola! Soy el asistente de SimonC. Puedo orientarte sobre los visores de realidad virtual, '
            'nuestros servicios, los precios, tus facturas y las PQR.'
        )
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


def _modelo_sugerido(motivo: str, modelo_probado: str) -> str:
    """Modelo de repuesto que el propio proveedor nombra al jubilar uno.

    Google retira modelos cada tanto y lo avisa dentro del error 404: «This
    model models/gemini-2.0-flash is no longer available. Please update your
    code to use models/gemini-3.8-flash». Leer ese nombre y probarlo enseguida
    es lo que evita tener que venir a editar la lista de reserva cada vez que
    jubilan uno. El primer ``models/...`` del texto es el que acaba de fallar,
    así que se descarta.
    """
    for candidato in re.findall(r'models/([A-Za-z0-9._-]+)', motivo):
        if candidato != modelo_probado:
            return candidato
    return ''


class FalloDeIA(Exception):
    """Un intento fallido contra el proveedor, con el motivo ya legible."""

    def __init__(self, motivo: str, reintentable: bool, pasajero: bool = False):
        super().__init__(motivo)
        self.motivo = motivo
        # ¿Vale la pena seguir con el siguiente modelo?
        self.reintentable = reintentable
        # ¿Vale la pena volver a este mismo modelo dentro de un rato?
        self.pasajero = pasajero


def _pedir_al_modelo(modelo: str, historial: list[dict[str, str]], catalogo: str) -> str:
    """Un intento contra un modelo concreto del proveedor."""
    cuerpo = json.dumps({
        'model': modelo,
        'messages': [
            {'role': 'system', 'content': f'{INSTRUCCIONES}\n\nCatálogo disponible:\n{catalogo}'},
            *historial,
        ],
        'temperature': 0.4,
        # Alcanza de sobra para la respuesta más larga que da el asistente, que
        # es enumerar el catálogo entero. Subirlo más solo le da cuerda a los
        # modelos que razonan antes de escribir, y entonces tardan de más.
        'max_tokens': 1200,
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
        raise FalloDeIA(
            f'error {exc.code}. {_motivo_del_proveedor(exc)}'.strip(),
            reintentable=exc.code in CODIGOS_REINTENTABLES,
            pasajero=exc.code in CODIGOS_PASAJEROS,
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FalloDeIA(
            f'no contestó a tiempo ({IA_TIMEOUT:.0f} s) o no se pudo contactar.',
            reintentable=True,
            pasajero=True,
        ) from exc

    opciones = datos.get('choices') or []
    contenido = (opciones[0].get('message', {}).get('content') if opciones else '') or ''
    if not contenido.strip():
        raise FalloDeIA('devolvió una respuesta vacía.', reintentable=True, pasajero=True)
    return contenido.strip()


def _consultar_ia(historial: list[dict[str, str]], catalogo: str) -> str:
    """Pide la respuesta al proveedor, probando los modelos de ``IA_MODEL`` en orden.

    Los planes gratuitos se saturan: el modelo más pedido devuelve 503 y otro de
    la misma clave contesta a la primera. Por eso, ante un error pasajero se
    pasa al siguiente modelo en lugar de rendirse. Si el error es de la clave o
    de la petición, no tiene sentido insistir y se corta de una vez.

    Cuando la racha de saturación pilla a todos los modelos a la vez, se espera
    unos segundos y se vuelve a empezar: el propio proveedor dice que esos picos
    son pasajeros, y una segunda vuelta suele bastar.
    """
    inicio = time.monotonic()
    # Un renglón por modelo con lo último que le pasó, para que el aviso no se
    # repita cuando se dan varias vueltas.
    motivos: dict[str, str] = {}
    veces: dict[str, int] = {}
    corte_definitivo = False

    def queda_tiempo() -> bool:
        return time.monotonic() - inicio < IA_PRESUPUESTO

    por_probar = _cadena_de_modelos()
    for vuelta in range(IA_VUELTAS):
        if not por_probar:
            break
        if vuelta:
            if not queda_tiempo():
                motivos['(tiempo)'] = 'se acabó el tiempo antes de volver a intentar'
                break
            time.sleep(IA_ESPERA_ENTRE_VUELTAS)

        pendientes = list(por_probar)
        ya_probados: set[str] = set()
        pasajeros: list[str] = []

        while pendientes:
            modelo = pendientes.pop(0)
            if modelo in ya_probados:
                continue
            ya_probados.add(modelo)
            if veces and not queda_tiempo():
                motivos['(tiempo)'] = 'se acabó el tiempo antes de probar los demás'
                corte_definitivo = True
                break
            veces[modelo] = veces.get(modelo, 0) + 1
            try:
                return _pedir_al_modelo(modelo, historial, catalogo)
            except FalloDeIA as fallo:
                motivos[modelo] = fallo.motivo
                if fallo.pasajero:
                    pasajeros.append(modelo)
                if not fallo.reintentable:
                    corte_definitivo = True
                    break
                # Si el proveedor jubiló este modelo y nombró su reemplazo, ese
                # va de primero: es el que con más probabilidad contesta.
                sugerido = _modelo_sugerido(fallo.motivo, modelo)
                if sugerido and sugerido not in ya_probados:
                    pendientes.insert(0, sugerido)
                    if sugerido not in por_probar:
                        por_probar.append(sugerido)

        if corte_definitivo:
            break
        # Solo se repiten los que fallaron por estar saturados o lentos: volver
        # a pedirle a un modelo que no existe no lo hace aparecer.
        por_probar = pasajeros

    if not motivos:
        raise HTTPException(status_code=502, detail='No hay ningún modelo de Inteligencia Artificial configurado.')

    # El aviso enumera todos los intentos: con un solo motivo no se distingue
    # un modelo saturado de uno que tarda de más, y son problemas distintos.
    intentos = [
        f'{modelo}: {motivo}' + (f' (se intentó {veces[modelo]} veces)' if veces.get(modelo, 0) > 1 else '')
        for modelo, motivo in motivos.items()
    ]
    raise HTTPException(
        status_code=502,
        detail=('Esta respuesta salió del catálogo porque la IA no contestó. Intentos: ' + ' · '.join(intentos)),
    )


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
