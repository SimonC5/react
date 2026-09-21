"""Pruebas de la API del quinto avance.

Se ejecutan sobre una base de datos temporal, así que no tocan
``backend/data/simonsc.db``:

    pip install -r backend/requirements-dev.txt
    python -m pytest backend
"""

import sys
import tempfile
from pathlib import Path

import pytest
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
