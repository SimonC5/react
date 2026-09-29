"""Modelos ORM (SQLAlchemy 2.0) de todas las entidades del proyecto.

Están escritos con el estilo tipado de SQLAlchemy 2.0: cada columna se declara
como ``Mapped[tipo]`` con ``mapped_column(...)``, de modo que el tipo de Python
queda a la vista y lo comprueban los analizadores estáticos. ``Optional[...]``
marca las columnas que aceptan NULL.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa 2.0: de ella cuelgan el metadata y todos los modelos."""


role_permissions = Table(
    'role_permisos',
    Base.metadata,
    Column('role_id', ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permiso_id', ForeignKey('permisos.id', ondelete='CASCADE'), primary_key=True),
)


class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    users: Mapped[list['User']] = relationship('User', back_populates='role')
    permissions: Mapped[list['Permission']] = relationship('Permission', secondary=role_permissions, back_populates='roles')


class Permission(Base):
    __tablename__ = 'permisos'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    roles: Mapped[list['Role']] = relationship('Role', secondary=role_permissions, back_populates='permissions')


class User(Base):
    __tablename__ = 'usuarios'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)
    document_number: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id'), nullable=False)
    role: Mapped['Role'] = relationship('Role', back_populates='users')
    pagos: Mapped[list['Pago']] = relationship('Pago', back_populates='cliente')


class Product(Base):
    __tablename__ = 'productos'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Service(Base):
    __tablename__ = 'servicios'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# --- Entidades comerciales y de IA del quinto avance -------------------------
#
# El runtime consulta la base con SQL directo (ver ``comercial.py`` y
# ``schema.sql``), así que estos modelos declaran el mismo esquema: son el
# modelo relacional en SQLAlchemy y lo que ``initialize_models`` crea en SQLite.
# Si se cambia una columna aquí, hay que cambiarla también en esos dos sitios.
#
# Las fechas se guardan como texto ``'YYYY-MM-DD HH:MM:SS'`` en los dos motores,
# de ahí el ``String`` en vez de ``DateTime``.


class Venta(Base):
    __tablename__ = 'ventas'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cliente_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    cliente_nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    cliente_documento: Mapped[str] = mapped_column(String(20), nullable=False, default='')
    usuario_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    usuario_nombre: Mapped[str] = mapped_column(String(160), nullable=False, default='')
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    impuestos: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='Registrada')
    observaciones: Mapped[str] = mapped_column(Text, nullable=False, default='')
    fecha: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[Optional[str]] = mapped_column(String(20))
    detalle: Mapped[list['DetalleVenta']] = relationship('DetalleVenta', back_populates='venta', cascade='all, delete-orphan')
    factura: Mapped[Optional['Factura']] = relationship('Factura', back_populates='venta', uselist=False, cascade='all, delete-orphan')
    pagos: Mapped[list['Pago']] = relationship('Pago', back_populates='venta', cascade='all, delete-orphan')


class DetalleVenta(Base):
    __tablename__ = 'detalle_ventas'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey('ventas.id', ondelete='CASCADE'), nullable=False)
    # "producto" o "servicio": la línea apunta a una u otra tabla del catálogo,
    # así que item_id no puede ser una clave foránea.
    item_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    item_id: Mapped[Optional[int]] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    venta: Mapped['Venta'] = relationship('Venta', back_populates='detalle')


class Factura(Base):
    __tablename__ = 'facturas'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey('ventas.id', ondelete='CASCADE'), unique=True, nullable=False)
    cliente_nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    cliente_documento: Mapped[str] = mapped_column(String(20), nullable=False, default='')
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    impuestos: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='Emitida')
    fecha: Mapped[str] = mapped_column(String(20), nullable=False)
    venta: Mapped['Venta'] = relationship('Venta', back_populates='factura')
    detalle: Mapped[list['DetalleFactura']] = relationship('DetalleFactura', back_populates='factura', cascade='all, delete-orphan')
    pagos: Mapped[list['Pago']] = relationship('Pago', back_populates='factura')


class DetalleFactura(Base):
    __tablename__ = 'detalle_facturas'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factura_id: Mapped[int] = mapped_column(Integer, ForeignKey('facturas.id', ondelete='CASCADE'), nullable=False)
    item_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    impuesto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    factura: Mapped['Factura'] = relationship('Factura', back_populates='detalle')


class Pago(Base):
    """Cada intento de cobro, salga bien o mal.

    Se guarda también el rechazado, porque el historial de una compra tiene
    que poder explicar por qué no está pagada. ``entidad`` es la franquicia de
    la tarjeta, el banco del débito PSE o el punto de pago en efectivo; de la
    tarjeta solo quedan los cuatro últimos dígitos, y ni el número completo ni
    el código de seguridad se escriben en ninguna parte.
    """

    __tablename__ = 'pagos'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referencia: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey('ventas.id', ondelete='CASCADE'), nullable=False)
    factura_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('facturas.id', ondelete='SET NULL'))
    cliente_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    cliente_nombre: Mapped[str] = mapped_column(String(160), nullable=False, default='')
    metodo: Mapped[str] = mapped_column(String(20), nullable=False, default='tarjeta')
    entidad: Mapped[str] = mapped_column(String(60), nullable=False, default='')
    ultimos_digitos: Mapped[str] = mapped_column(String(4), nullable=False, default='')
    cuotas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default='COP')
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='Pendiente')
    motivo: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    transaccion: Mapped[str] = mapped_column(String(80), nullable=False, default='')
    fecha: Mapped[str] = mapped_column(String(20), nullable=False)
    venta: Mapped['Venta'] = relationship('Venta', back_populates='pagos')
    factura: Mapped[Optional['Factura']] = relationship('Factura', back_populates='pagos')
    cliente: Mapped[Optional['User']] = relationship('User', back_populates='pagos')


class Pqr(Base):
    __tablename__ = 'pqr'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    radicado: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default='Petición')
    asunto: Mapped[str] = mapped_column(String(160), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='Pendiente')
    respuesta: Mapped[str] = mapped_column(Text, nullable=False, default='')
    cliente_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    cliente_nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    cliente_email: Mapped[str] = mapped_column(String(120), nullable=False, default='')
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(20), nullable=False)


class Conversacion(Base):
    __tablename__ = 'conversaciones'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    titulo: Mapped[str] = mapped_column(String(160), nullable=False, default='Conversación')
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(20), nullable=False)
    mensajes: Mapped[list['Mensaje']] = relationship('Mensaje', back_populates='conversacion', cascade='all, delete-orphan')


class Mensaje(Base):
    __tablename__ = 'mensajes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversacion_id: Mapped[int] = mapped_column(Integer, ForeignKey('conversaciones.id', ondelete='CASCADE'), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    # El otro extremo de Conversacion.mensajes. Sin esta línea, configurar los
    # mapeadores falla: back_populates exige que la relación exista a los dos lados.
    conversacion: Mapped['Conversacion'] = relationship('Conversacion', back_populates='mensajes')
