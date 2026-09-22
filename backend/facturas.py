"""Módulo de facturación: generación, consulta y descarga de facturas de venta."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

try:
    from .core import get_current_user, get_db_connection, require_roles
    from .comercial import ESTADOS_FACTURA, detalle_row, factura_row, next_number, now_iso, parse_date, venta_row
    from .documentos import construir_factura_pdf
except ImportError:
    from core import get_current_user, get_db_connection, require_roles
    from comercial import ESTADOS_FACTURA, detalle_row, factura_row, next_number, now_iso, parse_date, venta_row
    from documentos import construir_factura_pdf

router = APIRouter(prefix='/api/facturas', tags=['facturas'])


class FacturaCreate(BaseModel):
    ventaId: int


class FacturaEstado(BaseModel):
    estado: str


def _detalle_factura(conn, factura_id: int) -> list[dict[str, Any]]:
    rows = conn.execute('SELECT * FROM detalle_facturas WHERE factura_id = ? ORDER BY id', (factura_id,)).fetchall()
    return [detalle_row(row) for row in rows]


def _factura_con_venta(conn, factura_id: int):
    return conn.execute(
        '''
        SELECT f.*, v.numero AS venta_numero
        FROM facturas f
        JOIN ventas v ON v.id = f.venta_id
        WHERE f.id = ?
        ''',
        (factura_id,),
    ).fetchone()


@router.post('', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
@router.post('/', dependencies=[Depends(require_roles('Administrador', 'Empleado'))], include_in_schema=False)
def generar_factura(payload: FacturaCreate):
    """Emite la factura a partir de una venta ya registrada."""
    return emitir_factura_de_venta(payload.ventaId)


def emitir_factura_de_venta(venta_id: int) -> dict[str, Any]:
    """Emite la factura de una venta.

    La usan el botón "Generar una factura" del panel y también el pedido del
    carrito, que factura solo para que el cliente vea su factura al instante.
    """
    conn = get_db_connection()
    try:
        venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,)).fetchone()
        if venta is None:
            raise HTTPException(status_code=404, detail='La venta no existe.')
        if venta['estado'] == 'Anulada':
            raise HTTPException(status_code=400, detail='No se puede facturar una venta anulada.')

        existente = conn.execute('SELECT id FROM facturas WHERE venta_id = ?', (venta_id,)).fetchone()
        if existente is not None:
            raise HTTPException(status_code=409, detail='Esta venta ya tiene una factura emitida.')

        numero = next_number(conn, 'facturas', 'FV')
        cursor = conn.execute(
            '''
            INSERT INTO facturas (numero, venta_id, cliente_nombre, cliente_documento, subtotal, descuento,
                                  impuestos, total, estado, fecha)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ''',
            (numero, venta['id'], venta['cliente_nombre'], venta['cliente_documento'], venta['subtotal'],
             venta['descuento'], venta['impuestos'], venta['total'], 'Emitida', now_iso()),
        )
        factura_id = cursor.lastrowid

        lineas = conn.execute('SELECT * FROM detalle_ventas WHERE venta_id = ? ORDER BY id', (venta_id,)).fetchall()
        for linea in lineas:
            conn.execute(
                '''
                INSERT INTO detalle_facturas (factura_id, item_tipo, nombre, cantidad, precio_unitario,
                                              descuento, impuesto, subtotal, total)
                VALUES (?,?,?,?,?,?,?,?,?)
                ''',
                (factura_id, linea['item_tipo'], linea['nombre'], linea['cantidad'], linea['precio_unitario'],
                 linea['descuento'], linea['impuesto'], linea['subtotal'], linea['total']),
            )
        conn.commit()

        factura = _factura_con_venta(conn, factura_id)
        return {
            'message': 'Factura generada correctamente.',
            'factura': {**factura_row(factura), 'detalle': _detalle_factura(conn, factura_id)},
        }
    finally:
        conn.close()


@router.get('')
@router.get('/', include_in_schema=False)
def listar_facturas(
    current_user: dict[str, Any] = Depends(get_current_user),
    numero: Optional[str] = None,
    cliente: Optional[str] = None,
    estado: Optional[str] = None,
    fechaInicio: Optional[str] = Query(None, description='YYYY-MM-DD'),
    fechaFin: Optional[str] = Query(None, description='YYYY-MM-DD'),
    limite: int = Query(100, ge=1, le=500),
):
    """Consulta de facturas por número, cliente, estado o rango de fechas."""
    filtros = ['1 = 1']
    parametros: list[Any] = []

    if numero:
        filtros.append('f.numero LIKE ?')
        parametros.append(f'%{numero}%')
    if cliente:
        filtros.append('(f.cliente_nombre LIKE ? OR f.cliente_documento LIKE ?)')
        parametros.extend([f'%{cliente}%', f'%{cliente}%'])
    if estado:
        filtros.append('f.estado = ?')
        parametros.append(estado)
    desde = parse_date(fechaInicio)
    hasta = parse_date(fechaFin, end_of_day=True)
    if desde:
        filtros.append('f.fecha >= ?')
        parametros.append(desde)
    if hasta:
        filtros.append('f.fecha <= ?')
        parametros.append(hasta)
    if current_user.get('role') == 'Cliente':
        filtros.append('(v.cliente_id = ? OR f.cliente_documento = ?)')
        parametros.extend([current_user.get('id'), current_user.get('document_number', '')])

    conn = get_db_connection()
    try:
        rows = conn.execute(
            f'''
            SELECT f.*, v.numero AS venta_numero
            FROM facturas f
            JOIN ventas v ON v.id = f.venta_id
            WHERE {" AND ".join(filtros)}
            ORDER BY f.fecha DESC, f.id DESC
            LIMIT ?
            ''',
            (*parametros, limite),
        ).fetchall()
        return {'facturas': [factura_row(row) for row in rows]}
    finally:
        conn.close()


@router.get('/{factura_id}')
def obtener_factura(factura_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        factura = _factura_con_venta(conn, factura_id)
        if factura is None:
            raise HTTPException(status_code=404, detail='La factura no existe.')
        venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (factura['venta_id'],)).fetchone()
        if current_user.get('role') == 'Cliente' and venta['cliente_id'] != current_user.get('id'):
            raise HTTPException(status_code=403, detail='No tienes permisos para consultar esta factura.')
        return {
            'factura': {**factura_row(factura), 'detalle': _detalle_factura(conn, factura_id)},
            'venta': venta_row(venta),
        }
    finally:
        conn.close()


@router.get('/{factura_id}/pdf')
def descargar_factura(factura_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    """Descarga la factura en PDF."""
    conn = get_db_connection()
    try:
        factura = _factura_con_venta(conn, factura_id)
        if factura is None:
            raise HTTPException(status_code=404, detail='La factura no existe.')
        venta = conn.execute('SELECT * FROM ventas WHERE id = ?', (factura['venta_id'],)).fetchone()
        if current_user.get('role') == 'Cliente' and venta['cliente_id'] != current_user.get('id'):
            raise HTTPException(status_code=403, detail='No tienes permisos para descargar esta factura.')
        datos = factura_row(factura)
        contenido = construir_factura_pdf(datos, _detalle_factura(conn, factura_id), venta_row(venta))
    finally:
        conn.close()

    return Response(
        content=contenido,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="factura-{datos["numero"]}.pdf"'},
    )


@router.patch('/{factura_id}/estado', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def cambiar_estado_factura(factura_id: int, payload: FacturaEstado):
    if payload.estado not in ESTADOS_FACTURA:
        raise HTTPException(status_code=400, detail=f'Estado inválido. Use uno de: {", ".join(ESTADOS_FACTURA)}.')
    conn = get_db_connection()
    try:
        if conn.execute('SELECT id FROM facturas WHERE id = ?', (factura_id,)).fetchone() is None:
            raise HTTPException(status_code=404, detail='La factura no existe.')
        conn.execute('UPDATE facturas SET estado = ? WHERE id = ?', (payload.estado, factura_id))
        conn.commit()
        return {'message': 'Estado de la factura actualizado.', 'estado': payload.estado}
    finally:
        conn.close()
