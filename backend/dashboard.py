"""Dashboards: indicadores tipo Card y series para los gráficos.

Todo se calcula con consultas a la base de datos, de forma que el Frontend
nunca tenga información escrita a mano.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

try:
    from .core import get_current_user, get_db_connection, require_roles, usa_mysql
    from .comercial import ESTADOS_PQR, ESTADOS_VENTA, money, parse_date
except ImportError:
    from core import get_current_user, get_db_connection, require_roles, usa_mysql
    from comercial import ESTADOS_PQR, ESTADOS_VENTA, money, parse_date

# El dashboard es solo del Administrador: ni el Empleado ni el Cliente lo ven.
# Se cierra aquí y no solo en el menú del panel, porque esconder un botón no
# impide pedir la ruta a mano.
router = APIRouter(
    prefix='/api/dashboard',
    tags=['dashboard'],
    dependencies=[Depends(require_roles('Administrador'))],
)

# Agrupar por periodo es lo único que cambia de verdad entre los dos motores.
# Las variantes de MySQL evitan el '%' a propósito: la consulta lleva
# parámetros y ese símbolo se confundiría con un marcador de posición.
AGRUPACIONES_SQLITE = {
    'dia': "strftime('%Y-%m-%d', v.fecha)",
    'semana': "strftime('%Y-S%W', v.fecha)",
    'mes': "strftime('%Y-%m', v.fecha)",
}

AGRUPACIONES_MYSQL = {
    'dia': 'DATE(v.fecha)',
    'semana': "CONCAT(YEAR(v.fecha), '-S', LPAD(WEEK(v.fecha), 2, '0'))",
    'mes': "CONCAT(YEAR(v.fecha), '-', LPAD(MONTH(v.fecha), 2, '0'))",
}


def agrupaciones() -> dict[str, str]:
    return AGRUPACIONES_MYSQL if usa_mysql() else AGRUPACIONES_SQLITE


def _filtros_ventas(
    fechaInicio: Optional[str],
    fechaFin: Optional[str],
    estado: Optional[str],
    cliente: Optional[str],
    producto: Optional[str],
    servicio: Optional[str],
    usuario: dict[str, Any],
) -> tuple[list[str], list[Any]]:
    filtros: list[str] = []
    parametros: list[Any] = []

    if estado:
        filtros.append('v.estado = ?')
        parametros.append(estado)
    else:
        filtros.append("v.estado <> 'Anulada'")

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
    for tipo, termino in (('producto', producto), ('servicio', servicio)):
        if termino:
            filtros.append(
                'EXISTS (SELECT 1 FROM detalle_ventas d WHERE d.venta_id = v.id AND d.item_tipo = ? AND d.nombre LIKE ?)'
            )
            parametros.extend([tipo, f'%{termino}%'])
    if usuario.get('role') == 'Cliente':
        filtros.append('(v.cliente_id = ? OR v.cliente_documento = ?)')
        parametros.extend([usuario.get('id'), usuario.get('document_number', '')])

    return filtros, parametros


@router.get('/filtros')
def opciones_de_filtro(_usuario: dict[str, Any] = Depends(get_current_user)):
    """Valores disponibles para armar los selectores de los dashboards."""
    conn = get_db_connection()
    try:
        productos = [row['name'] for row in conn.execute('SELECT DISTINCT name FROM productos ORDER BY name').fetchall()]
        servicios = [row['name'] for row in conn.execute('SELECT DISTINCT name FROM servicios ORDER BY name').fetchall()]
        clientes = [
            row['cliente_nombre']
            for row in conn.execute('SELECT DISTINCT cliente_nombre FROM ventas ORDER BY cliente_nombre').fetchall()
        ]
        return {
            'productos': productos,
            'servicios': servicios,
            'clientes': clientes,
            'estadosVenta': list(ESTADOS_VENTA),
            'estadosPqr': list(ESTADOS_PQR),
        }
    finally:
        conn.close()


@router.get('/resumen')
def resumen(usuario: dict[str, Any] = Depends(get_current_user)):
    """Indicadores tipo Card, recortados según el rol de quien consulta."""
    rol = usuario.get('role')
    conn = get_db_connection()
    try:
        def escalar(consulta: str, parametros: tuple = ()) -> float:
            fila = conn.execute(consulta, parametros).fetchone()
            return money(fila[0] if fila and fila[0] is not None else 0)

        propias = ''
        parametros_propios: tuple = ()
        if rol == 'Cliente':
            propias = ' AND (cliente_id = ? OR cliente_documento = ?)'
            parametros_propios = (usuario.get('id'), usuario.get('document_number', ''))

        tarjetas = [
            {
                'clave': 'ventas',
                'titulo': 'Ventas registradas',
                'valor': escalar(f"SELECT COUNT(*) FROM ventas WHERE estado <> 'Anulada'{propias}", parametros_propios),
                'formato': 'numero',
            },
            {
                'clave': 'facturacion',
                'titulo': 'Total facturado',
                'valor': escalar(
                    f"SELECT SUM(total) FROM ventas WHERE estado <> 'Anulada'{propias}", parametros_propios
                ),
                'formato': 'moneda',
            },
            {
                'clave': 'facturas',
                'titulo': 'Facturas emitidas',
                'valor': escalar(
                    'SELECT COUNT(*) FROM facturas f JOIN ventas v ON v.id = f.venta_id'
                    + (' WHERE v.cliente_id = ? OR v.cliente_documento = ?' if rol == 'Cliente' else ''),
                    parametros_propios if rol == 'Cliente' else (),
                ),
                'formato': 'numero',
            },
            {
                'clave': 'pqrPendientes',
                'titulo': 'PQR pendientes',
                'valor': escalar(
                    "SELECT COUNT(*) FROM pqr WHERE estado IN ('Pendiente', 'En proceso')"
                    + (' AND cliente_id = ?' if rol == 'Cliente' else ''),
                    (usuario.get('id'),) if rol == 'Cliente' else (),
                ),
                'formato': 'numero',
            },
        ]

        if rol in ('Administrador', 'Empleado'):
            tarjetas.extend([
                {'clave': 'productos', 'titulo': 'Productos activos',
                 'valor': escalar('SELECT COUNT(*) FROM productos WHERE active = 1'), 'formato': 'numero'},
                {'clave': 'servicios', 'titulo': 'Servicios activos',
                 'valor': escalar('SELECT COUNT(*) FROM servicios WHERE active = 1'), 'formato': 'numero'},
            ])
        if rol == 'Administrador':
            tarjetas.append({
                'clave': 'usuarios', 'titulo': 'Usuarios registrados',
                'valor': escalar('SELECT COUNT(*) FROM usuarios'), 'formato': 'numero',
            })

        # El cliente solo cuenta sus propias solicitudes, no las de los demás.
        filtro_pqr = ' AND cliente_id = ?' if rol == 'Cliente' else ''
        pqr_por_estado = [
            {
                'etiqueta': estado,
                'valor': escalar(
                    f'SELECT COUNT(*) FROM pqr WHERE estado = ?{filtro_pqr}',
                    (estado, usuario.get('id')) if rol == 'Cliente' else (estado,),
                ),
            }
            for estado in ESTADOS_PQR
        ]

        return {'rol': rol, 'tarjetas': tarjetas, 'pqrPorEstado': pqr_por_estado}
    finally:
        conn.close()


@router.get('/ventas')
def dashboard_ventas(
    usuario: dict[str, Any] = Depends(get_current_user),
    agrupacion: str = Query('dia', description='dia, semana o mes'),
    fechaInicio: Optional[str] = None,
    fechaFin: Optional[str] = None,
    estado: Optional[str] = None,
    cliente: Optional[str] = None,
    producto: Optional[str] = None,
    servicio: Optional[str] = None,
    limite: int = Query(12, ge=3, le=60),
):
    """Series para el gráfico de barras (montos) y el lineal (número de ventas)."""
    periodos = agrupaciones()
    if agrupacion not in periodos:
        raise HTTPException(status_code=400, detail='La agrupación debe ser dia, semana o mes.')

    filtros, parametros = _filtros_ventas(fechaInicio, fechaFin, estado, cliente, producto, servicio, usuario)
    where = ' AND '.join(filtros)
    periodo = periodos[agrupacion]

    conn = get_db_connection()
    try:
        series = conn.execute(
            f'''
            SELECT {periodo} AS periodo, COUNT(*) AS cantidad, SUM(v.total) AS total
            FROM ventas v
            WHERE {where}
            GROUP BY periodo
            ORDER BY periodo DESC
            LIMIT ?
            ''',
            (*parametros, limite),
        ).fetchall()

        top_items = conn.execute(
            f'''
            SELECT d.nombre, d.item_tipo, SUM(d.cantidad) AS unidades, SUM(d.total) AS total
            FROM detalle_ventas d
            JOIN ventas v ON v.id = d.venta_id
            WHERE {where}
            GROUP BY d.nombre, d.item_tipo
            ORDER BY total DESC
            LIMIT 5
            ''',
            tuple(parametros),
        ).fetchall()

        por_estado = conn.execute(
            f'SELECT v.estado, COUNT(*) AS cantidad FROM ventas v WHERE {where} GROUP BY v.estado',
            tuple(parametros),
        ).fetchall()

        puntos = [
            {'etiqueta': fila['periodo'], 'total': money(fila['total']), 'cantidad': int(fila['cantidad'] or 0)}
            for fila in reversed(series)
        ]

        return {
            'agrupacion': agrupacion,
            'barras': [{'etiqueta': punto['etiqueta'], 'valor': punto['total']} for punto in puntos],
            'lineal': [{'etiqueta': punto['etiqueta'], 'valor': punto['cantidad']} for punto in puntos],
            'topItems': [
                {
                    'nombre': fila['nombre'],
                    'tipo': fila['item_tipo'],
                    'unidades': money(fila['unidades']),
                    'total': money(fila['total']),
                }
                for fila in top_items
            ],
            'porEstado': [{'etiqueta': fila['estado'], 'valor': int(fila['cantidad'] or 0)} for fila in por_estado],
            'totales': {
                'ventas': sum(punto['cantidad'] for punto in puntos),
                'monto': money(sum(punto['total'] for punto in puntos)),
            },
        }
    finally:
        conn.close()
