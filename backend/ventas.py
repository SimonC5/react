"""Módulo de ventas: registro, historial con filtros y detalle de la venta."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from .core import get_current_user, get_db_connection, require_roles
    from .comercial import (
        ESTADOS_VENTA,
        TIPOS_ITEM,
        detalle_row,
        money,
        next_number,
        now_iso,
        parse_date,
        venta_row,
    )
except ImportError:
    from core import get_current_user, get_db_connection, require_roles
    from comercial import (
        ESTADOS_VENTA,
        TIPOS_ITEM,
        detalle_row,
        money,
        next_number,
        now_iso,
        parse_date,
        venta_row,
    )

router = APIRouter(prefix='/api/ventas', tags=['ventas'])

IVA = 0.19


class VentaItem(BaseModel):
    tipo: str = Field(description='producto o servicio')
    itemId: Optional[int] = None
    nombre: Optional[str] = None
    cantidad: float = 1
    precioUnitario: Optional[float] = None
    descuento: float = 0


class VentaCreate(BaseModel):
    clienteId: Optional[int] = None
    cliente: str
    clienteDocumento: str = ''
    observaciones: str = ''
    aplicaImpuesto: bool = True
    items: list[VentaItem]


class VentaEstado(BaseModel):
    estado: str


def _catalog_item(conn, tipo: str, item_id: Optional[int]) -> Optional[dict[str, Any]]:
    if item_id is None:
        return None
    table = 'productos' if tipo == 'producto' else 'servicios'
    row = conn.execute(f'SELECT id, name, price FROM {table} WHERE id = ?', (item_id,)).fetchone()
    return dict(row) if row else None


def _load_detalle(conn, venta_id: int) -> list[dict[str, Any]]:
    rows = conn.execute('SELECT * FROM detalle_ventas WHERE venta_id = ? ORDER BY id', (venta_id,)).fetchall()
    return [detalle_row(row) for row in rows]


class PedidoItem(BaseModel):
    """Línea de un pedido hecho por el propio cliente desde el carrito."""

    tipo: str = Field(description='producto o servicio')
    itemId: int
    cantidad: float = 1


class PedidoCreate(BaseModel):
    observaciones: str = ''
    items: list[PedidoItem]


@router.post('', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
@router.post('/', dependencies=[Depends(require_roles('Administrador', 'Empleado'))], include_in_schema=False)
def crear_venta(payload: VentaCreate, current_user: dict[str, Any] = Depends(get_current_user)):
    return _registrar_venta(payload, current_user)


@router.post('/pedido')
def crear_pedido(payload: PedidoCreate, current_user: dict[str, Any] = Depends(get_current_user)):
    """Pedido del carrito: la venta queda a nombre de quien tiene la sesión.

    El cliente solo elige qué y cuánto. Ni el nombre del comprador ni los
    precios ni los descuentos llegan desde el navegador: se toman del token y
    del catálogo, de modo que nadie pueda pedir a nombre de otro ni fijarse su
    propio precio.
    """
    _verificar_disponibles(payload.items)
    nombre = f"{current_user.get('name', '')} {current_user.get('last_name', '')}".strip()
    venta = VentaCreate(
        clienteId=current_user.get('id'),
        cliente=nombre or current_user.get('email', 'Cliente'),
        clienteDocumento=current_user.get('document_number', '') or '',
        observaciones=payload.observaciones,
        items=[VentaItem(tipo=item.tipo, itemId=item.itemId, cantidad=item.cantidad) for item in payload.items],
    )
    resultado = _registrar_venta(venta, current_user)
    return {'message': 'Pedido registrado correctamente.', 'venta': resultado['venta']}


def _verificar_disponibles(items: list[PedidoItem]) -> None:
    """Un pedido solo puede llevar artículos que hoy estén publicados."""
    conn = get_db_connection()
    try:
        for item in items:
            tipo = item.tipo.strip().lower()
            if tipo not in TIPOS_ITEM:
                raise HTTPException(status_code=400, detail='Cada línea debe ser de tipo producto o servicio.')
            tabla = 'productos' if tipo == 'producto' else 'servicios'
            fila = conn.execute(f'SELECT active FROM {tabla} WHERE id = ?', (item.itemId,)).fetchone()
            if fila is None or not fila['active']:
                raise HTTPException(status_code=400, detail='Uno de los artículos del carrito ya no está disponible.')
    finally:
        conn.close()


def _registrar_venta(payload: VentaCreate, current_user: dict[str, Any]) -> dict[str, Any]:
    if not payload.cliente.strip():
        raise HTTPException(status_code=400, detail='El nombre del cliente es obligatorio.')
    if not payload.items:
        raise HTTPException(status_code=400, detail='La venta debe incluir al menos un producto o servicio.')

    conn = get_db_connection()
    try:
        lineas = []
        subtotal = descuento_total = impuesto_total = 0.0

        for item in payload.items:
            tipo = item.tipo.strip().lower()
            if tipo not in TIPOS_ITEM:
                raise HTTPException(status_code=400, detail='Cada línea debe ser de tipo producto o servicio.')
            if item.cantidad <= 0:
                raise HTTPException(status_code=400, detail='La cantidad debe ser mayor que cero.')

            catalogo = _catalog_item(conn, tipo, item.itemId)
            nombre = (item.nombre or (catalogo or {}).get('name') or '').strip()
            if not nombre:
                raise HTTPException(status_code=400, detail='No se pudo identificar el producto o servicio vendido.')

            precio = money(item.precioUnitario if item.precioUnitario is not None else (catalogo or {}).get('price'))
            bruto = money(precio * item.cantidad)
            descuento = money(min(max(item.descuento, 0), bruto))
            base = money(bruto - descuento)
            impuesto = money(base * IVA) if payload.aplicaImpuesto else 0.0

            subtotal += base
            descuento_total += descuento
            impuesto_total += impuesto
            lineas.append((tipo, item.itemId, nombre, item.cantidad, precio, descuento, impuesto, base, money(base + impuesto)))

        total = money(subtotal + impuesto_total)
        numero = next_number(conn, 'ventas', 'VT')
        usuario_nombre = f"{current_user.get('name', '')} {current_user.get('last_name', '')}".strip()

        cursor = conn.execute(
            '''
            INSERT INTO ventas (numero, cliente_id, cliente_nombre, cliente_documento, usuario_id, usuario_nombre,
                                subtotal, descuento, impuestos, total, estado, observaciones, fecha)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (numero, payload.clienteId, payload.cliente.strip(), payload.clienteDocumento.strip(),
             current_user.get('id'), usuario_nombre, money(subtotal), money(descuento_total),
             money(impuesto_total), total, 'Registrada', payload.observaciones.strip(), now_iso()),
        )
        venta_id = cursor.lastrowid

        for linea in lineas:
            conn.execute(
                '''
                INSERT INTO detalle_ventas (venta_id, item_tipo, item_id, nombre, cantidad, precio_unitario,
                                            descuento, impuesto, subtotal, total)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ''',
                (venta_id, *linea),
            )
        conn.commit()

        venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()
        return {
            'message': 'Venta registrada correctamente.',
            'venta': {**venta_row(venta), 'detalle': _load_detalle(conn, venta_id)},
        }
    finally:
        conn.close()


@router.get('')
@router.get('/', include_in_schema=False)
def listar_ventas(
    current_user: dict[str, Any] = Depends(get_current_user),
    fechaInicio: Optional[str] = Query(None, description='YYYY-MM-DD'),
    fechaFin: Optional[str] = Query(None, description='YYYY-MM-DD'),
    cliente: Optional[str] = None,
    estado: Optional[str] = None,
    producto: Optional[str] = None,
    servicio: Optional[str] = None,
    valorMinimo: Optional[float] = None,
    valorMaximo: Optional[float] = None,
    limite: int = Query(100, ge=1, le=500),
):
    """Historial de ventas. El cliente solo ve las suyas."""
    filtros = ['1 = 1']
    parametros: list[Any] = []

    desde = parse_date(fechaInicio)
    hasta = parse_date(fechaFin, end_of_day=True)
    if desde:
        filtros.append('v.fecha >= ?')
        parametros.append(desde)
    if hasta:
        filtros.append('v.fecha <= ?')
        parametros.append(hasta)
    if cliente:
        filtros.append('(v.cliente_nombre LIKE ? OR v.cliente_documento LIKE ?)')
        parametros.extend([f'%{cliente}%', f'%{cliente}%'])
    if estado:
        filtros.append('v.estado = ?')
        parametros.append(estado)
    if valorMinimo is not None:
        filtros.append('v.total >= ?')
        parametros.append(valorMinimo)
    if valorMaximo is not None:
        filtros.append('v.total <= ?')
        parametros.append(valorMaximo)
    for tipo, termino in (('producto', producto), ('servicio', servicio)):
        if termino:
            filtros.append(
                'EXISTS (SELECT 1 FROM detalle_ventas d WHERE d.venta_id = v.id AND d.item_tipo = ? AND d.nombre LIKE ?)'
            )
            parametros.extend([tipo, f'%{termino}%'])

    if current_user.get('role') == 'Cliente':
        filtros.append('(v.cliente_id = ? OR v.cliente_documento = ?)')
        parametros.extend([current_user.get('id'), current_user.get('document_number', '')])

    conn = get_db_connection()
    try:
        rows = conn.execute(
            f'SELECT v.* FROM ventas v WHERE {" AND ".join(filtros)} ORDER BY v.fecha DESC, v.id DESC LIMIT ?',
            (*parametros, limite),
        ).fetchall()
        ventas = [venta_row(row) for row in rows]
        return {
            'ventas': ventas,
            'resumen': {
                'cantidad': len(ventas),
                'total': money(sum(item['total'] for item in ventas)),
            },
        }
    finally:
        conn.close()


@router.get('/{venta_id}')
def obtener_venta(venta_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='La venta no existe.')
        if current_user.get('role') == 'Cliente' and row['cliente_id'] != current_user.get('id'):
            raise HTTPException(status_code=403, detail='No tienes permisos para consultar esta venta.')
        return {'venta': {**venta_row(row), 'detalle': _load_detalle(conn, venta_id)}}
    finally:
        conn.close()


@router.patch('/{venta_id}/estado', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def cambiar_estado(venta_id: int, payload: VentaEstado):
    if payload.estado not in ESTADOS_VENTA:
        raise HTTPException(status_code=400, detail=f'Estado inválido. Use uno de: {", ".join(ESTADOS_VENTA)}.')
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT id FROM ventas WHERE id = ?', (venta_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='La venta no existe.')
        conn.execute('UPDATE ventas SET estado = ? WHERE id = ?', (payload.estado, venta_id))
        conn.commit()
        return {'message': 'Estado actualizado.', 'estado': payload.estado}
    finally:
        conn.close()
