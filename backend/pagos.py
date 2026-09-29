"""Pasarela de pago de la tienda.

Es un formulario dentro del propio sitio: el comprador elige el medio de pago,
llena los datos y ve el resultado sin salir de la página. No hay salto a una
pasarela externa.

Hay tres medios, y los tres terminan con una fila en la tabla ``pagos``:

- **Tarjeta de crédito o débito.** Se valida el número con el algoritmo de Luhn
  y la fecha de vencimiento, y el cobro se aprueba o se rechaza.
- **PSE (débito desde la cuenta bancaria).** Se elige el banco y se identifica
  al titular.
- **Efectivo.** Genera un código para pagar en Efecty o Baloto, así que el pago
  queda *Pendiente* hasta que se confirme y la compra sigue sin pagar.

Un pago aprobado deja la venta y su factura en **Pagada**. Nunca se guarda el
número completo de la tarjeta ni el código de seguridad: de la tarjeta solo
quedan la franquicia y los cuatro últimos dígitos, que es lo que lleva un
recibo. El valor a cobrar tampoco llega del navegador: se lee de la venta.
"""

import hashlib
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

try:
    from .core import get_current_user, get_db_connection
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
    from core import get_current_user, get_db_connection
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
METODOS = ('tarjeta', 'pse', 'efectivo')

BANCOS = (
    'Bancolombia', 'Banco de Bogotá', 'Davivienda', 'BBVA Colombia',
    'Banco de Occidente', 'Banco Popular', 'Scotiabank Colpatria', 'Nequi',
)

PUNTOS_DE_PAGO = ('Efecty', 'Baloto', 'Su Red')

TIPOS_DE_DOCUMENTO = ('CC', 'CE', 'NIT', 'TI', 'PA')

FRANQUICIAS = (
    ('Visa', ('4',)),
    ('Mastercard', ('51', '52', '53', '54', '55', '2221', '2720')),
    ('American Express', ('34', '37')),
    ('Diners Club', ('36', '38', '30')),
)

# Las que la pantalla de pago muestra para poder probar sin inventar números.
# Una tarjeta terminada en 0000 no tiene fondos y el código 666 lo rechaza el
# banco: son las mismas señales que usan los entornos de prueba de verdad.
TARJETAS_DE_PRUEBA = (
    {'numero': '4111 1111 1111 1111', 'franquicia': 'Visa', 'resultado': 'Pago aprobado'},
    {'numero': '5471 3000 0000 0003', 'franquicia': 'Mastercard', 'resultado': 'Pago aprobado'},
    {'numero': '4000 0002 0000 0000', 'franquicia': 'Visa', 'resultado': 'Rechazada: sin fondos'},
)


# --- Validación de la tarjeta ----------------------------------------------

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


def vencimiento_valido(valor: str) -> bool:
    """La fecha viene como MM/AA y tiene que ser de este mes en adelante."""
    texto = str(valor or '').strip()
    if len(texto) != 5 or texto[2] != '/':
        return False
    mes, anio = texto[:2], texto[3:]
    if not (mes.isdigit() and anio.isdigit()) or not 1 <= int(mes) <= 12:
        return False
    hoy = date.today()
    return (2000 + int(anio), int(mes)) >= (hoy.year, hoy.month)


def _codigo(semilla: str) -> str:
    """Número de aprobación del banco, o código para pagar en efectivo."""
    return hashlib.sha256(f'{semilla}-{now_iso()}'.encode('utf-8')).hexdigest()[:12].upper()


# --- Esquemas --------------------------------------------------------------

class PagoCreate(BaseModel):
    """Formulario de pago. Cada medio usa solo los campos que le tocan."""

    model_config = ConfigDict(json_schema_extra={'examples': [{
        'ventaId': 1, 'metodo': 'tarjeta', 'nombre': 'Ana Restrepo',
        'numero': '4111111111111111', 'vencimiento': '12/30', 'cvv': '123', 'cuotas': 1,
    }]})

    ventaId: int
    metodo: str = Field(default='tarjeta', description='tarjeta, pse o efectivo')

    # Tarjeta. El número y el código se usan para validar y se descartan.
    nombre: str = Field(default='', max_length=80, description='Nombre como aparece en la tarjeta')
    numero: str = Field(default='', max_length=25, description='No se guarda: solo los cuatro últimos dígitos')
    vencimiento: str = Field(default='', max_length=5, description='MM/AA')
    cvv: str = Field(default='', max_length=4, description='No se guarda')
    cuotas: int = Field(default=1, ge=1, le=36)

    # PSE.
    banco: str = Field(default='', max_length=60)

    # PSE y efectivo: a nombre de quién va el pago.
    tipoDocumento: str = Field(default='CC', max_length=5)
    documento: str = Field(default='', max_length=15)

    # Efectivo.
    puntoDePago: str = Field(default='', max_length=30)


class PagoResponse(BaseModel):
    id: int
    referencia: str
    ventaId: int
    facturaId: Optional[int] = None
    clienteId: Optional[int] = None
    cliente: str = ''
    metodo: str
    entidad: str = ''
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


class TarjetaDePrueba(BaseModel):
    numero: str
    franquicia: str
    resultado: str


class ConfigPagos(BaseModel):
    """Lo que la pantalla de pago necesita para dibujar el formulario."""

    metodos: list[str]
    bancos: list[str]
    puntosDePago: list[str]
    tiposDeDocumento: list[str]
    tarjetasDePrueba: list[TarjetaDePrueba]


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


def _marcar_pagada(conn, venta_id: int) -> None:
    """Un pago aprobado deja pagadas la venta y su factura."""
    conn.execute("UPDATE ventas SET estado = 'Pagada' WHERE id = ? AND estado <> 'Anulada'", (venta_id,))
    conn.execute("UPDATE facturas SET estado = 'Pagada' WHERE venta_id = ? AND estado <> 'Anulada'", (venta_id,))
    conn.commit()


# --- Cada medio de pago ----------------------------------------------------

def _cobrar_con_tarjeta(payload: PagoCreate, numero_de_venta: str) -> dict[str, Any]:
    numero = ''.join(c for c in payload.numero if c.isdigit())
    if len(payload.nombre.strip()) < 3:
        raise HTTPException(status_code=400, detail='Escribe el nombre del titular de la tarjeta.')
    if not luhn(numero):
        raise HTTPException(status_code=400, detail='El número de la tarjeta no es válido.')
    if not vencimiento_valido(payload.vencimiento):
        raise HTTPException(status_code=400, detail='La fecha de vencimiento no es válida.')
    if not payload.cvv.isdigit() or len(payload.cvv) < 3:
        raise HTTPException(status_code=400, detail='El código de seguridad no es válido.')

    datos = {
        'entidad': franquicia_de(numero),
        'ultimos_digitos': numero[-4:],
        'cuotas': payload.cuotas,
        'transaccion': _codigo(numero_de_venta),
    }
    if payload.cvv == '666' or 'REJECTED' in payload.nombre.upper():
        return {**datos, 'estado': 'Rechazado', 'motivo': 'La entidad bancaria rechazó la transacción.'}
    if numero.endswith('0000'):
        return {**datos, 'estado': 'Rechazado', 'motivo': 'Fondos insuficientes.'}
    return {**datos, 'estado': 'Aprobado', 'motivo': 'Transacción aprobada.'}


def _cobrar_con_pse(payload: PagoCreate, numero_de_venta: str) -> dict[str, Any]:
    if payload.banco not in BANCOS:
        raise HTTPException(status_code=400, detail='Elige uno de los bancos de la lista.')
    if payload.tipoDocumento not in TIPOS_DE_DOCUMENTO:
        raise HTTPException(status_code=400, detail='Ese tipo de documento no existe.')
    if not payload.documento.strip().isdigit():
        raise HTTPException(status_code=400, detail='El número de documento debe ser numérico.')

    return {
        'entidad': payload.banco,
        'cuotas': 1,
        'transaccion': _codigo(numero_de_venta),
        'estado': 'Aprobado',
        'motivo': f'Débito aprobado desde {payload.banco}.',
    }


def _cobrar_en_efectivo(payload: PagoCreate, numero_de_venta: str) -> dict[str, Any]:
    if payload.puntoDePago not in PUNTOS_DE_PAGO:
        raise HTTPException(status_code=400, detail='Elige uno de los puntos de pago de la lista.')

    codigo = _codigo(numero_de_venta)
    return {
        'entidad': payload.puntoDePago,
        'cuotas': 1,
        'transaccion': codigo,
        # El dinero todavía no ha entrado, así que la compra sigue sin pagar.
        'estado': 'Pendiente',
        'motivo': f'Paga en {payload.puntoDePago} con el código {codigo}. Tienes 3 días.',
    }


COBROS = {'tarjeta': _cobrar_con_tarjeta, 'pse': _cobrar_con_pse, 'efectivo': _cobrar_en_efectivo}


# --- Endpoints -------------------------------------------------------------

@router.get('/config', response_model=ConfigPagos, summary='Datos del formulario de pago')
def configuracion(_: dict[str, Any] = Depends(get_current_user)):
    """Medios de pago, bancos y puntos de pago que acepta la tienda."""
    return {
        'metodos': list(METODOS),
        'bancos': list(BANCOS),
        'puntosDePago': list(PUNTOS_DE_PAGO),
        'tiposDeDocumento': list(TIPOS_DE_DOCUMENTO),
        'tarjetasDePrueba': list(TARJETAS_DE_PRUEBA),
    }


@router.post('', response_model=ResultadoPago, status_code=201, summary='Pagar una compra')
@router.post('/', response_model=ResultadoPago, status_code=201, include_in_schema=False)
def pagar(payload: PagoCreate, current_user: dict[str, Any] = Depends(get_current_user)):
    """Cobra la venta con el medio de pago elegido.

    El importe no llega del formulario: se lee de la venta, de modo que nadie
    pueda pagar dos millones con un formulario de mil pesos.
    """
    metodo = payload.metodo.strip().lower()
    if metodo not in COBROS:
        raise HTTPException(status_code=400, detail='Ese medio de pago no existe.')

    conn = get_db_connection()
    try:
        venta = _venta_a_pagar(conn, payload.ventaId, current_user)
        resultado = COBROS[metodo](payload, venta['numero'])

        referencia = next_number(conn, 'pagos', 'PG')
        conn.execute(
            '''
            INSERT INTO pagos (referencia, venta_id, factura_id, cliente_id, cliente_nombre, metodo,
                               entidad, ultimos_digitos, cuotas, monto, moneda, estado, motivo, transaccion, fecha)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (referencia, venta['id'], _factura_de(conn, venta['id']),
             venta['cliente_id'] or current_user.get('id'), venta['cliente_nombre'], metodo,
             resultado['entidad'], resultado.get('ultimos_digitos', ''), resultado.get('cuotas', 1),
             money(venta['total']), MONEDA, resultado['estado'], resultado['motivo'],
             resultado['transaccion'], now_iso()),
        )
        conn.commit()

        if resultado['estado'] == 'Aprobado':
            _marcar_pagada(conn, venta['id'])

        pago = conn.execute('SELECT * FROM pagos WHERE referencia = ?', (referencia,)).fetchone()
        actualizada = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta['id'],)).fetchone()
        return {'message': resultado['motivo'], 'pago': pago_row(pago), 'venta': venta_row(actualizada)}
    finally:
        conn.close()


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
        filtros.append('estado = ?')
        parametros.append(estado)
    if referencia:
        filtros.append('referencia LIKE ?')
        parametros.append(f'%{referencia}%')

    conn = get_db_connection()
    try:
        consulta = 'SELECT * FROM pagos'
        if filtros:
            consulta += ' WHERE ' + ' AND '.join(filtros)
        consulta += ' ORDER BY id DESC'
        pagos = [pago_row(fila) for fila in conn.execute(consulta, tuple(parametros)).fetchall()]

        if current_user.get('role') == 'Cliente':
            ventas = {
                fila['id']: fila
                for fila in conn.execute('SELECT id, cliente_id, cliente_documento FROM ventas').fetchall()
            }
            pagos = [
                pago for pago in pagos
                if pago['ventaId'] in ventas and la_venta_es_del_cliente(ventas[pago['ventaId']], current_user)
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
