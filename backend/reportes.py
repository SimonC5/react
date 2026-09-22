"""Reporte diario de ventas y sus exportaciones en PDF y Excel."""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

try:
    from .core import get_db_connection, require_roles
    from .comercial import money, parse_date
    from .documentos import construir_pdf, construir_xlsx, formato_moneda
except ImportError:
    from core import get_db_connection, require_roles
    from comercial import money, parse_date
    from documentos import construir_pdf, construir_xlsx, formato_moneda

router = APIRouter(prefix='/api/reportes', tags=['reportes'])

ENCABEZADOS = ['Venta', 'Fecha', 'Cliente', 'Productos y/o servicios', 'Cantidad', 'Valor', 'Estado']


def _reporte_diario(fecha: Optional[str]) -> dict[str, Any]:
    """Arma el reporte de un día: ventas, líneas agregadas y totales."""
    dia = (fecha or date.today().isoformat())[:10]
    desde = parse_date(dia) or f'{date.today().isoformat()} 00:00:00'
    hasta = parse_date(dia, end_of_day=True) or f'{date.today().isoformat()} 23:59:59'

    conn = get_db_connection()
    try:
        ventas = conn.execute(
            'SELECT * FROM ventas WHERE fecha >= ? AND fecha <= ? ORDER BY fecha, id',
            (desde, hasta),
        ).fetchall()

        filas = []
        total_general = subtotal_general = impuestos_generales = descuentos_generales = 0.0
        unidades = 0.0

        for venta in ventas:
            lineas = conn.execute(
                'SELECT nombre, item_tipo, cantidad FROM detalle_ventas WHERE venta_id = ? ORDER BY id',
                (venta['id'],),
            ).fetchall()
            descripcion = ', '.join(f"{linea['nombre']} ({linea['item_tipo']})" for linea in lineas) or 'Sin detalle'
            cantidad = sum(float(linea['cantidad'] or 0) for linea in lineas)
            unidades += cantidad
            subtotal_general += money(venta['subtotal'])
            descuentos_generales += money(venta['descuento'])
            impuestos_generales += money(venta['impuestos'])
            if venta['estado'] != 'Anulada':
                total_general += money(venta['total'])
            filas.append({
                'numero': venta['numero'],
                'fecha': venta['fecha'],
                'cliente': venta['cliente_nombre'],
                'descripcion': descripcion,
                'cantidad': cantidad,
                'total': money(venta['total']),
                'estado': venta['estado'],
            })

        return {
            'fecha': dia,
            'generadoEn': f'{date.today().isoformat()}',
            'filas': filas,
            'totales': {
                'ventas': len(filas),
                'unidades': money(unidades),
                'subtotal': money(subtotal_general),
                'descuentos': money(descuentos_generales),
                'impuestos': money(impuestos_generales),
                'total': money(total_general),
            },
        }
    finally:
        conn.close()


def _filas_planas(reporte: dict[str, Any]) -> list[list[Any]]:
    return [
        [fila['numero'], fila['fecha'], fila['cliente'], fila['descripcion'], fila['cantidad'], fila['total'], fila['estado']]
        for fila in reporte['filas']
    ]


@router.get('/ventas/diario', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def reporte_diario(fecha: Optional[str] = Query(None, description='YYYY-MM-DD, por defecto hoy')):
    """Reporte diario de ventas en JSON, para mostrarlo en pantalla."""
    return {'reporte': _reporte_diario(fecha)}


@router.get('/ventas/diario.pdf', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def reporte_diario_pdf(fecha: Optional[str] = Query(None, description='YYYY-MM-DD, por defecto hoy')):
    """Exporta el reporte diario en PDF."""
    reporte = _reporte_diario(fecha)
    totales = reporte['totales']
    contenido = construir_pdf(
        'Reporte diario de ventas',
        f"Fecha del reporte: {reporte['fecha']} · Generado el {reporte['generadoEn']} · Identificación: SimonC Realidad Virtual",
        ENCABEZADOS,
        [[fila[0], fila[1], fila[2], fila[3], f'{fila[4]:g}', formato_moneda(fila[5]), fila[6]] for fila in _filas_planas(reporte)],
        [
            ('Ventas registradas', str(totales['ventas'])),
            ('Unidades vendidas', f"{totales['unidades']:g}"),
            ('Subtotal', formato_moneda(totales['subtotal'])),
            ('Descuentos', formato_moneda(totales['descuentos'])),
            ('Impuestos', formato_moneda(totales['impuestos'])),
            ('Total del día', formato_moneda(totales['total'])),
        ],
    )
    return Response(
        content=contenido,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="reporte-ventas-{reporte["fecha"]}.pdf"'},
    )


@router.get('/ventas/diario.xlsx', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def reporte_diario_excel(fecha: Optional[str] = Query(None, description='YYYY-MM-DD, por defecto hoy')):
    """Exporta el mismo reporte diario en Excel para analizarlo o filtrarlo."""
    reporte = _reporte_diario(fecha)
    totales = reporte['totales']
    contenido = construir_xlsx(
        'Reporte diario de ventas',
        f"Fecha del reporte: {reporte['fecha']} · Generado el {reporte['generadoEn']}",
        ENCABEZADOS,
        _filas_planas(reporte),
        [
            ('Ventas registradas', totales['ventas']),
            ('Unidades vendidas', totales['unidades']),
            ('Subtotal', totales['subtotal']),
            ('Descuentos', totales['descuentos']),
            ('Impuestos', totales['impuestos']),
            ('Total del día', totales['total']),
        ],
    )
    return Response(
        content=contenido,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="reporte-ventas-{reporte["fecha"]}.xlsx"'},
    )
