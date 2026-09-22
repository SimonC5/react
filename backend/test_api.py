"""Pruebas de la API del quinto avance.

Se ejecutan sobre una base de datos temporal, así que no tocan
``backend/data/simonsc.db``:

    pip install -r backend/requirements-dev.txt
    python -m pytest backend
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402

_TMP = Path(tempfile.mkdtemp())
core.DATA_DIR = _TMP
core.DB_PATH = _TMP / 'test.db'

import main  # noqa: E402

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


def test_el_cliente_no_ve_las_pqr_de_otros_en_su_dashboard(client, admin):
    client.post('/api/pqr', headers=admin, json={
        'tipo': 'Queja', 'asunto': 'Solicitud del administrador', 'descripcion': 'No debe verla el cliente.',
    })
    client.post('/api/auth/register', json={
        'name': 'Otro', 'lastName': 'Cliente', 'documentType': 'CC', 'documentNumber': '8888888888',
        'address': 'Calle 2', 'phone': '3009998877', 'email': 'otro.cliente@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'otro.cliente@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}

    resumen = client.get('/api/dashboard/resumen', headers=cliente).json()
    assert sum(fila['valor'] for fila in resumen['pqrPorEstado']) == 0


def test_permisos_por_rol(client, admin):
    client.post('/api/auth/register', json={
        'name': 'Cliente', 'lastName': 'Demo', 'documentType': 'CC', 'documentNumber': '9999999999',
        'address': 'Calle 1', 'phone': '3001112233', 'email': 'cliente.demo@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'cliente.demo@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}

    assert client.post('/api/ventas', headers=cliente, json={'cliente': 'x', 'items': []}).status_code == 403
    assert client.get('/api/reportes/ventas/diario', headers=cliente).status_code == 403
    assert client.get('/api/ventas', headers=cliente).json()['resumen']['cantidad'] == 0
    assert client.get('/api/dashboard/resumen', headers=cliente).status_code == 200
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
        'address': 'Calle 4', 'phone': '3006161616', 'email': 'catalogo@simonsc.com', 'password': 'Cliente1234',
    })
    token = client.post('/api/auth/login', json={
        'email': 'catalogo@simonsc.com', 'password': 'Cliente1234',
    }).json()['token']
    cliente = {'Authorization': f'Bearer {token}'}

    creado = client.post('/api/products', headers=admin, json={
        'name': 'Visor descontinuado', 'description': 'Ya no se vende.', 'price': 100000,
    })
    assert creado.status_code == 200, creado.text
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
        'address': 'Calle 3', 'phone': '3007070707', 'email': 'carrito@simonsc.com', 'password': 'Cliente1234',
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
    assert alta.status_code == 200, alta.text

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
