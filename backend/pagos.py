"""Pasarela de pago de la tienda.

Hay dos, y las dos terminan igual: con un registro en la tabla ``pagos`` y, si
el pago se aprueba, con la venta y su factura marcadas como **Pagada**.

- **PayU WebCheckout** es la pasarela de verdad, en su modo de pruebas. El
  navegador sale del sitio, paga en la página de PayU con una tarjeta de
  prueba y vuelve a ``/pago/respuesta``. No hace falta crear ninguna cuenta:
  PayU publica las credenciales del entorno de pruebas de Colombia en su
  documentación, y son las que trae el proyecto por defecto.
- **La pasarela simulada** cobra sin salir del sitio. Sirve para la
  sustentación cuando no hay internet o el entorno de pruebas de PayU no
  responde, y es la que usan las pruebas automáticas.

Nunca se guarda el número completo de la tarjeta ni el código de seguridad:
de la tarjeta solo quedan la franquicia y los cuatro últimos dígitos, que es
lo que lleva un recibo.
"""

import hashlib
import os
from typing import Any, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

try:
    from .core import get_current_user, get_db_connection, origenes_permitidos, require_roles
    from .comercial import (
        ESTADOS_PAGO,
        la_venta_es_del_cliente,
        money,
        next_number,
        now_iso,
        pago_row,
        venta_row,
    )
except ImportError:
    from core import get_current_user, get_db_connection, origenes_permitidos, require_roles
    from comercial import (
        ESTADOS_PAGO,
        la_venta_es_del_cliente,
        money,
        next_number,
        now_iso,
        pago_row,
        venta_row,
    )

router = APIRouter(prefix='/api/pagos', tags=['pagos'])

MONEDA = 'COP'

# Credenciales del entorno de pruebas de PayU para Colombia, publicadas por
# PayU en <https://developers.payulatam.com/latam/es/docs/getting-started/
# test-your-solution.html>. Son de mentira y las comparte todo el mundo: no
# mueven dinero y no identifican a nadie. Para cobrar de verdad se cambian por
# las del comercio con las variables PAYU_*.
PAYU_PRUEBAS = {
    'url': 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/',
    'merchantId': '508029',
    'accountId': '512321',
    'apiKey': '4Vj8eK4rloUd272L48hsrarnUA',
}

# Lo que PayU contesta en `transactionState`.
ESTADOS_PAYU = {'4': 'Aprobado', '6': 'Rechazado', '7': 'Pendiente', '104': 'Error'}

FRANQUICIAS = (
    ('Visa', ('4',)),
    ('Mastercard', ('51', '52', '53', '54', '55', '2221', '2720')),
    ('American Express', ('34', '37')),
    ('Diners Club', ('36', '38', '30')),
)


# --- Configuración ---------------------------------------------------------

def _variable(nombre: str) -> str:
    return (os.getenv(nombre) or '').strip()


def payu_config() -> dict[str, str]:
    """Credenciales de PayU: las del comercio si están, las de pruebas si no."""
    return {
        'url': _variable('PAYU_URL') or PAYU_PRUEBAS['url'],
        'merchantId': _variable('PAYU_MERCHANT_ID') or PAYU_PRUEBAS['merchantId'],
        'accountId': _variable('PAYU_ACCOUNT_ID') or PAYU_PRUEBAS['accountId'],
        'apiKey': _variable('PAYU_API_KEY') or PAYU_PRUEBAS['apiKey'],
    }


def en_pruebas() -> bool:
    """¿Se está cobrando de mentira? Solo es falso con credenciales propias."""
    if _variable('PAYU_TEST'):
        return _variable('PAYU_TEST').lower() not in ('0', 'false', 'no')
    return payu_config()['apiKey'] == PAYU_PRUEBAS['apiKey']


def _frontend_url() -> str:
    permitidos = origenes_permitidos()
    # El primero configurado es el sitio publicado; si no hay, el de casa.
    for origen in permitidos:
        if 'localhost' not in origen and '127.0.0.1' not in origen:
            return origen
    return permitidos[0] if permitidos else 'http://localhost:5173'


def _api_publica() -> str:
    """Dirección pública de esta API, si la tiene.

    Es a donde PayU manda el aviso de servidor a servidor, así que tiene que
    ser la del backend y no la del sitio. En el computador de uno no existe
    (PayU no puede entrar a localhost), y entonces no se manda el campo: el
    pago se confirma igual cuando el navegador vuelve.
    """
    directa = _variable('API_PUBLIC_URL') or _variable('RENDER_EXTERNAL_URL')
    if directa:
        return directa.rstrip('/')
    host = _variable('RENDER_EXTERNAL_HOSTNAME')
    return f'https://{host}' if host else ''


def _origen_valido(origen: str) -> str:
    """Solo se vuelve a una dirección del propio sitio.

    El navegador dice desde dónde está comprando para que el pago vuelva al
    mismo sitio (en casa es localhost, publicado es el dominio de Render). Se
    compara contra la lista de orígenes permitidos, la misma del CORS: si
    llegara cualquier otra, PayU devolvería al visitante a una página ajena.
    """
    limpio = str(origen or '').strip().rstrip('/')
    if not limpio:
        return ''
    try:
        partes = urlsplit(limpio)
    except ValueError:
        return ''
    base = f'{partes.scheme}://{partes.netloc}'
    return base if base in origenes_permitidos() else ''


# --- Firma de PayU ---------------------------------------------------------

def _monto_para_firma(valor: float) -> str:
    """El monto va en la firma tal como viaja en el formulario.

    En pesos no hay centavos, así que un valor entero se firma sin decimales,
    que es como lo muestran los ejemplos de PayU.
    """
    numero = money(valor)
    return str(int(numero)) if float(numero).is_integer() else f'{numero:.2f}'


def firma_peticion(referencia: str, monto: float, config: Optional[dict[str, str]] = None) -> str:
    """MD5 de ``ApiKey~merchantId~referenceCode~amount~currency``."""
    datos = config or payu_config()
    cadena = f"{datos['apiKey']}~{datos['merchantId']}~{referencia}~{_monto_para_firma(monto)}~{MONEDA}"
    return hashlib.md5(cadena.encode('utf-8')).hexdigest()


def _montos_de_respuesta(valor: str) -> list[str]:
    """Las formas en que PayU puede escribir el monto al volver.

    La documentación manda redondear a un decimal con redondeo bancario, que es
    justo lo que hace ``round`` en Python, pero según el medio de pago vuelve
    también como entero. Se aceptan las dos: la firma sigue cerrando solo si el
    valor es el mismo.
    """
    try:
        numero = float(str(valor).strip())
    except (TypeError, ValueError):
        return []
    formas = [f'{round(numero, 1):.1f}']
    if float(numero).is_integer():
        formas.append(str(int(numero)))
    return list(dict.fromkeys(formas))


def firma_valida(parametros: dict[str, Any]) -> bool:
    """Comprueba la firma con la que PayU avisa del resultado.

    Es lo único que impide que alguien abra a mano
    ``/pago/respuesta?transactionState=4`` y se marque la venta como pagada:
    la firma solo la puede calcular quien tenga la ApiKey.
    """
    config = payu_config()
    recibida = str(parametros.get('signature') or '').strip().lower()
    referencia = str(parametros.get('referenceCode') or '').strip()
    estado = str(parametros.get('transactionState') or '').strip()
    if not recibida or not referencia or not estado:
        return False
    if str(parametros.get('merchantId') or '').strip() != config['merchantId']:
        return False
    for monto in _montos_de_respuesta(parametros.get('TX_VALUE')):
        cadena = f"{config['apiKey']}~{config['merchantId']}~{referencia}~{monto}~{MONEDA}~{estado}"
        for algoritmo in (hashlib.md5, hashlib.sha256):
            if algoritmo(cadena.encode('utf-8')).hexdigest() == recibida:
                return True
    return False


# --- Tarjetas --------------------------------------------------------------

def franquicia_de(numero: str) -> str:
    digitos = ''.join(c for c in str(numero) if c.isdigit())
    for nombre, prefijos in FRANQUICIAS:
        if digitos.startswith(prefijos):
            return nombre
    return 'Tarjeta'


def luhn(numero: str) -> bool:
    """Comprueba el dígito de control, que es lo que valida un cajero."""
    digitos = [int(c) for c in str(numero) if c.isdigit()]
    if len(digitos) < 13:
        return False
    total = 0
    for posicion, digito in enumerate(reversed(digitos)):
        if posicion % 2:
            digito *= 2
            if digito > 9:
                digito -= 9
        total += digito
    return total % 10 == 0


def _vencimiento_valido(valor: str) -> bool:
    texto = str(valor or '').strip()
    if len(texto) != 5 or texto[2] != '/':
        return False
    mes, anio = texto[:2], texto[3:]
    if not (mes.isdigit() and anio.isdigit()):
        return False
    if not 1 <= int(mes) <= 12:
        return False
    from datetime import date

    hoy = date.today()
    return (2000 + int(anio), int(mes)) >= (hoy.year, hoy.month)


def _resultado_simulado(nombre: str, numero: str, cvv: str) -> tuple[str, str]:
    """Reglas de la pasarela simulada, iguales a las del entorno de PayU.

    Están escritas para poderlas enseñar: el nombre o el código de seguridad
    deciden el resultado, así que en la sustentación se puede mostrar un pago
    aprobado y uno rechazado sin tocar el código.
    """
    if cvv == '666' or 'REJECTED' in nombre.upper():
        return 'Rechazado', 'La entidad bancaria rechazó la transacción.'
    if numero.endswith('0000'):
        return 'Rechazado', 'Fondos insuficientes.'
    if cvv == '777' or 'PENDING' in nombre.upper():
        return 'Pendiente', 'El banco está verificando la transacción.'
    return 'Aprobado', 'Transacción aprobada.'


# --- Esquemas --------------------------------------------------------------

class PagoTarjeta(BaseModel):
    """Datos del formulario de la pasarela simulada."""

    model_config = ConfigDict(json_schema_extra={'examples': [{
        'ventaId': 1, 'nombre': 'APPROVED Ana Restrepo', 'numero': '4111111111111111',
        'vencimiento': '12/30', 'cvv': '123', 'cuotas': 1,
    }]})

    ventaId: int
    nombre: str = Field(min_length=3, max_length=80, description='Nombre como aparece en la tarjeta')
    numero: str = Field(min_length=13, max_length=25, description='Solo se guardan los cuatro últimos dígitos')
    vencimiento: str = Field(description='MM/AA')
    cvv: str = Field(min_length=3, max_length=4, description='No se guarda')
    cuotas: int = Field(default=1, ge=1, le=36)


class PagoPayU(BaseModel):
    """Petición para empezar el pago en PayU."""

    model_config = ConfigDict(json_schema_extra={'examples': [{'ventaId': 1, 'origen': 'http://localhost:5173'}]})

    ventaId: int
    origen: str = Field(default='', description='Dirección del sitio a la que debe volver el navegador')


class PagoResponse(BaseModel):
    id: int
    referencia: str
    ventaId: int
    facturaId: Optional[int] = None
    clienteId: Optional[int] = None
    cliente: str = ''
    pasarela: str
    metodo: str
    franquicia: str = ''
    ultimosDigitos: str = ''
    cuotas: int = 1
    monto: float = 0
    moneda: str = MONEDA
    estado: str
    motivo: str = ''
    transaccion: str = ''
    fecha: str


class PagosResponse(BaseModel):
    pagos: list[PagoResponse]
    resumen: dict[str, float]


class ResultadoPago(BaseModel):
    message: str
    pago: PagoResponse
    venta: Optional[dict[str, Any]] = None


class FormularioPayU(BaseModel):
    """Lo que el navegador tiene que enviarle a PayU."""

    url: str
    campos: dict[str, str]
    referencia: str
    pruebas: bool


class TarjetaDePrueba(BaseModel):
    numero: str
    franquicia: str
    resultado: str
    # "ambas" o "simulada": en PayU el resultado lo decide el nombre del titular.
    donde: str = 'ambas'


class ConfigPagos(BaseModel):
    pasarelas: list[str]
    payuPruebas: bool
    tarjetasDePrueba: list[TarjetaDePrueba]


# Las que la pantalla de pago muestra al comprador para que pueda probar. Las
# dos primeras son las tarjetas de prueba que publica PayU; la tercera termina
# en 0000, que es lo que la pasarela simulada trata como saldo insuficiente.
TARJETAS_DE_PRUEBA = [
    {'numero': '4111 1111 1111 1111', 'franquicia': 'Visa', 'resultado': 'Pago aprobado', 'donde': 'ambas'},
    {'numero': '5471 3000 0000 0003', 'franquicia': 'Mastercard', 'resultado': 'Pago aprobado', 'donde': 'ambas'},
    {'numero': '4000 0002 0000 0000', 'franquicia': 'Visa',
     'resultado': 'Rechazada: fondos insuficientes', 'donde': 'simulada'},
]


# --- Acceso a la venta -----------------------------------------------------

def _venta_a_pagar(conn, venta_id: int, usuario: dict[str, Any]):
    venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()
    if venta is None:
        raise HTTPException(status_code=404, detail='La venta no existe.')
    if usuario.get('role') == 'Cliente' and not la_venta_es_del_cliente(venta, usuario):
        raise HTTPException(status_code=403, detail='Esta compra no es tuya.')
    if venta['estado'] == 'Anulada':
        raise HTTPException(status_code=400, detail='La venta está anulada y no se puede pagar.')
    if venta['estado'] == 'Pagada':
        raise HTTPException(status_code=400, detail='Esta compra ya está pagada.')
    if money(venta['total']) <= 0:
        raise HTTPException(status_code=400, detail='La venta no tiene un total que cobrar.')
    return venta


def _factura_de(conn, venta_id: int) -> Optional[int]:
    fila = conn.execute('SELECT id FROM facturas WHERE venta_id = ?', (venta_id,)).fetchone()
    return fila['id'] if fila else None


def _crear_pago(conn, venta, usuario: dict[str, Any], pasarela: str, metodo: str, **extra) -> str:
    referencia = next_number(conn, 'pagos', 'PG')
    conn.execute(
        '''
        INSERT INTO pagos (referencia, venta_id, factura_id, cliente_id, cliente_nombre, pasarela, metodo,
                           franquicia, ultimos_digitos, cuotas, monto, moneda, estado, motivo, transaccion, fecha)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''',
        (referencia, venta['id'], _factura_de(conn, venta['id']), venta['cliente_id'] or usuario.get('id'),
         venta['cliente_nombre'], pasarela, metodo, extra.get('franquicia', ''), extra.get('ultimos_digitos', ''),
         extra.get('cuotas', 1), money(venta['total']), MONEDA, extra.get('estado', 'Pendiente'),
         extra.get('motivo', ''), extra.get('transaccion', ''), now_iso()),
    )
    conn.commit()
    return referencia


def _marcar_pagada(conn, venta_id: int) -> None:
    """Un pago aprobado deja pagadas la venta y su factura."""
    conn.execute("UPDATE ventas SET estado = 'Pagada' WHERE id = ? AND estado <> 'Anulada'", (venta_id,))
    conn.execute("UPDATE facturas SET estado = 'Pagada' WHERE venta_id = ? AND estado <> 'Anulada'", (venta_id,))
    conn.commit()


def _pago_por_referencia(conn, referencia: str):
    return conn.execute('SELECT * FROM pagos WHERE referencia = ?', (referencia,)).fetchone()


# --- Endpoints -------------------------------------------------------------

@router.get('/config', response_model=ConfigPagos, summary='Medios de pago disponibles')
def configuracion(_: dict[str, Any] = Depends(get_current_user)):
    """Le dice al sitio qué pasarelas puede ofrecer y con qué tarjetas probar."""
    return {
        'pasarelas': ['payu', 'simulada'],
        'payuPruebas': en_pruebas(),
        'tarjetasDePrueba': TARJETAS_DE_PRUEBA,
    }


@router.post('/payu', response_model=FormularioPayU, summary='Empezar el pago en PayU')
def iniciar_payu(payload: PagoPayU, current_user: dict[str, Any] = Depends(get_current_user)):
    """Prepara el formulario firmado con el que el navegador salta a PayU.

    El monto no llega del navegador: se lee de la venta, y la firma lo sella,
    así que nadie puede pagar dos millones con un formulario de mil pesos.
    """
    conn = get_db_connection()
    try:
        venta = _venta_a_pagar(conn, payload.ventaId, current_user)
        referencia = _crear_pago(conn, venta, current_user, 'payu', 'payu')
        monto = money(venta['total'])
        config = payu_config()
        volver = _origen_valido(payload.origen) or _frontend_url()
        campos = {
            'merchantId': config['merchantId'],
            'accountId': config['accountId'],
            'description': f"Compra {venta['numero']} en SimonC Realidad Virtual",
            'referenceCode': referencia,
            'amount': _monto_para_firma(monto),
            'tax': '0',
            'taxReturnBase': '0',
            'currency': MONEDA,
            'signature': firma_peticion(referencia, monto, config),
            'test': '1' if en_pruebas() else '0',
            'buyerEmail': current_user.get('email', ''),
            'buyerFullName': venta['cliente_nombre'],
            'payerFullName': venta['cliente_nombre'],
            'payerEmail': current_user.get('email', ''),
            'payerDocument': venta['cliente_documento'] or '',
            'telephone': current_user.get('phone', '') or '',
            'responseUrl': f'{volver}/pago/respuesta',
        }
        api = _api_publica()
        if api:
            campos['confirmationUrl'] = f'{api}/api/pagos/payu/confirmacion'
        return {'url': config['url'], 'campos': campos, 'referencia': referencia, 'pruebas': en_pruebas()}
    finally:
        conn.close()


def _aplicar_respuesta(parametros: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Guarda lo que PayU contestó, una sola vez y solo si la firma cierra."""
    if not firma_valida(parametros):
        raise HTTPException(status_code=400, detail='La respuesta de la pasarela no es válida.')

    referencia = str(parametros.get('referenceCode')).strip()
    estado = ESTADOS_PAYU.get(str(parametros.get('transactionState')).strip(), 'Error')
    motivo = str(parametros.get('message') or parametros.get('lapResponseCode') or '').strip()
    transaccion = str(parametros.get('transactionId') or parametros.get('reference_pol') or '').strip()

    conn = get_db_connection()
    try:
        pago = _pago_por_referencia(conn, referencia)
        if pago is None:
            raise HTTPException(status_code=404, detail='Ese pago no existe.')
        if money(parametros.get('TX_VALUE')) != money(pago['monto']):
            raise HTTPException(status_code=400, detail='El valor pagado no coincide con la venta.')

        if pago['estado'] != estado or not pago['transaccion']:
            conn.execute(
                'UPDATE pagos SET estado = ?, motivo = ?, transaccion = ?, factura_id = ? WHERE id = ?',
                (estado, motivo, transaccion, _factura_de(conn, pago['venta_id']), pago['id']),
            )
            conn.commit()
        if estado == 'Aprobado':
            _marcar_pagada(conn, pago['venta_id'])

        actualizado = conn.execute('SELECT * FROM pagos WHERE id = ?', (pago['id'],)).fetchone()
        venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (pago['venta_id'],)).fetchone()
        return {'pago': pago_row(actualizado), 'venta': venta_row(venta) if venta else None}
    finally:
        conn.close()


@router.post('/payu/respuesta', response_model=ResultadoPago, summary='Confirmar el pago al volver de PayU')
def respuesta_payu(parametros: dict[str, Any], _: dict[str, Any] = Depends(get_current_user)):
    """Lo que el sitio manda al volver de PayU, con los datos de la dirección."""
    resultado = _aplicar_respuesta(parametros)
    mensajes = {
        'Aprobado': 'El pago fue aprobado.',
        'Rechazado': 'El pago fue rechazado.',
        'Pendiente': 'El pago quedó pendiente de confirmación.',
    }
    return {'message': mensajes.get(resultado['pago']['estado'], 'La pasarela reportó un error.'), **resultado}


@router.post('/payu/confirmacion', include_in_schema=False)
async def confirmacion_payu(request: Request):
    """Aviso que PayU le manda al servidor, sin navegador de por medio.

    Va sin token a propósito: quien llama es PayU, no una persona. Lo que
    autoriza el cambio es la firma, que se comprueba igual que en la respuesta.
    """
    formulario = await request.form()
    parametros = {clave: valor for clave, valor in formulario.items()}
    if not parametros:
        parametros = await request.json()
    # PayU nombra distinto dos campos del aviso que del retorno.
    parametros.setdefault('transactionState', parametros.get('state_pol'))
    parametros.setdefault('TX_VALUE', parametros.get('value'))
    parametros.setdefault('signature', parametros.get('sign'))
    _aplicar_respuesta(parametros)
    return {'message': 'Confirmación recibida.'}


@router.post('/simulado', response_model=ResultadoPago, status_code=201, summary='Pagar con la pasarela simulada')
def pagar_simulado(payload: PagoTarjeta, current_user: dict[str, Any] = Depends(get_current_user)):
    """Cobra sin salir del sitio, con las reglas de arriba.

    Del formulario no se guarda nada sensible: el número se usa para validar y
    se descarta, y del resultado quedan la franquicia y los cuatro últimos
    dígitos.
    """
    numero = ''.join(c for c in payload.numero if c.isdigit())
    if not luhn(numero):
        raise HTTPException(status_code=400, detail='El número de la tarjeta no es válido.')
    if not _vencimiento_valido(payload.vencimiento):
        raise HTTPException(status_code=400, detail='La fecha de vencimiento no es válida.')
    if not payload.cvv.isdigit():
        raise HTTPException(status_code=400, detail='El código de seguridad debe ser numérico.')

    estado, motivo = _resultado_simulado(payload.nombre, numero, payload.cvv)

    conn = get_db_connection()
    try:
        venta = _venta_a_pagar(conn, payload.ventaId, current_user)
        referencia = _crear_pago(
            conn, venta, current_user, 'simulada', 'tarjeta',
            franquicia=franquicia_de(numero), ultimos_digitos=numero[-4:], cuotas=payload.cuotas,
            estado=estado, motivo=motivo, transaccion=f'SIM-{referencia_corta(numero, venta["numero"])}',
        )
        if estado == 'Aprobado':
            _marcar_pagada(conn, venta['id'])

        pago = _pago_por_referencia(conn, referencia)
        venta_final = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta['id'],)).fetchone()
        return {
            'message': motivo,
            'pago': pago_row(pago),
            'venta': venta_row(venta_final),
        }
    finally:
        conn.close()


def referencia_corta(numero: str, venta_numero: str) -> str:
    """Identificador de la transacción simulada, sin el número de la tarjeta."""
    semilla = f'{venta_numero}-{numero[-4:]}-{now_iso()}'
    return hashlib.sha256(semilla.encode('utf-8')).hexdigest()[:12].upper()


@router.get('', response_model=PagosResponse, summary='Historial de pagos')
@router.get('/', response_model=PagosResponse, include_in_schema=False)
def listar_pagos(
    current_user: dict[str, Any] = Depends(get_current_user),
    estado: Optional[str] = Query(default=None, description='Aprobado, Rechazado, Pendiente o Error'),
    referencia: Optional[str] = None,
):
    """Todos los pagos para quien administra; los suyos para el Cliente."""
    if estado and estado not in ESTADOS_PAGO:
        raise HTTPException(status_code=400, detail='Ese estado de pago no existe.')

    filtros: list[str] = []
    parametros: list[Any] = []
    if estado:
        filtros.append('p.estado = ?')
        parametros.append(estado)
    if referencia:
        filtros.append('p.referencia LIKE ?')
        parametros.append(f'%{referencia}%')

    conn = get_db_connection()
    try:
        consulta = 'SELECT p.* FROM pagos p'
        if filtros:
            consulta += ' WHERE ' + ' AND '.join(filtros)
        consulta += ' ORDER BY p.id DESC'
        filas = conn.execute(consulta, tuple(parametros)).fetchall()

        pagos = [pago_row(fila) for fila in filas]
        if current_user.get('role') == 'Cliente':
            documento = (current_user.get('document_number') or '').strip()
            ventas = {
                fila['id']: fila
                for fila in conn.execute('SELECT id, cliente_id, cliente_documento FROM ventas').fetchall()
            }
            pagos = [
                pago for pago in pagos
                if pago['ventaId'] in ventas and la_venta_es_del_cliente(ventas[pago['ventaId']], {
                    'id': current_user.get('id'), 'document_number': documento,
                })
            ]

        aprobado = money(sum(pago['monto'] for pago in pagos if pago['estado'] == 'Aprobado'))
        return {'pagos': pagos, 'resumen': {'cantidad': len(pagos), 'aprobado': aprobado}}
    finally:
        conn.close()


@router.get('/{pago_id}', response_model=PagoResponse, summary='Detalle de un pago')
def obtener_pago(pago_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        fila = conn.execute('SELECT * FROM pagos WHERE id = ?', (pago_id,)).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail='Ese pago no existe.')
        if current_user.get('role') == 'Cliente':
            venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (fila['venta_id'],)).fetchone()
            if venta is None or not la_venta_es_del_cliente(venta, current_user):
                raise HTTPException(status_code=403, detail='Ese pago no es tuyo.')
        return pago_row(fila)
    finally:
        conn.close()
