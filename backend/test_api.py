"""Pruebas de la API del quinto avance.

Se ejecutan sobre una base de datos temporal, así que no tocan
``backend/data/simonsc.db``:

    pip install -r backend/requirements-dev.txt
    python -m pytest backend
"""

import inspect
import json
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import hashlib

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402
import correo  # noqa: E402

_TMP = Path(tempfile.mkdtemp())
core.DATA_DIR = _TMP
core.DB_PATH = _TMP / 'test.db'

import main  # noqa: E402
import pagos  # noqa: E402

main.DATA_DIR = _TMP
main.DB_PATH = _TMP / 'test.db'


@pytest.fixture(scope='module')
def client():
    with TestClient(main.app) as cliente:
        yield cliente


@pytest.fixture(scope='module')
def admin(client):
    respuesta = client.post('/api/auth/login', json={'email': 'admin@simonsc.com', 'password': 'Admin1234'})
    assert respuesta.status_code == 200, respuesta.text
    return {'Authorization': f"Bearer {respuesta.json()['token']}"}


@pytest.fixture(scope='module')
def venta(client, admin):
    productos = client.get('/api/products', headers=admin).json()['products']
    servicios = client.get('/api/services', headers=admin).json()['services']
    respuesta = client.post('/api/ventas', headers=admin, json={
        'cliente': 'Cliente de prueba',
        'clienteDocumento': '1111111111',
        'items': [
            {'tipo': 'producto', 'itemId': productos[0]['id'], 'cantidad': 2},
            {'tipo': 'servicio', 'itemId': servicios[0]['id'], 'cantidad': 1, 'descuento': 50000},
        ],
    })
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()['venta']


def test_health(client):
    assert client.get('/api/health').json()['status'] == 'ok'


def test_registro_de_venta_calcula_totales(venta):
    assert venta['numero'].startswith('VT-')
    assert len(venta['detalle']) == 2
    assert venta['total'] == pytest.approx(venta['subtotal'] + venta['impuestos'], rel=1e-6)


def test_venta_sin_items_es_rechazada(client, admin):
    respuesta = client.post('/api/ventas', headers=admin, json={'cliente': 'Nadie', 'items': []})
    assert respuesta.status_code == 400


def test_historial_filtra_por_cliente(client, admin, venta):
    encontradas = client.get('/api/ventas', headers=admin, params={'cliente': 'prueba'}).json()
    assert any(fila['numero'] == venta['numero'] for fila in encontradas['ventas'])
    vacio = client.get('/api/ventas', headers=admin, params={'cliente': 'no-existe'}).json()
    assert vacio['resumen']['cantidad'] == 0


def test_reporte_diario_se_exporta_en_pdf_y_excel(client, admin, venta):
    reporte = client.get('/api/reportes/ventas/diario', headers=admin).json()['reporte']
    assert reporte['totales']['ventas'] >= 1

    pdf = client.get('/api/reportes/ventas/diario.pdf', headers=admin)
    assert pdf.status_code == 200 and pdf.content[:4] == b'%PDF'

    excel = client.get('/api/reportes/ventas/diario.xlsx', headers=admin)
    assert excel.status_code == 200 and excel.content[:2] == b'PK'


def test_factura_se_genera_una_sola_vez_y_se_descarga(client, admin, venta):
    creada = client.post('/api/facturas', headers=admin, json={'ventaId': venta['id']})
    assert creada.status_code == 200, creada.text
    factura = creada.json()['factura']
    assert factura['numero'].startswith('FV-')
    assert factura['total'] == pytest.approx(venta['total'], rel=1e-6)

    repetida = client.post('/api/facturas', headers=admin, json={'ventaId': venta['id']})
    assert repetida.status_code == 409

    buscadas = client.get('/api/facturas', headers=admin, params={'numero': factura['numero']}).json()['facturas']
    assert len(buscadas) == 1

    pdf = client.get(f"/api/facturas/{factura['id']}/pdf", headers=admin)
    assert pdf.status_code == 200 and pdf.content[:4] == b'%PDF'


@pytest.mark.parametrize('agrupacion', ['dia', 'semana', 'mes'])
def test_dashboard_entrega_series_por_periodo(client, admin, agrupacion, venta):
    datos = client.get('/api/dashboard/ventas', headers=admin, params={'agrupacion': agrupacion}).json()
    assert datos['barras'] and datos['lineal']
    assert len(datos['barras']) == len(datos['lineal'])


def test_dashboard_rechaza_agrupacion_desconocida(client, admin):
    assert client.get('/api/dashboard/ventas', headers=admin, params={'agrupacion': 'anio'}).status_code == 400


def test_resumen_del_administrador_incluye_usuarios(client, admin):
    claves = {tarjeta['clave'] for tarjeta in client.get('/api/dashboard/resumen', headers=admin).json()['tarjetas']}
    assert {'ventas', 'facturacion', 'facturas', 'pqrPendientes', 'usuarios'} <= claves


def test_ciclo_de_una_pqr(client, admin):
    creada = client.post('/api/pqr', headers=admin, json={
        'tipo': 'Queja', 'asunto': 'Prueba', 'descripcion': 'Descripción de prueba',
    })
    assert creada.status_code == 200, creada.text
    registro = creada.json()['pqr']
    assert registro['estado'] == 'Pendiente'

    actualizada = client.patch(f"/api/pqr/{registro['id']}", headers=admin, json={
        'estado': 'Respondida', 'respuesta': 'Caso resuelto.',
    }).json()['pqr']
    assert actualizada['estado'] == 'Respondida'
    assert actualizada['respuesta'] == 'Caso resuelto.'

    assert client.patch(f"/api/pqr/{registro['id']}", headers=admin, json={'estado': 'Inventado'}).status_code == 400


def test_chatbot_responde_y_guarda_la_conversacion(client, admin):
    assert client.get('/api/chatbot/estado', headers=admin).json()['iaHabilitada'] in (True, False)

    primera = client.post('/api/chatbot/mensajes', headers=admin, json={'mensaje': '¿Cuánto cuesta el branding?'})
    assert primera.status_code == 200, primera.text
    conversacion_id = primera.json()['conversacionId']

    client.post('/api/chatbot/mensajes', headers=admin, json={
        'mensaje': 'Quiero poner una queja', 'conversacionId': conversacion_id,
    })
    mensajes = client.get(f'/api/chatbot/conversaciones/{conversacion_id}', headers=admin).json()['mensajes']
    assert len(mensajes) == 4


def test_el_nombre_interno_del_hosting_se_vuelve_dominio_publico(monkeypatch):
    """Al enlazar servicios, Render entrega "simonc-web", no el dominio real."""
    import core

    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME', 'simonc-api.onrender.com')

    assert core.dominio_publico('simonc-web') == 'https://simonc-web.onrender.com'
    assert core.dominio_publico('https://simonc-web/') == 'https://simonc-web.onrender.com'
    # Un dominio completo no se toca, y tampoco el backend de casa.
    assert core.dominio_publico('https://simonc-web.onrender.com/') == 'https://simonc-web.onrender.com'
    assert core.dominio_publico('http://localhost:5173') == 'http://localhost:5173'
    assert core.dominio_publico('') == ''


def test_sin_hosting_conocido_el_nombre_interno_se_deja_igual(monkeypatch):
    """Fuera de Render no hay sufijo que agregar: no hay que inventarse uno."""
    import core

    monkeypatch.delenv('RENDER_EXTERNAL_HOSTNAME', raising=False)
    monkeypatch.delenv('RENDER_EXTERNAL_URL', raising=False)

    assert core.dominio_publico('simonc-web') == 'https://simonc-web'


def test_el_chatbot_explica_el_error_del_proveedor(monkeypatch):
    """Un 404 a secas no dice nada: hay que reenviar el motivo, sin la clave."""
    import io
    import urllib.error

    import chatbot

    cuerpo = json.dumps([{'error': {
        'code': 404,
        'message': 'models/gemini-inexistente is not found for API version v1beta. clave-secreta',
    }}]).encode('utf-8')
    fallo = urllib.error.HTTPError(
        chatbot.IA_API_URL, 404, 'Not Found', {}, io.BytesIO(cuerpo),
    )

    monkeypatch.setenv('IA_API_KEY', 'clave-secreta')
    motivo = chatbot._motivo_del_proveedor(fallo)

    assert 'models/gemini-inexistente is not found' in motivo
    # La clave nunca viaja al navegador, ni siquiera dentro del error.
    assert 'clave-secreta' not in motivo


def test_el_chatbot_cambia_de_modelo_cuando_el_primero_esta_saturado(monkeypatch):
    """Un 503 del modelo de moda no debe tumbar la respuesta: hay más modelos."""
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        if modelo == 'saturado':
            raise chatbot.FalloDeIA(
                'El servicio de Inteligencia Artificial respondió con error 503. '
                'Dice: This model is currently experiencing high demand.',
                reintentable=True,
            )
        return 'Con gusto te ayudo.'

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['saturado', 'de-reserva'])
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    assert chatbot._consultar_ia([], 'catálogo') == 'Con gusto te ayudo.'
    assert intentados == ['saturado', 'de-reserva']


def test_hay_modelos_de_reserva_aunque_este_configurado_uno_solo(monkeypatch):
    """Escribir un solo modelo a mano no debe dejar al chatbot sin IA."""
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        if modelo == 'gemini-flash-latest':
            raise chatbot.FalloDeIA('no contestó a tiempo (20 s) o no se pudo contactar.', reintentable=True)
        return 'Con gusto te ayudo.'

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['gemini-flash-latest'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions')
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    assert chatbot._consultar_ia([], 'catálogo') == 'Con gusto te ayudo.'
    # Se intentó el configurado y después uno de reserva, sin repetirlo.
    assert intentados[0] == 'gemini-flash-latest'
    assert len(intentados) == 2
    assert intentados[1] in chatbot.MODELOS_DE_RESERVA


def test_el_chatbot_usa_el_modelo_que_sugiere_el_proveedor(monkeypatch):
    """Cuando Google jubila un modelo, nombra el reemplazo dentro del error 404.

    Leerlo y probarlo enseguida es lo que evita que el chatbot se quede sin IA
    cada vez que el proveedor retira un modelo de la lista configurada.
    """
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        if modelo == 'gemini-viejo':
            raise chatbot.FalloDeIA(
                'error 404. Dice: This model models/gemini-viejo is no longer available. '
                'Please update your code to use models/gemini-nuevo for the latest features.',
                reintentable=True,
            )
        return 'Con gusto te ayudo.'

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['gemini-viejo'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions')
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    assert chatbot._consultar_ia([], 'catálogo') == 'Con gusto te ayudo.'
    # El sugerido se prueba de inmediato, antes que los de reserva.
    assert intentados == ['gemini-viejo', 'gemini-nuevo']


def test_el_modelo_sugerido_no_es_el_que_acaba_de_fallar():
    """El aviso del proveedor nombra dos modelos: el que falló y su reemplazo."""
    import chatbot

    motivo = (
        'error 404. Dice: This model models/gemini-2.0-flash is no longer available. '
        'Please update your code to use models/gemini-3.8-flash for the latest features.'
    )
    assert chatbot._modelo_sugerido(motivo, 'gemini-2.0-flash') == 'gemini-3.8-flash'
    # Sin sugerencia no se inventa ninguna.
    assert chatbot._modelo_sugerido('error 503. Dice: high demand.', 'gemini-2.0-flash') == ''


def test_ningun_modelo_se_intenta_dos_veces(monkeypatch):
    """La sugerencia no debe hacer que se repita un modelo ya probado."""
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        raise chatbot.FalloDeIA(
            f'error 404. Dice: This model models/{modelo} is no longer available. '
            'Please update your code to use models/gemini-flash-latest instead.',
            reintentable=True,
        )

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['uno', 'dos'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions')
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    with pytest.raises(HTTPException):
        chatbot._consultar_ia([], 'catálogo')

    assert len(intentados) == len(set(intentados))


def test_el_chatbot_da_una_segunda_vuelta_cuando_todo_esta_saturado(monkeypatch):
    """Una racha de 503 es pasajera: el propio Google dice que esperes y reintentes."""
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        # Todos saturados en la primera vuelta; en la segunda ya contestan.
        if len(intentados) <= 2:
            raise chatbot.FalloDeIA(
                'error 503. Dice: This model is currently experiencing high demand.',
                reintentable=True,
                pasajero=True,
            )
        return 'Con gusto te ayudo.'

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['uno', 'dos'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://api.groq.com/openai/v1/chat/completions')
    monkeypatch.setattr(chatbot, 'IA_ESPERA_ENTRE_VUELTAS', 0)
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    assert chatbot._consultar_ia([], 'catálogo') == 'Con gusto te ayudo.'
    assert intentados == ['uno', 'dos', 'uno']


def test_la_segunda_vuelta_no_repite_los_modelos_que_no_existen(monkeypatch):
    """Volver a pedirle a un modelo jubilado no lo hace aparecer."""
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        if modelo == 'jubilado':
            raise chatbot.FalloDeIA('error 404. Dice: no longer available.', reintentable=True, pasajero=False)
        raise chatbot.FalloDeIA(
            'error 503. Dice: high demand.', reintentable=True, pasajero=True,
        )

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['jubilado', 'saturado'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://api.groq.com/openai/v1/chat/completions')
    monkeypatch.setattr(chatbot, 'IA_ESPERA_ENTRE_VUELTAS', 0)
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    with pytest.raises(HTTPException):
        chatbot._consultar_ia([], 'catálogo')

    # El jubilado se intentó una sola vez; el saturado, en las dos vueltas.
    assert intentados == ['jubilado', 'saturado', 'saturado']


def test_el_aviso_no_repite_el_mismo_modelo_en_cada_vuelta(monkeypatch):
    """Con varias vueltas el aviso debe seguir siendo un renglón por modelo."""
    import chatbot

    def responder(modelo, historial, catalogo):
        raise chatbot.FalloDeIA('error 503. Dice: high demand.', reintentable=True, pasajero=True)

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['uno'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://api.groq.com/openai/v1/chat/completions')
    monkeypatch.setattr(chatbot, 'IA_ESPERA_ENTRE_VUELTAS', 0)
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    with pytest.raises(HTTPException) as fallo:
        chatbot._consultar_ia([], 'catálogo')

    aviso = fallo.value.detail
    assert aviso.count('uno:') == 1
    assert 'se intentó 2 veces' in aviso


def test_los_modelos_de_reserva_son_solo_para_google(monkeypatch):
    """Con otro proveedor, los nombres de Google no significan nada."""
    import chatbot

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['llama-3.1-8b-instant'])
    monkeypatch.setattr(chatbot, 'IA_API_URL', 'https://api.groq.com/openai/v1/chat/completions')

    assert chatbot._cadena_de_modelos() == ['llama-3.1-8b-instant']


def test_el_aviso_dice_que_paso_con_cada_modelo(monkeypatch):
    """Un solo motivo no distingue un modelo saturado de uno que tarda de más."""
    import chatbot

    motivos = {
        'saturado': 'error 503. Dice: This model is currently experiencing high demand.',
        'lento': 'no contestó a tiempo (30 s) o no se pudo contactar.',
    }

    def responder(modelo, historial, catalogo):
        raise chatbot.FalloDeIA(motivos[modelo], reintentable=True)

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['saturado', 'lento'])
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    with pytest.raises(HTTPException) as fallo:
        chatbot._consultar_ia([], 'catálogo')

    detalle = fallo.value.detail
    assert 'saturado: error 503' in detalle
    assert 'lento: no contestó a tiempo' in detalle


def test_el_respaldo_reconoce_los_temas_de_la_tienda():
    """Sin IA, el asistente igual tiene que responder lo que la tienda sí sabe."""
    import chatbot

    catalogo = '- Producto: SimonC Vision One ($ 2.950.000). Visor de entrada.'
    casos = {
        '¿cómo compro unas gafas?': 'carrito',
        '¿dan garantía?': 'garantía',
        '¿me instalan el equipo?': 'instalación',
        '¿dónde veo mis facturas?': 'Mis facturas',
        'quiero poner una queja': 'PQR',
        '¿cuál es el horario?': 'Contacto',
    }
    for pregunta, esperado in casos.items():
        assert esperado in chatbot._respuesta_local(pregunta, catalogo), pregunta

    # Lo que no reconoce no se queda sin respuesta: muestra el catálogo.
    assert 'SimonC Vision One' in chatbot._respuesta_local('¿el universo es infinito?', catalogo)


def test_el_chatbot_no_insiste_si_la_clave_esta_mala(monkeypatch):
    """Un 400 por clave inválida no se arregla probando otro modelo."""
    import chatbot

    intentados = []

    def responder(modelo, historial, catalogo):
        intentados.append(modelo)
        raise chatbot.FalloDeIA(
            'El servicio de Inteligencia Artificial respondió con error 400. '
            'Dice: Please pass a valid API key',
            reintentable=False,
        )

    monkeypatch.setattr(chatbot, 'IA_MODELOS', ['uno', 'dos', 'tres'])
    monkeypatch.setattr(chatbot, '_pedir_al_modelo', responder)

    with pytest.raises(HTTPException) as fallo:
        chatbot._consultar_ia([], 'catálogo')

    assert 'valid API key' in fallo.value.detail
    assert intentados == ['uno']


def test_el_chatbot_contesta_aunque_la_ia_falle(client, admin, monkeypatch):
    """Si el proveedor de IA falla, el cliente igual recibe una respuesta útil."""
    import chatbot

    def revienta(historial, catalogo):
        raise HTTPException(status_code=502, detail='El servicio de IA respondió con error 429.')

    monkeypatch.setenv('IA_API_KEY', 'clave-de-prueba')
    monkeypatch.setattr(chatbot, '_consultar_ia', revienta)

    respuesta = client.post('/api/chatbot/mensajes', headers=admin, json={'mensaje': 'Quiero poner una queja'})

    assert respuesta.status_code == 200
    datos = respuesta.json()
    # La pregunta no se queda sin contestar...
    assert 'PQR' in datos['respuesta']
    assert datos['origen'] == 'catalogo'
    # ...y el motivo técnico sigue disponible para diagnosticar.
    assert '429' in datos['aviso']


def test_el_chatbot_no_expone_la_api_key(client, admin):
    cuerpo = client.get('/api/chatbot/estado', headers=admin).text
    assert 'sk-' not in cuerpo


def test_el_documento_solo_acepta_numeros(client, admin):
    """Ni el registro público ni el panel deben dejar pasar letras."""
    registro = client.post('/api/auth/register', json={
        'name': 'Con', 'lastName': 'Letras', 'documentType': 'CC', 'documentNumber': '12AB5678',
        'address': 'Calle 3 #45-67', 'phone': '3001234567', 'email': 'con.letras@simonsc.com', 'password': 'Cliente1234',
    })
    assert registro.status_code == 422, registro.text

    desde_el_panel = client.post('/api/users', headers=admin, json={
        'name': 'Con', 'lastName': 'Letras', 'documentType': 'CC', 'documentNumber': '12AB5678',
        'address': 'Calle 3 #45-67', 'phone': '3001234567', 'email': 'panel.letras@simonsc.com',
        'password': 'Cliente1234', 'role': 'Cliente',
    })
    assert desde_el_panel.status_code == 400, desde_el_panel.text
    assert 'dígitos' in desde_el_panel.json()['detail']


def test_el_dashboard_es_solo_del_administrador(client, admin):
    """Esconder el botón no basta: la ruta también tiene que estar cerrada."""
    client.post('/api/auth/register', json={
        'name': 'Otro', 'lastName': 'Cliente', 'documentType': 'CC', 'documentNumber': '8888888888',
        'address': 'Calle 2 #34-56', 'phone': '3009998877', 'email': 'otro.cliente@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'otro.cliente@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}
    token_empleado = client.post('/api/auth/login', json={
        'email': 'empleado@simonsc.com', 'password': 'Empleado1234',
    }).json()['token']
    empleado = {'Authorization': f'Bearer {token_empleado}'}

    for ruta in ('/api/dashboard/resumen', '/api/dashboard/ventas', '/api/dashboard/filtros'):
        assert client.get(ruta, headers=cliente).status_code == 403, ruta
        assert client.get(ruta, headers=empleado).status_code == 403, ruta
        assert client.get(ruta, headers=admin).status_code == 200, ruta


def test_permisos_por_rol(client, admin):
    client.post('/api/auth/register', json={
        'name': 'Cliente', 'lastName': 'Demo', 'documentType': 'CC', 'documentNumber': '9999999999',
        'address': 'Calle 1 #23-45', 'phone': '3001112233', 'email': 'cliente.demo@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'cliente.demo@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}

    assert client.post('/api/ventas', headers=cliente, json={'cliente': 'x', 'items': []}).status_code == 403
    assert client.get('/api/reportes/ventas/diario', headers=cliente).status_code == 403
    assert client.get('/api/ventas', headers=cliente).json()['resumen']['cantidad'] == 0
    assert client.get('/api/dashboard/resumen', headers=cliente).status_code == 403
    assert client.get('/api/ventas').status_code == 401


def test_el_catalogo_publico_no_pide_sesion(client):
    datos = client.get('/api/catalogo')
    assert datos.status_code == 200, datos.text
    cuerpo = datos.json()
    assert {'id', 'name', 'description', 'price'} == set(cuerpo['productos'][0])
    # La tienda es de realidad virtual: veinte visores y veinte servicios.
    assert len(cuerpo['productos']) >= 20
    assert len(cuerpo['servicios']) >= 20
    # El catálogo genérico del avance anterior queda oculto.
    nombres = {fila['name'] for fila in cuerpo['productos']} | {fila['name'] for fila in cuerpo['servicios']}
    assert 'Branding Premium' not in nombres and 'Desarrollo web' not in nombres


def test_el_cliente_no_ve_el_catalogo_retirado(client, admin):
    """Quien administra ve todo el catálogo; el cliente solo lo publicado."""
    client.post('/api/auth/register', json={
        'name': 'Cata', 'lastName': 'Logo', 'documentType': 'CC', 'documentNumber': '6161616161',
        'address': 'Calle 4 #56-78', 'phone': '3006161616', 'email': 'catalogo@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'catalogo@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}

    creado = client.post('/api/products', headers=admin, json={
        'name': 'Visor descontinuado', 'description': 'Ya no se vende.', 'price': 100000,
    })
    assert creado.status_code == 201, creado.text
    producto_id = creado.json()['id']
    client.patch(f'/api/products/{producto_id}/status', headers=admin, json={'active': False})

    del_admin = client.get('/api/products', headers=admin).json()['products']
    del_cliente = client.get('/api/products', headers=cliente).json()['products']
    assert any(fila['name'] == 'Visor descontinuado' for fila in del_admin)
    assert all(fila['active'] for fila in del_cliente)
    assert len(del_cliente) < len(del_admin)
    # Y tampoco aparece en la tienda pública.
    publicos = client.get('/api/catalogo').json()['productos']
    assert all(fila['name'] != 'Visor descontinuado' for fila in publicos)


def test_el_cliente_pide_su_carrito_a_su_propio_nombre(client, admin):
    """El pedido toma el comprador del token y el precio del catálogo."""
    client.post('/api/auth/register', json={
        'name': 'Carro', 'lastName': 'Cliente', 'documentType': 'CC', 'documentNumber': '7070707070',
        'address': 'Calle 3 #45-67', 'phone': '3007070707', 'email': 'carrito@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'carrito@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}

    catalogo = client.get('/api/catalogo').json()
    producto = catalogo['productos'][0]

    respuesta = client.post('/api/ventas/pedido', headers=cliente, json={
        'items': [{'tipo': 'producto', 'itemId': producto['id'], 'cantidad': 2}],
    })
    assert respuesta.status_code == 200, respuesta.text
    venta = respuesta.json()['venta']
    assert venta['cliente'] == 'Carro Cliente'
    # El precio sale del catálogo, no del navegador.
    assert venta['detalle'][0]['precioUnitario'] == producto['price']
    assert venta['subtotal'] == pytest.approx(producto['price'] * 2)

    # Y el cliente solo ve esa compra en su historial.
    historial = client.get('/api/ventas', headers=cliente).json()
    assert [fila['numero'] for fila in historial['ventas']] == [venta['numero']]

    # La factura sale con el pedido: nadie tiene que generarla a mano.
    factura = respuesta.json()['factura']
    assert factura is not None and factura['total'] == venta['total']
    mis_facturas = client.get('/api/facturas', headers=cliente).json()['facturas']
    assert [fila['numero'] for fila in mis_facturas] == [factura['numero']]

    # Un artículo inexistente no crea la venta.
    assert client.post('/api/ventas/pedido', headers=cliente, json={
        'items': [{'tipo': 'producto', 'itemId': 99999, 'cantidad': 1}],
    }).status_code == 400
    assert client.post('/api/ventas/pedido', json={'items': []}).status_code == 401


def test_recuperacion_de_clave_genera_enlace_y_permite_cambiarla(client, capsys):
    """Sin SMTP el enlace se imprime; con ese token se cambia la contraseña."""
    correo = 'recupera@simonsc.com'
    alta = client.post('/api/auth/register', json={
        'name': 'Reco', 'lastName': 'Pera', 'documentType': 'CC', 'documentNumber': '4545454545',
        'address': 'Calle siempre viva 123', 'phone': '3001112233',
        'email': correo, 'password': 'Clave1234', 'confirmPassword': 'Clave1234',
    })
    assert alta.status_code == 201, alta.text

    solicitud = client.post('/api/auth/recover', json={'email': correo})
    assert solicitud.status_code == 200
    # El token jamás viaja en la respuesta: solo por correo o por consola.
    assert 'token' not in solicitud.text

    impreso = capsys.readouterr().out
    assert 'reset-password?token=' in impreso
    token = impreso.split('reset-password?token=')[1].split()[0]

    corta = client.post('/api/auth/reset-password', json={'token': token, 'password': 'abc'})
    assert corta.status_code == 400

    cambio = client.post('/api/auth/reset-password', json={'token': token, 'password': 'NuevaClave9'})
    assert cambio.status_code == 200, cambio.text

    # El mismo enlace no sirve dos veces.
    repetido = client.post('/api/auth/reset-password', json={'token': token, 'password': 'OtraClave9'})
    assert repetido.status_code == 400

    assert client.post('/api/auth/login', json={'email': correo, 'password': 'Clave1234'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': correo, 'password': 'NuevaClave9'}).status_code == 200


def test_recuperacion_de_un_correo_inexistente_responde_igual(client):
    """No se puede averiguar qué correos están registrados."""
    respuesta = client.post('/api/auth/recover', json={'email': 'nadie@simonsc.com'})
    assert respuesta.status_code == 200
    assert respuesta.json()['message'] == 'Si el correo existe, recibirás instrucciones para recuperar tu cuenta.'


def test_la_traduccion_a_mysql_respeta_el_sql_de_sqlite():
    """El SQL se escribe una sola vez y se adapta al motor en core.py."""
    assert core._traducir('SELECT * FROM ventas WHERE id = ?') == 'SELECT * FROM ventas WHERE id = %s'
    assert core._traducir('INSERT OR IGNORE INTO roles (name) VALUES (?)') == (
        'INSERT IGNORE INTO roles (name) VALUES (%s)'
    )


def test_las_filas_se_leen_por_nombre_y_por_posicion():
    """El resto del backend usa las dos formas, como con sqlite3.Row."""
    fila = core.Fila([('total', 3), ('estado', 'Registrada')])
    assert fila['total'] == 3
    assert fila[0] == 3
    assert fila[1] == 'Registrada'


def test_los_valores_de_mysql_quedan_como_los_de_sqlite():
    """Decimal y datetime se normalizan para que el JSON no cambie de forma."""
    from datetime import datetime as _dt
    from decimal import Decimal as _Dec

    assert core._normalizar(_Dec('1500.50')) == 1500.5
    assert core._normalizar(_dt(2026, 9, 21, 15, 4, 5, 123456)) == '2026-09-21 15:04:05'


@pytest.mark.skipif(not core.usa_mysql(), reason='solo aplica cuando se corre contra MySQL')
def test_mysql_no_deja_resultados_sin_leer():
    """Con la extensión en C, una fila sin leer rompe la consulta siguiente."""
    conn = core.get_db_connection()
    try:
        cursor = conn.execute('SELECT id, name FROM productos')
        cursor.fetchone()  # a propósito se lee solo la primera de varias filas
        assert conn._conexion.unread_result is False
        assert conn.execute('SELECT COUNT(*) AS total FROM productos').fetchone()['total'] >= 0
    finally:
        conn.close()


@pytest.mark.skipif(not core.usa_mysql(), reason='solo aplica cuando se corre contra MySQL')
def test_mysql_informa_cuantas_filas_toco():
    """Sin "rowcount" el panel no podía editar ni desactivar nada en MySQL."""
    conn = core.get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO productos (name, description, price, active) VALUES (?,?,?,1)',
            ('Producto de prueba rowcount', 'Temporal.', 1000),
        )
        creado = cursor.lastrowid
        # Se escribe el mismo valor a propósito: con FOUND_ROWS cuenta igual.
        assert conn.execute('UPDATE productos SET active = 1 WHERE id = ?', (creado,)).rowcount == 1
        assert conn.execute('UPDATE productos SET active = 0 WHERE id = ?', (-1,)).rowcount == 0
        assert conn.execute('DELETE FROM productos WHERE id = ?', (creado,)).rowcount == 1
        conn.commit()
    finally:
        conn.close()


@pytest.mark.skipif(not core.usa_mysql(), reason='solo aplica cuando se corre contra MySQL')
def test_mysql_crea_la_base_si_no_existe(monkeypatch):
    """Borrar la base en phpMyAdmin no debe dejar el backend sin arrancar."""
    parametros = core._parametros_mysql()
    efimera = 'simonsc_tmp_creacion'

    import mysql.connector

    servidor = mysql.connector.connect(
        **{k: v for k, v in parametros.items() if k != 'database'}, autocommit=True
    )
    cursor = servidor.cursor()
    cursor.execute(f'DROP DATABASE IF EXISTS `{efimera}`')
    cursor.close()
    servidor.close()

    monkeypatch.setattr(core, '_parametros_mysql', lambda: {**parametros, 'database': efimera})
    conn = core.get_db_connection()
    try:
        assert conn.execute('SELECT DATABASE() AS actual').fetchone()['actual'] == efimera
    finally:
        conn.close()

    servidor = mysql.connector.connect(
        **{k: v for k, v in parametros.items() if k != 'database'}, autocommit=True
    )
    cursor = servidor.cursor()
    cursor.execute(f'DROP DATABASE IF EXISTS `{efimera}`')
    cursor.close()
    servidor.close()


def _cuenta_de_cliente(client, correo, documento):
    """Crea un Cliente y devuelve su cabecera de autorización."""
    client.post('/api/auth/register', json={
        'name': 'Ana', 'lastName': 'Ramírez', 'documentType': 'CC',
        'documentNumber': documento, 'phone': '3001234567',
        'address': 'Calle 45 numero 12-30', 'email': correo,
        'password': 'Cliente1234',
    })
    respuesta = client.post('/api/auth/login', json={'email': correo, 'password': 'Cliente1234'})
    assert respuesta.status_code == 200, respuesta.text
    return {'Authorization': f"Bearer {respuesta.json()['token']}"}


def _venta_de_mostrador(client, admin, documento):
    """Venta registrada en el panel a nombre de un documento, sin cuenta."""
    productos = client.get('/api/products', headers=admin).json()['products']
    respuesta = client.post('/api/ventas', headers=admin, json={
        'cliente': 'Comprador de mostrador',
        'clienteDocumento': documento,
        'items': [{'tipo': 'producto', 'itemId': productos[0]['id'], 'cantidad': 1}],
    })
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()['venta']


def test_el_cliente_puede_abrir_la_venta_que_ve_en_su_historial(client, admin):
    """Una venta de mostrador se empareja por documento: el detalle también.

    El historial lista las ventas del Cliente por ``cliente_id`` o por
    documento, pero el detalle solo miraba ``cliente_id``: la venta salía en
    "Mis compras" y al pulsar "Detalle" respondía 403.
    """
    documento = '1122334455'
    cliente = _cuenta_de_cliente(client, 'ana.mostrador@correo.com', documento)
    venta = _venta_de_mostrador(client, admin, documento)

    historial = client.get('/api/ventas', headers=cliente).json()['ventas']
    assert any(item['id'] == venta['id'] for item in historial), 'debería salir en su historial'

    detalle = client.get(f"/api/ventas/{venta['id']}", headers=cliente)
    assert detalle.status_code == 200, detalle.text


def test_el_cliente_baja_el_pdf_de_la_factura_que_ve(client, admin):
    """La factura de esa misma venta tiene que abrirse y descargarse igual."""
    documento = '2233445566'
    cliente = _cuenta_de_cliente(client, 'ana.factura@correo.com', documento)
    venta = _venta_de_mostrador(client, admin, documento)

    emitida = client.post('/api/facturas', headers=admin, json={'ventaId': venta['id']})
    assert emitida.status_code == 200, emitida.text
    factura_id = emitida.json()['factura']['id']

    assert client.get(f'/api/facturas/{factura_id}', headers=cliente).status_code == 200
    pdf = client.get(f'/api/facturas/{factura_id}/pdf', headers=cliente)
    assert pdf.status_code == 200
    assert pdf.content[:4] == b'%PDF'


def test_un_cliente_sigue_sin_ver_las_ventas_de_otro(client, admin):
    """Emparejar por documento no debe abrirle la puerta a nadie más."""
    intruso = _cuenta_de_cliente(client, 'luis.ajeno@correo.com', '9988776655')
    ajena = _venta_de_mostrador(client, admin, '5555555555')

    assert client.get(f"/api/ventas/{ajena['id']}", headers=intruso).status_code == 403


def _radicar_pqr(client, cabecera, asunto='Demora en el envío'):
    respuesta = client.post('/api/pqr', headers=cabecera, json={
        'tipo': 'Queja', 'asunto': asunto,
        'descripcion': 'El pedido no ha llegado y ya pasó la fecha.',
    })
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()['pqr']


def test_responder_una_pqr_la_marca_respondida_y_avisa_al_cliente(client, admin):
    """Un solo botón: guarda la respuesta, cambia el estado y notifica."""
    cliente = _cuenta_de_cliente(client, 'ana.pqr@correo.com', '4455667788')
    solicitud = _radicar_pqr(client, cliente)

    enviada = client.post(
        f"/api/pqr/{solicitud['id']}/responder",
        headers=admin,
        json={'respuesta': 'Tu pedido sale mañana, disculpa la demora.'},
    )
    assert enviada.status_code == 200, enviada.text
    datos = enviada.json()
    assert datos['pqr']['estado'] == 'Respondida'
    assert datos['pqr']['respuesta'] == 'Tu pedido sale mañana, disculpa la demora.'
    # Sin SMTP configurado no sale correo, pero la respuesta queda guardada.
    assert datos['correoEnviado'] is False
    assert 'panel' in datos['message']

    # Y el cliente la ve en su propia consulta.
    suyas = client.get('/api/pqr', headers=cliente).json()['pqr']
    mia = next(item for item in suyas if item['id'] == solicitud['id'])
    assert mia['respuesta'] == 'Tu pedido sale mañana, disculpa la demora.'


def test_no_se_envia_una_respuesta_vacia(client, admin):
    """Pulsar enviar sin escribir nada no debe marcar la PQR como respondida."""
    cliente = _cuenta_de_cliente(client, 'ana.vacia@correo.com', '5566778899')
    solicitud = _radicar_pqr(client, cliente, asunto='Consulta de garantía')

    fallo = client.post(f"/api/pqr/{solicitud['id']}/responder", headers=admin, json={'respuesta': '   '})
    assert fallo.status_code == 400

    sigue = client.get(f"/api/pqr/{solicitud['id']}", headers=admin).json()['pqr']
    assert sigue['estado'] != 'Respondida'


def test_un_cliente_no_puede_responder_pqr(client):
    """Responder es de Administrador y Empleado."""
    cliente = _cuenta_de_cliente(client, 'ana.intrusa@correo.com', '6677889900')
    solicitud = _radicar_pqr(client, cliente, asunto='Otra consulta')

    negado = client.post(f"/api/pqr/{solicitud['id']}/responder", headers=cliente, json={'respuesta': 'Yo me respondo'})
    assert negado.status_code == 403


VARIABLES_DE_CORREO = (
    'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_FROM', 'SMTP_USE_TLS', 'SMTP_USE_SSL',
    'EMAIL_API_KEY', 'EMAIL_FROM', 'EMAIL_API_URL', 'RENDER', 'RENDER_EXTERNAL_HOSTNAME',
)


def _sin_correo_configurado(monkeypatch):
    """Deja el entorno como el de un computador sin servidor de correo."""
    for nombre in VARIABLES_DE_CORREO:
        monkeypatch.delenv(nombre, raising=False)


def _servidor_de_correo_falso(recibidos):
    """Un SMTP mínimo en un puerto libre, para probar el envío de verdad.

    Habla lo suficiente para que ``smtplib`` complete un envío: saludo, AUTH
    PLAIN, DATA y QUIT. Guarda en ``recibidos`` el correo tal como llegó.
    """
    escucha = socket.socket()
    escucha.bind(('127.0.0.1', 0))
    escucha.listen(1)
    puerto = escucha.getsockname()[1]

    def atender():
        conexion, _ = escucha.accept()
        with conexion, escucha:
            lector = conexion.makefile('rb')
            conexion.sendall(b'220 prueba ESMTP\r\n')
            cuerpo, en_cuerpo = [], False
            while True:
                linea = lector.readline()
                if not linea:
                    break
                if en_cuerpo:
                    if linea.strip() == b'.':
                        en_cuerpo = False
                        conexion.sendall(b'250 recibido\r\n')
                    else:
                        cuerpo.append(linea)
                    continue
                orden = linea.upper()
                if orden.startswith(b'EHLO'):
                    conexion.sendall(b'250-prueba\r\n250 AUTH PLAIN\r\n')
                elif orden.startswith(b'AUTH'):
                    conexion.sendall(b'235 autenticado\r\n')
                elif orden.startswith(b'DATA'):
                    en_cuerpo = True
                    conexion.sendall(b'354 escribe el mensaje\r\n')
                elif orden.startswith(b'QUIT'):
                    conexion.sendall(b'221 adios\r\n')
                    break
                else:
                    conexion.sendall(b'250 listo\r\n')
            recibidos.append(b''.join(cuerpo))

    hilo = threading.Thread(target=atender, daemon=True)
    hilo.start()
    return puerto, hilo


def _apuntar_al_servidor_falso(monkeypatch, puerto):
    _sin_correo_configurado(monkeypatch)
    monkeypatch.setenv('SMTP_HOST', '127.0.0.1')
    monkeypatch.setenv('SMTP_PORT', str(puerto))
    monkeypatch.setenv('SMTP_USER', 'tienda@gmail.com')
    monkeypatch.setenv('SMTP_PASSWORD', 'clavedeaplicacion')
    # El servidor de prueba no tiene certificado, así que no se negocia TLS.
    monkeypatch.setenv('SMTP_USE_TLS', 'false')


def test_el_servidor_de_correo_se_deduce_del_dominio(monkeypatch):
    """Con Gmail basta el usuario y la contraseña de aplicación."""
    _sin_correo_configurado(monkeypatch)
    assert 'SMTP_USER' in correo.revisar_configuracion()

    monkeypatch.setenv('SMTP_USER', 'tienda@gmail.com')
    assert 'SMTP_PASSWORD' in correo.revisar_configuracion()

    monkeypatch.setenv('SMTP_PASSWORD', 'clavedeaplicacion')
    assert correo.revisar_configuracion() == ''
    assert correo.servidor_de_correo() == ('smtp.gmail.com', 587)
    assert correo.remitente() == 'SimonC Realidad Virtual <tienda@gmail.com>'
    assert correo.hay_correo_configurado() is True

    # Un dominio propio sí necesita que le digan a qué servidor conectarse.
    monkeypatch.setenv('SMTP_USER', 'tienda@midominio.co')
    assert 'SMTP_HOST' in correo.revisar_configuracion()
    monkeypatch.setenv('SMTP_HOST', 'correo.midominio.co')
    monkeypatch.setenv('SMTP_PORT', '2525')
    assert correo.servidor_de_correo() == ('correo.midominio.co', 2525)
    assert correo.revisar_configuracion() == ''


def test_el_enlace_de_recuperacion_sale_por_correo(client, monkeypatch, capsys):
    """Con servidor de correo configurado el enlace viaja en el mensaje."""
    direccion = 'porcorreo@simonsc.com'
    alta = client.post('/api/auth/register', json={
        'name': 'Por', 'lastName': 'Correo', 'documentType': 'CC', 'documentNumber': '5151515151',
        'address': 'Carrera 9 numero 8-70', 'phone': '3009998877',
        'email': direccion, 'password': 'Clave1234', 'confirmPassword': 'Clave1234',
    })
    assert alta.status_code == 201, alta.text

    recibidos = []
    puerto, hilo = _servidor_de_correo_falso(recibidos)
    _apuntar_al_servidor_falso(monkeypatch, puerto)

    respuesta = client.post('/api/auth/recover', json={'email': direccion})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()['correoConfigurado'] is True

    hilo.join(timeout=10)
    assert recibidos, 'el servidor de correo no recibió nada'
    mensaje = recibidos[0]
    assert b'reset-password' in mensaje
    # Va en dos versiones: texto plano y HTML con el botón.
    assert b'multipart/alternative' in mensaje
    assert direccion.encode() in mensaje
    # Si el correo salió, el enlace ya no se imprime en la consola.
    assert 'reset-password?token=' not in capsys.readouterr().out


def test_el_panel_reporta_el_estado_del_correo(client, admin, monkeypatch):
    """El administrador ve qué falta sin tener que leer la consola."""
    _sin_correo_configurado(monkeypatch)
    datos = client.get('/api/auth/correo-estado', headers=admin).json()
    assert datos['configurado'] is False
    assert 'SMTP_USER' in datos['motivo']

    monkeypatch.setenv('SMTP_USER', 'tienda@gmail.com')
    monkeypatch.setenv('SMTP_PASSWORD', 'clavedeaplicacion')
    datos = client.get('/api/auth/correo-estado', headers=admin).json()
    assert datos['configurado'] is True
    assert datos['servidor'] == 'smtp.gmail.com:587'
    assert datos['remitente'] == 'SimonC Realidad Virtual <tienda@gmail.com>'


def test_la_prueba_de_correo_llega_y_es_solo_del_administrador(client, admin, monkeypatch):
    recibidos = []
    puerto, hilo = _servidor_de_correo_falso(recibidos)
    _apuntar_al_servidor_falso(monkeypatch, puerto)

    respuesta = client.post('/api/auth/probar-correo', headers=admin, json={'email': 'destino@gmail.com'})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()['enviado'] is True
    hilo.join(timeout=10)
    assert recibidos and b'destino@gmail.com' in recibidos[0]

    cliente = _cuenta_de_cliente(client, 'ana.correo@correo.com', '7788990011')
    assert client.post('/api/auth/probar-correo', headers=cliente, json={'email': 'x@gmail.com'}).status_code == 403
    assert client.post('/api/auth/probar-correo', json={'email': 'x@gmail.com'}).status_code == 401
    assert client.get('/api/auth/correo-estado', headers=cliente).status_code == 403


def test_sin_configurar_la_prueba_explica_que_falta(client, admin, monkeypatch):
    """No se le dice "no se pudo" sin decir por qué."""
    _sin_correo_configurado(monkeypatch)
    respuesta = client.post('/api/auth/probar-correo', headers=admin, json={'email': 'destino@gmail.com'})
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos['enviado'] is False
    assert 'SMTP_USER' in datos['message']

    # Y la pantalla de recuperación avisa que el enlace no se está enviando.
    recuperar = client.post('/api/auth/recover', json={'email': 'nadie@simonsc.com'}).json()
    assert recuperar['correoConfigurado'] is False


def _api_de_correo_falsa(recibidas, codigo=201, respuesta=b'{"messageId":"<abc>"}'):
    """Un servidor HTTP mínimo que hace de proveedor de correo por API web."""

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 (lo exige BaseHTTPRequestHandler)
            largo = int(self.headers.get('Content-Length', '0'))
            recibidas.append({
                'ruta': self.path,
                'clave': self.headers.get('api-key', ''),
                'cuerpo': json.loads(self.rfile.read(largo).decode('utf-8')),
            })
            self.send_response(codigo)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(respuesta)))
            self.end_headers()
            self.wfile.write(respuesta)

        def log_message(self, *_):
            pass

    servidor = ThreadingHTTPServer(('127.0.0.1', 0), Manejador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


def _apuntar_a_la_api_falsa(monkeypatch, servidor):
    _sin_correo_configurado(monkeypatch)
    monkeypatch.setenv('EMAIL_API_KEY', 'clave-de-prueba')
    monkeypatch.setenv('EMAIL_FROM', 'tienda@gmail.com')
    monkeypatch.setenv('EMAIL_API_URL', f'http://127.0.0.1:{servidor.server_address[1]}/v3/smtp/email')


def test_el_correo_sale_por_la_api_web(client, monkeypatch, capsys):
    """La forma que sí funciona en el plan gratuito de Render."""
    direccion = 'porapi@simonsc.com'
    alta = client.post('/api/auth/register', json={
        'name': 'Por', 'lastName': 'Api', 'documentType': 'CC', 'documentNumber': '5252525252',
        'address': 'Carrera 10 numero 11-12', 'phone': '3007776655',
        'email': direccion, 'password': 'Clave1234', 'confirmPassword': 'Clave1234',
    })
    assert alta.status_code == 201, alta.text

    recibidas = []
    servidor = _api_de_correo_falsa(recibidas)
    try:
        _apuntar_a_la_api_falsa(monkeypatch, servidor)
        assert correo.via() == 'api'

        respuesta = client.post('/api/auth/recover', json={'email': direccion})
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()['correoConfigurado'] is True
    finally:
        servidor.shutdown()

    assert len(recibidas) == 1
    peticion = recibidas[0]
    assert peticion['clave'] == 'clave-de-prueba'
    assert peticion['cuerpo']['sender'] == {'name': 'SimonC Realidad Virtual', 'email': 'tienda@gmail.com'}
    assert peticion['cuerpo']['to'] == [{'email': direccion}]
    assert 'reset-password?token=' in peticion['cuerpo']['textContent']
    assert 'Crear una contraseña nueva' in peticion['cuerpo']['htmlContent']
    # Si el correo salió, el enlace ya no se imprime en la consola.
    assert 'reset-password?token=' not in capsys.readouterr().out


def test_la_api_web_manda_sobre_smtp(monkeypatch):
    """Configuradas las dos, se usa la que funciona en todas partes."""
    _sin_correo_configurado(monkeypatch)
    monkeypatch.setenv('SMTP_USER', 'tienda@gmail.com')
    monkeypatch.setenv('SMTP_PASSWORD', 'clavedeaplicacion')
    assert correo.via() == 'smtp'
    monkeypatch.setenv('EMAIL_API_KEY', 'clave-de-prueba')
    assert correo.via() == 'api'


def test_sin_remitente_la_api_web_dice_que_falta(client, admin, monkeypatch):
    _sin_correo_configurado(monkeypatch)
    monkeypatch.setenv('EMAIL_API_KEY', 'clave-de-prueba')
    datos = client.get('/api/auth/correo-estado', headers=admin).json()
    assert datos['configurado'] is False
    assert 'EMAIL_FROM' in datos['motivo']


def test_la_api_web_explica_el_error_del_proveedor(client, admin, monkeypatch):
    """Una clave vencida no puede quedarse en un "no se pudo" sin causa."""
    servidor = _api_de_correo_falsa([], codigo=401, respuesta=b'{"message":"Key not found"}')
    try:
        _apuntar_a_la_api_falsa(monkeypatch, servidor)
        respuesta = client.post('/api/auth/probar-correo', headers=admin, json={'email': 'destino@gmail.com'})
    finally:
        servidor.shutdown()

    datos = respuesta.json()
    assert datos['enviado'] is False
    assert 'EMAIL_API_KEY' in datos['message']
    # La clave jamás aparece en un mensaje que se muestra en pantalla.
    assert 'clave-de-prueba' not in datos['message']


def test_en_render_avisa_que_el_plan_gratuito_bloquea_smtp(client, admin, monkeypatch):
    """El correo por SMTP se perdería en silencio en el sitio publicado."""
    _sin_correo_configurado(monkeypatch)
    monkeypatch.setenv('SMTP_USER', 'tienda@gmail.com')
    monkeypatch.setenv('SMTP_PASSWORD', 'clavedeaplicacion')
    assert correo.advertencia() == ''

    monkeypatch.setenv('RENDER', 'true')
    assert 'Render bloquea' in correo.advertencia()
    datos = client.get('/api/auth/correo-estado', headers=admin).json()
    assert datos['configurado'] is True
    assert 'EMAIL_API_KEY' in datos['advertencia']

    # Por API web no hay nada que advertir: esa sí sale desde Render.
    monkeypatch.setenv('EMAIL_API_KEY', 'clave-de-prueba')
    monkeypatch.setenv('EMAIL_FROM', 'tienda@gmail.com')
    assert correo.advertencia() == ''


# --- Criterios de la matriz de validación técnica ---------------------------

def test_el_token_oauth2_sirve_para_el_boton_authorize(client):
    """El flujo OAuth2 password es el que usa /docs para autenticarse."""
    respuesta = client.post(
        '/api/auth/token',
        data={'username': 'admin@simonsc.com', 'password': 'Admin1234'},
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos['token_type'] == 'bearer'

    # Y ese token abre los endpoints protegidos, igual que el de /auth/login.
    cabeceras = {'Authorization': f"Bearer {datos['access_token']}"}
    assert client.get('/api/users', headers=cabeceras).status_code == 200

    # Una credencial mala es 401, no un 422 de formato.
    assert client.post('/api/auth/token', data={'username': 'admin@simonsc.com', 'password': 'mala'}).status_code == 401
    assert client.post('/api/auth/token', data={'username': 'no-es-un-correo', 'password': 'x'}).status_code == 401


def test_el_esquema_openapi_queda_documentado(client):
    """Criterio de documentación: tags con descripción, ejemplos y seguridad."""
    esquema = client.get('/openapi.json').json()

    assert 'Authorize' in esquema['info']['description']
    etiquetas = {tag['name']: tag.get('description', '') for tag in esquema.get('tags', [])}
    assert {'auth', 'usuarios', 'catalogo', 'ventas', 'pqr'} <= set(etiquetas)
    assert all(etiquetas.values()), 'toda etiqueta necesita su descripción'

    # El botón Authorize solo aparece si hay un esquema de seguridad declarado.
    seguridad = esquema['components'].get('securitySchemes', {})
    assert any(valor.get('type') == 'oauth2' for valor in seguridad.values())

    # Ejemplos precargados en el cuerpo de las peticiones.
    assert esquema['components']['schemas']['UserCreateSchema']['examples']

    # Resúmenes y esquema de salida declarado en las rutas del dominio.
    listar = esquema['paths']['/api/products']['get']
    assert listar['summary']
    cuerpo = listar['responses']['200']['content']['application/json']['schema']
    assert 'ProductsResponseSchema' in json.dumps(cuerpo)


def test_consultar_un_solo_registro_por_su_id(client, admin):
    """El CRUD incluye "consultar": productos, servicios y usuarios, uno a uno."""
    creado = client.post('/api/products', headers=admin, json={
        'name': 'Visor de prueba por id', 'description': 'Para la matriz.', 'price': 150000,
    })
    assert creado.status_code == 201, creado.text
    producto = creado.json()

    uno = client.get(f"/api/products/{producto['id']}", headers=admin)
    assert uno.status_code == 200, uno.text
    assert uno.json()['name'] == 'Visor de prueba por id'
    assert 'password' not in uno.text

    assert client.get('/api/products/999999', headers=admin).status_code == 404
    assert client.get(f"/api/products/{producto['id']}").status_code == 401

    servicios = client.get('/api/services', headers=admin).json()['services']
    assert client.get(f"/api/services/{servicios[0]['id']}", headers=admin).status_code == 200

    usuarios = client.get('/api/users', headers=admin).json()['users']
    uno = client.get(f"/api/users/{usuarios[0]['id']}", headers=admin)
    assert uno.status_code == 200, uno.text
    # El esquema de salida recorta el hash de la contraseña aunque venga en la fila.
    assert 'password' not in uno.text
    assert client.get('/api/users/999999', headers=admin).status_code == 404


def test_el_cliente_no_consulta_por_id_lo_retirado(client, admin):
    """Lo que no está publicado tampoco se alcanza sabiendo el id."""
    creado = client.post('/api/products', headers=admin, json={
        'name': 'Visor retirado por id', 'description': 'Ya no se vende.', 'price': 100000,
    })
    producto_id = creado.json()['id']
    assert client.patch(f'/api/products/{producto_id}/status', headers=admin, json={'active': False}).status_code == 200

    cliente = _cuenta_de_cliente(client, 'ana.porid@correo.com', '8899001122')
    assert client.get(f'/api/products/{producto_id}', headers=cliente).status_code == 404
    # El administrador sí lo ve, porque es quien lo administra.
    assert client.get(f'/api/products/{producto_id}', headers=admin).status_code == 200


def test_la_salud_del_servicio_es_asincrona(client):
    """Criterio de asincronía: hay endpoints escritos con async/await."""
    assert inspect.iscoroutinefunction(main.health)
    assert inspect.iscoroutinefunction(main.public_catalog)

    datos = client.get('/api/health').json()
    assert datos['status'] == 'ok'
    assert datos['database'] in ('sqlite', 'mysql')


def test_el_correo_de_recuperacion_se_manda_en_segundo_plano():
    """Criterio de tareas en segundo plano: /recover no espera al proveedor."""
    import recuperacion as modulo

    parametros = inspect.signature(modulo.solicitar_recuperacion).parameters
    assert any(
        getattr(parametro.annotation, '__name__', '') == 'BackgroundTasks'
        for parametro in parametros.values()
    ), 'solicitar_recuperacion debe recibir BackgroundTasks'


def test_los_modelos_orm_se_configuran_y_estan_relacionados():
    """Criterio de persistencia: modelos SQLAlchemy 2.0 con relaciones válidas."""
    from sqlalchemy.orm import configure_mappers

    import models

    # Falla si un back_populates no tiene su pareja al otro lado.
    configure_mappers()

    assert {'usuarios', 'ventas', 'detalle_ventas', 'facturas', 'pqr'} <= set(models.Base.metadata.tables)

    # Estilo tipado de 2.0: las columnas se anotan con Mapped[...].
    assert 'id' in models.Venta.__annotations__
    assert 'Mapped' in str(models.Venta.__annotations__['id'])

    # Dos entidades relacionadas, navegables en los dos sentidos.
    assert models.Venta.detalle.property.mapper.class_ is models.DetalleVenta
    assert models.DetalleVenta.venta.property.mapper.class_ is models.Venta
    assert models.Mensaje.conversacion.property.mapper.class_ is models.Conversacion


# --- Pasarela de pago ------------------------------------------------------

def _comprador(client, sufijo: str):
    """Crea un cliente con su propia compra sin pagar y devuelve sus datos."""
    correo = f'pago{sufijo}@simonsc.com'
    client.post('/api/auth/register', json={
        'name': 'Pago', 'lastName': 'Cliente', 'documentType': 'CC', 'documentNumber': f'88{sufijo}8888',
        'address': 'Calle 10 #20-30', 'phone': '3001234567', 'email': correo, 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={'email': correo, 'password': 'Cliente1234'}).json()['token']
    cabeceras = {'Authorization': f'Bearer {token}'}
    producto = client.get('/api/catalogo').json()['productos'][0]
    pedido = client.post('/api/ventas/pedido', headers=cabeceras, json={
        'items': [{'tipo': 'producto', 'itemId': producto['id'], 'cantidad': 1}],
    }).json()
    return cabeceras, pedido


def _tarjeta(venta_id: int, numero: str = '4111111111111111', **extra) -> dict:
    datos = {
        'ventaId': venta_id, 'nombre': 'PAGO CLIENTE', 'numero': numero,
        'vencimiento': '12/30', 'cvv': '123', 'cuotas': 1,
    }
    datos.update(extra)
    return datos


def test_la_firma_de_payu_coincide_con_el_ejemplo_de_su_documentacion():
    """El ejemplo publicado por PayU es la única forma de comprobar la firma aquí.

    El entorno de pruebas de PayU no se puede llamar desde las pruebas, así que
    se verifica contra el valor que la propia documentación da por bueno para
    ``4Vj8eK4rloUd272L48hsrarnUA~508029~TestPayU~20000~COP``.
    """
    credenciales = {'apiKey': '4Vj8eK4rloUd272L48hsrarnUA', 'merchantId': '508029'}
    assert pagos.firma_peticion('TestPayU', 20000, credenciales) == '7ee7cf808ce6a39b17481c54f2c57acc'


def test_el_pago_simulado_aprueba_y_deja_pagadas_la_venta_y_la_factura(client):
    cabeceras, pedido = _comprador(client, '01')
    venta, factura = pedido['venta'], pedido['factura']
    assert venta['estado'] == 'Registrada' and factura['estado'] == 'Emitida'

    respuesta = client.post('/api/pagos/simulado', headers=cabeceras, json=_tarjeta(venta['id']))
    assert respuesta.status_code == 201, respuesta.text
    pago = respuesta.json()['pago']
    assert pago['estado'] == 'Aprobado'
    assert pago['monto'] == venta['total']
    # De la tarjeta solo quedan la franquicia y los cuatro últimos dígitos.
    assert pago['franquicia'] == 'Visa' and pago['ultimosDigitos'] == '1111'
    assert '4111111111111111' not in respuesta.text

    assert client.get(f"/api/ventas/{venta['id']}", headers=cabeceras).json()['venta']['estado'] == 'Pagada'
    assert client.get(f"/api/facturas/{factura['id']}", headers=cabeceras).json()['factura']['estado'] == 'Pagada'

    # Una compra pagada no se vuelve a cobrar.
    assert client.post('/api/pagos/simulado', headers=cabeceras, json=_tarjeta(venta['id'])).status_code == 400


def test_el_pago_simulado_rechaza_y_la_compra_sigue_sin_pagar(client):
    cabeceras, pedido = _comprador(client, '02')
    venta = pedido['venta']

    fondos = client.post('/api/pagos/simulado', headers=cabeceras, json=_tarjeta(venta['id'], '4000000200000000'))
    assert fondos.status_code == 201
    assert fondos.json()['pago']['estado'] == 'Rechazado'
    assert 'Fondos insuficientes' in fondos.json()['message']
    assert fondos.json()['venta']['estado'] == 'Registrada'

    banco = client.post('/api/pagos/simulado', headers=cabeceras, json=_tarjeta(venta['id'], cvv='666'))
    assert banco.json()['pago']['estado'] == 'Rechazado'

    # Un rechazo no impide volver a intentarlo, y el segundo intento sí pasa.
    bueno = client.post('/api/pagos/simulado', headers=cabeceras, json=_tarjeta(venta['id']))
    assert bueno.json()['pago']['estado'] == 'Aprobado'


def test_la_tarjeta_invalida_no_llega_a_cobrarse(client):
    cabeceras, pedido = _comprador(client, '03')
    venta_id = pedido['venta']['id']

    # Dígito de control incorrecto, fecha vencida y código no numérico.
    assert client.post('/api/pagos/simulado', headers=cabeceras,
                       json=_tarjeta(venta_id, '4111111111111112')).status_code == 400
    assert client.post('/api/pagos/simulado', headers=cabeceras,
                       json=_tarjeta(venta_id, vencimiento='01/20')).status_code == 400
    assert client.post('/api/pagos/simulado', headers=cabeceras,
                       json=_tarjeta(venta_id, cvv='abc')).status_code == 400
    # Y lo que ni siquiera tiene forma de tarjeta lo para Pydantic antes.
    assert client.post('/api/pagos/simulado', headers=cabeceras,
                       json=_tarjeta(venta_id, '12')).status_code == 422

    # Y ninguno de esos intentos dejó rastro de cobro.
    assert client.get('/api/pagos', headers=cabeceras).json()['pagos'] == []


def test_nadie_paga_la_compra_de_otro_ni_ve_sus_pagos(client):
    uno, pedido_uno = _comprador(client, '04')
    otro, _ = _comprador(client, '05')

    ajena = client.post('/api/pagos/simulado', headers=otro, json=_tarjeta(pedido_uno['venta']['id']))
    assert ajena.status_code == 403

    client.post('/api/pagos/simulado', headers=uno, json=_tarjeta(pedido_uno['venta']['id']))
    assert len(client.get('/api/pagos', headers=uno).json()['pagos']) == 1
    assert client.get('/api/pagos', headers=otro).json()['pagos'] == []
    assert client.post('/api/pagos/simulado', json=_tarjeta(1)).status_code == 401


def test_payu_firma_el_formulario_y_solo_acepta_la_respuesta_firmada(client):
    cabeceras, pedido = _comprador(client, '06')
    venta = pedido['venta']

    formulario = client.post('/api/pagos/payu', headers=cabeceras,
                             json={'ventaId': venta['id'], 'origen': 'http://localhost:5173'})
    assert formulario.status_code == 200, formulario.text
    datos = formulario.json()
    campos = datos['campos']
    assert datos['pruebas'] is True and campos['test'] == '1'
    # El importe no lo pone el navegador: sale de la venta y va sellado en la firma.
    assert campos['amount'] == str(int(venta['total']))
    assert campos['signature'] == pagos.firma_peticion(datos['referencia'], venta['total'])
    assert campos['responseUrl'] == 'http://localhost:5173/pago/respuesta'

    def responder(estado: str, firma: str | None = None) -> dict:
        cuerpo = {
            'merchantId': campos['merchantId'], 'referenceCode': datos['referencia'],
            'TX_VALUE': campos['amount'], 'currency': 'COP', 'transactionState': estado,
            'message': 'APPROVED', 'transactionId': 'trx-1',
        }
        credenciales = pagos.payu_config()
        cadena = f"{credenciales['apiKey']}~{credenciales['merchantId']}~{datos['referencia']}~{campos['amount']}~COP~{estado}"
        cuerpo['signature'] = firma if firma is not None else hashlib.md5(cadena.encode('utf-8')).hexdigest()
        return cuerpo

    # Sin la firma correcta no se toca nada: si no, bastaría abrir la dirección
    # de vuelta a mano para darse por pagado.
    assert client.post('/api/pagos/payu/respuesta', headers=cabeceras,
                       json=responder('4', firma='0' * 32)).status_code == 400
    assert client.get(f"/api/ventas/{venta['id']}", headers=cabeceras).json()['venta']['estado'] == 'Registrada'

    aprobada = client.post('/api/pagos/payu/respuesta', headers=cabeceras, json=responder('4'))
    assert aprobada.status_code == 200, aprobada.text
    assert aprobada.json()['pago']['estado'] == 'Aprobado'
    assert client.get(f"/api/ventas/{venta['id']}", headers=cabeceras).json()['venta']['estado'] == 'Pagada'


def test_payu_solo_devuelve_el_navegador_a_una_direccion_del_sitio(client):
    cabeceras, pedido = _comprador(client, '07')
    respuesta = client.post('/api/pagos/payu', headers=cabeceras,
                            json={'ventaId': pedido['venta']['id'], 'origen': 'https://sitio-ajeno.com'})
    assert respuesta.status_code == 200
    assert 'sitio-ajeno' not in respuesta.json()['campos']['responseUrl']
