"""Esquema y utilidades del módulo comercial del quinto avance.

Agrega a la base de datos las tablas ``ventas``, ``detalle_ventas``,
``facturas``, ``detalle_facturas``, ``pagos``, ``pqr``, ``conversaciones`` y
``mensajes``,
junto con los ayudantes de numeración y cálculo que comparten los endpoints.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Any, Optional

ESTADOS_VENTA = ('Registrada', 'Pagada', 'Anulada')
ESTADOS_FACTURA = ('Emitida', 'Pagada', 'Anulada')
ESTADOS_PAGO = ('Pendiente', 'Aprobado', 'Rechazado', 'Error')
ESTADOS_PQR = ('Pendiente', 'En proceso', 'Respondida', 'Cerrada')
TIPOS_PQR = ('Petición', 'Queja', 'Reclamo', 'Sugerencia')
TIPOS_ITEM = ('producto', 'servicio')

COMERCIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    cliente_id INTEGER,
    cliente_nombre TEXT NOT NULL,
    cliente_documento TEXT NOT NULL DEFAULT '',
    usuario_id INTEGER,
    usuario_nombre TEXT NOT NULL DEFAULT '',
    subtotal REAL NOT NULL DEFAULT 0,
    descuento REAL NOT NULL DEFAULT 0,
    impuestos REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    estado TEXT NOT NULL DEFAULT 'Registrada',
    observaciones TEXT NOT NULL DEFAULT '',
    fecha TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    item_tipo TEXT NOT NULL,
    item_id INTEGER,
    -- Una línea es de un producto o de un servicio, nunca de los dos: la que no
    -- corresponde queda en NULL. Son las que enlazan la venta con el catálogo.
    producto_id INTEGER,
    servicio_id INTEGER,
    nombre TEXT NOT NULL,
    cantidad REAL NOT NULL DEFAULT 1,
    precio_unitario REAL NOT NULL DEFAULT 0,
    descuento REAL NOT NULL DEFAULT 0,
    impuesto REAL NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL,
    FOREIGN KEY (servicio_id) REFERENCES servicios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    venta_id INTEGER NOT NULL UNIQUE,
    cliente_nombre TEXT NOT NULL,
    cliente_documento TEXT NOT NULL DEFAULT '',
    subtotal REAL NOT NULL DEFAULT 0,
    descuento REAL NOT NULL DEFAULT 0,
    impuestos REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    estado TEXT NOT NULL DEFAULT 'Emitida',
    fecha TEXT NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS detalle_facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    item_tipo TEXT NOT NULL,
    producto_id INTEGER,
    servicio_id INTEGER,
    nombre TEXT NOT NULL,
    cantidad REAL NOT NULL DEFAULT 1,
    precio_unitario REAL NOT NULL DEFAULT 0,
    descuento REAL NOT NULL DEFAULT 0,
    impuesto REAL NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL,
    FOREIGN KEY (servicio_id) REFERENCES servicios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referencia TEXT NOT NULL UNIQUE,
    venta_id INTEGER NOT NULL,
    factura_id INTEGER,
    cliente_id INTEGER,
    cliente_nombre TEXT NOT NULL DEFAULT '',
    metodo TEXT NOT NULL DEFAULT 'tarjeta',
    entidad TEXT NOT NULL DEFAULT '',
    ultimos_digitos TEXT NOT NULL DEFAULT '',
    cuotas INTEGER NOT NULL DEFAULT 1,
    monto REAL NOT NULL DEFAULT 0,
    moneda TEXT NOT NULL DEFAULT 'COP',
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    motivo TEXT NOT NULL DEFAULT '',
    transaccion TEXT NOT NULL DEFAULT '',
    fecha TEXT NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE SET NULL,
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pqr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    radicado TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL DEFAULT 'Petición',
    asunto TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Pendiente',
    respuesta TEXT NOT NULL DEFAULT '',
    cliente_id INTEGER,
    cliente_nombre TEXT NOT NULL,
    cliente_email TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS conversaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    titulo TEXT NOT NULL DEFAULT 'Conversación',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversacion_id INTEGER NOT NULL,
    rol TEXT NOT NULL,
    contenido TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
CREATE INDEX IF NOT EXISTS idx_detalle_ventas_venta ON detalle_ventas(venta_id);
CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha);
CREATE INDEX IF NOT EXISTS idx_pagos_venta ON pagos(venta_id);
CREATE INDEX IF NOT EXISTS idx_pqr_estado ON pqr(estado);
CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion ON mensajes(conversacion_id);
"""


def money(value: Any) -> float:
    """Redondea a dos decimales para que los totales no arrastren flotantes."""
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=' ')


def next_number(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    """Genera un consecutivo legible del tipo ``VT-000007``."""
    row = conn.execute(f'SELECT COUNT(*) AS total FROM {table}').fetchone()
    return f'{prefix}-{(row["total"] or 0) + 1:06d}'


def parse_date(value: Optional[str], end_of_day: bool = False) -> Optional[str]:
    """Normaliza ``YYYY-MM-DD`` a un límite comparable con ``fecha``."""
    if not value:
        return None
    try:
        day = datetime.strptime(value[:10], '%Y-%m-%d')
    except ValueError:
        return None
    return f'{day.date().isoformat()} 23:59:59' if end_of_day else f'{day.date().isoformat()} 00:00:00'


def la_venta_es_del_cliente(venta, usuario: dict[str, Any]) -> bool:
    """¿Esta venta le pertenece al Cliente que está consultando?

    El historial empareja por ``cliente_id`` **o** por documento, porque una
    venta registrada en el mostrador no tiene cuenta asociada y el comprador
    puede crearse la cuenta después; el documento es único por persona. El
    detalle y la factura tienen que usar la misma regla: si no, la venta sale
    en "Mis compras" pero abrirla responde 403.
    """
    datos = dict(venta)
    if datos.get('cliente_id') is not None and datos.get('cliente_id') == usuario.get('id'):
        return True
    documento = (usuario.get('document_number') or '').strip()
    return bool(documento) and (datos.get('cliente_documento') or '').strip() == documento


def venta_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    return {
        'id': data['id'],
        'numero': data['numero'],
        'clienteId': data.get('cliente_id'),
        'cliente': data['cliente_nombre'],
        'clienteDocumento': data.get('cliente_documento', ''),
        'usuario': data.get('usuario_nombre', ''),
        'subtotal': money(data.get('subtotal')),
        'descuento': money(data.get('descuento')),
        'impuestos': money(data.get('impuestos')),
        'total': money(data.get('total')),
        'estado': data['estado'],
        'observaciones': data.get('observaciones', ''),
        'fecha': data['fecha'],
    }


def pago_row(row: sqlite3.Row) -> dict[str, Any]:
    """Un pago tal como lo lee el sitio.

    Nunca sale de aquí el número de la tarjeta: en la tabla solo están los
    cuatro últimos dígitos y la entidad (la franquicia de la tarjeta, el banco
    del débito o el punto de pago en efectivo), que es lo que lleva un recibo.
    """
    data = dict(row)
    return {
        'id': data['id'],
        'referencia': data['referencia'],
        'ventaId': data['venta_id'],
        'facturaId': data.get('factura_id'),
        'clienteId': data.get('cliente_id'),
        'cliente': data.get('cliente_nombre', ''),
        'metodo': data.get('metodo', ''),
        'entidad': data.get('entidad', ''),
        'ultimosDigitos': data.get('ultimos_digitos', ''),
        'cuotas': int(data.get('cuotas') or 1),
        'monto': money(data.get('monto')),
        'moneda': data.get('moneda', 'COP'),
        'estado': data['estado'],
        'motivo': data.get('motivo', ''),
        'transaccion': data.get('transaccion', ''),
        'fecha': data['fecha'],
    }


def detalle_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    return {
        'id': data['id'],
        'tipo': data['item_tipo'],
        'itemId': data.get('item_id'),
        'nombre': data['nombre'],
        'cantidad': money(data.get('cantidad')),
        'precioUnitario': money(data.get('precio_unitario')),
        'descuento': money(data.get('descuento')),
        'impuesto': money(data.get('impuesto')),
        'subtotal': money(data.get('subtotal')),
        'total': money(data.get('total')),
    }


def factura_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    return {
        'id': data['id'],
        'numero': data['numero'],
        'ventaId': data['venta_id'],
        'ventaNumero': data.get('venta_numero'),
        'cliente': data['cliente_nombre'],
        'clienteDocumento': data.get('cliente_documento', ''),
        'subtotal': money(data.get('subtotal')),
        'descuento': money(data.get('descuento')),
        'impuestos': money(data.get('impuestos')),
        'total': money(data.get('total')),
        'estado': data['estado'],
        'fecha': data['fecha'],
    }


def pqr_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    return {
        'id': data['id'],
        'radicado': data['radicado'],
        'tipo': data['tipo'],
        'asunto': data['asunto'],
        'descripcion': data['descripcion'],
        'estado': data['estado'],
        'respuesta': data.get('respuesta', ''),
        'clienteId': data.get('cliente_id'),
        'cliente': data['cliente_nombre'],
        'clienteEmail': data.get('cliente_email', ''),
        'creado': data['created_at'],
        'actualizado': data['updated_at'],
    }


def init_comercial_db(conn, crear_tablas: bool = True) -> None:
    """Crea las tablas del quinto avance y siembra datos de demostración.

    En MySQL las tablas ya vienen de ``backend/schema.sql``, así que solo se
    siembra (``crear_tablas=False``).
    """
    if crear_tablas:
        _rehacer_pagos_si_es_del_dia_anterior(conn)
        conn.executescript(COMERCIAL_SCHEMA)
    # Va también en MySQL: allí las tablas ya existen y ``CREATE TABLE IF NOT
    # EXISTS`` no les agrega nada.
    _enlazar_detalle_con_el_catalogo(conn)
    _seed_demo(conn)
    conn.commit()


def _columnas(conn, tabla: str) -> set[str]:
    """Nombres de las columnas de una tabla, o vacío si no existe."""
    try:
        cursor = conn.execute(f'SELECT * FROM {tabla} LIMIT 0')
    except Exception:
        return set()
    columnas = {descripcion[0] for descripcion in cursor.description or ()}
    # El conector de MySQL se cae si queda una consulta a medio leer.
    cursor.fetchall()
    return columnas


# Cada línea del detalle apunta al catálogo por estas dos columnas. Una línea
# llena la que le toca y deja la otra en NULL.
ENLACES_AL_CATALOGO = (('producto_id', 'productos'), ('servicio_id', 'servicios'))

DETALLES = ('detalle_ventas', 'detalle_facturas')


def _enlazar_detalle_con_el_catalogo(conn) -> None:
    """Agrega ``producto_id`` y ``servicio_id`` al detalle si no los tiene.

    Antes, el detalle decía qué se vendió con ``item_tipo`` + ``item_id``, que
    apuntan a dos tablas distintas según el tipo. Eso no puede ser una clave
    foránea, y por eso ``productos`` y ``servicios`` salían sueltos en el
    Diseñador de phpMyAdmin: la relación existía en el código pero no en la
    base de datos. Con una columna por tabla sí es una relación de verdad.

    En una base que ya tiene datos, las columnas se agregan y se rellenan a
    partir de lo que ya estaba guardado, sin borrar nada.
    """
    for tabla in DETALLES:
        columnas = _columnas(conn, tabla)
        if not columnas:
            continue
        for columna, catalogo in ENLACES_AL_CATALOGO:
            if columna in columnas:
                continue
            # INTEGER y nulable por defecto: lo entienden igual SQLite y MySQL.
            conn.execute(f'ALTER TABLE {tabla} ADD COLUMN {columna} INTEGER')
            try:
                conn.execute(
                    f'ALTER TABLE {tabla} ADD CONSTRAINT fk_{tabla}_{columna} '
                    f'FOREIGN KEY ({columna}) REFERENCES {catalogo} (id) ON DELETE SET NULL'
                )
            except Exception:
                # SQLite no sabe agregar una restricción a una tabla que ya
                # existe. No importa: la base nueva sí la trae, y es MySQL
                # quien tiene que dibujarla en el Diseñador.
                pass
            _rellenar_enlace(conn, tabla, columna, catalogo)
    conn.commit()


def _rellenar_enlace(conn, tabla: str, columna: str, catalogo: str) -> None:
    """Deduce a qué artículo apuntaba cada línea que ya estaba guardada."""
    tipo = 'producto' if columna == 'producto_id' else 'servicio'
    if 'item_id' in _columnas(conn, tabla):
        # En las ventas el id exacto ya estaba guardado.
        conn.execute(
            f'UPDATE {tabla} SET {columna} = item_id '
            f"WHERE item_tipo = '{tipo}' AND item_id IN (SELECT id FROM {catalogo})"
        )
        return
    # En las facturas no, así que se busca por el nombre que quedó copiado. El
    # que no aparezca se queda en NULL, que es la verdad: ya no está.
    conn.execute(
        f'UPDATE {tabla} SET {columna} = '
        f'(SELECT MIN(c.id) FROM {catalogo} c WHERE c.name = {tabla}.nombre) '
        f"WHERE item_tipo = '{tipo}'"
    )


def _rehacer_pagos_si_es_del_dia_anterior(conn) -> None:
    """Rehace ``pagos`` si quedó con las columnas de la primera versión.

    La tabla nació el 2026-09-29 con ``pasarela`` y ``franquicia``, pensada para
    saltar a una pasarela externa. Ese mismo día se cambió por un formulario
    dentro del sitio, con ``metodo`` y ``entidad``. ``CREATE TABLE IF NOT
    EXISTS`` no corrige una tabla que ya existe, así que la vieja se rehace:
    solo pudo tener cobros de prueba de ese día.
    """
    columnas = _columnas(conn, 'pagos')
    if 'entidad' not in columnas and 'pasarela' in columnas:
        conn.execute('DROP TABLE pagos')
        conn.commit()


def _seed_demo(conn: sqlite3.Connection) -> None:
    """Deja unas ventas, facturas y PQR de ejemplo la primera vez.

    Los dashboards leen siempre de la base de datos, así que sin datos los
    gráficos saldrían vacíos en una instalación nueva.
    """
    if conn.execute('SELECT COUNT(*) AS total FROM ventas').fetchone()['total'] > 0:
        return

    productos = conn.execute('SELECT id, name, price FROM productos WHERE active = 1').fetchall()
    servicios = conn.execute('SELECT id, name, price FROM servicios WHERE active = 1').fetchall()
    if not productos and not servicios:
        return

    catalogo = [('producto', row) for row in productos] + [('servicio', row) for row in servicios]
    clientes = [
        ('Laura Gómez', '1024567890'),
        ('Carlos Peña', '1098765432'),
        ('Marcela Ríos', '1032145678'),
    ]
    vendedor = conn.execute(
        "SELECT u.id, u.name, u.last_name FROM usuarios u JOIN roles r ON r.id = u.role_id WHERE r.name = 'Administrador' LIMIT 1"
    ).fetchone()
    vendedor_id = vendedor['id'] if vendedor else None
    vendedor_nombre = f"{vendedor['name']} {vendedor['last_name']}" if vendedor else 'Sistema'

    hoy = datetime.now().replace(hour=10, minute=30, second=0, microsecond=0)
    for indice in range(9):
        fecha = hoy - timedelta(days=indice % 5, hours=indice)
        cliente_nombre, cliente_documento = clientes[indice % len(clientes)]
        lineas = [catalogo[(indice + paso) % len(catalogo)] for paso in range(1 + indice % 2)]

        subtotal = descuento_total = impuesto_total = 0.0
        detalle = []
        for tipo, item in lineas:
            cantidad = 1 + (indice % 3)
            precio = money(item['price'])
            bruto = money(precio * cantidad)
            descuento = money(bruto * 0.05) if indice % 3 == 0 else 0.0
            base = money(bruto - descuento)
            impuesto = money(base * 0.19)
            subtotal += base
            descuento_total += descuento
            impuesto_total += impuesto
            producto_id = item['id'] if tipo == 'producto' else None
            servicio_id = item['id'] if tipo == 'servicio' else None
            detalle.append((tipo, item['id'], producto_id, servicio_id, item['name'], cantidad,
                            precio, descuento, impuesto, base, money(base + impuesto)))

        total = money(subtotal + impuesto_total)
        numero = next_number(conn, 'ventas', 'VT')
        estado = 'Pagada' if indice % 4 else 'Registrada'
        cursor = conn.execute(
            '''
            INSERT INTO ventas (numero, cliente_id, cliente_nombre, cliente_documento, usuario_id, usuario_nombre,
                                subtotal, descuento, impuestos, total, estado, observaciones, fecha)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (numero, None, cliente_nombre, cliente_documento, vendedor_id, vendedor_nombre,
             money(subtotal), money(descuento_total), money(impuesto_total), total, estado,
             'Venta de demostración', fecha.isoformat(sep=' ')),
        )
        venta_id = cursor.lastrowid
        for linea in detalle:
            conn.execute(
                '''
                INSERT INTO detalle_ventas (venta_id, item_tipo, item_id, producto_id, servicio_id, nombre,
                                            cantidad, precio_unitario, descuento, impuesto, subtotal, total)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ''',
                (venta_id, *linea),
            )

        if estado == 'Pagada':
            factura_numero = next_number(conn, 'facturas', 'FV')
            factura_cursor = conn.execute(
                '''
                INSERT INTO facturas (numero, venta_id, cliente_nombre, cliente_documento, subtotal, descuento,
                                      impuestos, total, estado, fecha)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ''',
                (factura_numero, venta_id, cliente_nombre, cliente_documento, money(subtotal),
                 money(descuento_total), money(impuesto_total), total, 'Emitida', fecha.isoformat(sep=' ')),
            )
            factura_id = factura_cursor.lastrowid
            for (tipo, _item_id, producto_id, servicio_id, nombre, cantidad,
                 precio, descuento, impuesto, base, linea_total) in detalle:
                conn.execute(
                    '''
                    INSERT INTO detalle_facturas (factura_id, item_tipo, producto_id, servicio_id, nombre,
                                                  cantidad, precio_unitario, descuento, impuesto, subtotal, total)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    ''',
                    (factura_id, tipo, producto_id, servicio_id, nombre, cantidad, precio,
                     descuento, impuesto, base, linea_total),
                )

    demo_pqr = [
        ('Queja', 'Demora en la entrega', 'El pedido llegó dos días después de lo acordado.', 'Pendiente'),
        ('Petición', 'Cotización de branding', 'Solicito una cotización para identidad visual completa.', 'En proceso'),
        ('Reclamo', 'Cobro duplicado', 'Aparecen dos cobros por el mismo servicio.', 'Respondida'),
    ]
    for indice, (tipo, asunto, descripcion, estado) in enumerate(demo_pqr):
        cliente_nombre, _documento = clientes[indice % len(clientes)]
        momento = (hoy - timedelta(days=indice)).isoformat(sep=' ')
        conn.execute(
            '''
            INSERT INTO pqr (radicado, tipo, asunto, descripcion, estado, respuesta, cliente_id, cliente_nombre,
                             cliente_email, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (next_number(conn, 'pqr', 'PQR'), tipo, asunto, descripcion, estado,
             'Estamos revisando el caso con el área contable.' if estado == 'Respondida' else '',
             None, cliente_nombre, '', momento, momento),
        )
