from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


role_permissions = Table(
    'role_permisos',
    Base.metadata,
    Column('role_id', ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permiso_id', ForeignKey('permisos.id', ondelete='CASCADE'), primary_key=True),
)


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(40), unique=True, nullable=False)
    users = relationship('User', back_populates='role')
    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')


class Permission(Base):
    __tablename__ = 'permisos'
    id = Column(Integer, primary_key=True)
    name = Column(String(60), unique=True, nullable=False)
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')


class User(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    document_type = Column(String(20), nullable=False)
    document_number = Column(String(12), unique=True, nullable=False)
    address = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    role = relationship('Role', back_populates='users')


class Product(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False, default='')
    price = Column(Numeric(12, 2), nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


class Service(Base):
    __tablename__ = 'servicios'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=False, default='')
    price = Column(Numeric(12, 2), nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)


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
    id = Column(Integer, primary_key=True)
    numero = Column(String(20), unique=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    cliente_nombre = Column(String(160), nullable=False)
    cliente_documento = Column(String(20), nullable=False, default='')
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    usuario_nombre = Column(String(160), nullable=False, default='')
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    descuento = Column(Numeric(12, 2), nullable=False, default=0)
    impuestos = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    estado = Column(String(20), nullable=False, default='Registrada')
    observaciones = Column(Text, nullable=False, default='')
    fecha = Column(String(20), nullable=False)
    created_at = Column(String(20))
    detalle = relationship('DetalleVenta', back_populates='venta', cascade='all, delete-orphan')
    factura = relationship('Factura', back_populates='venta', uselist=False, cascade='all, delete-orphan')


class DetalleVenta(Base):
    __tablename__ = 'detalle_ventas'
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey('ventas.id', ondelete='CASCADE'), nullable=False)
    # "producto" o "servicio": la línea apunta a una u otra tabla del catálogo,
    # así que item_id no puede ser una clave foránea.
    item_tipo = Column(String(20), nullable=False)
    item_id = Column(Integer)
    nombre = Column(String(160), nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False, default=1)
    precio_unitario = Column(Numeric(12, 2), nullable=False, default=0)
    descuento = Column(Numeric(12, 2), nullable=False, default=0)
    impuesto = Column(Numeric(12, 2), nullable=False, default=0)
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    venta = relationship('Venta', back_populates='detalle')


class Factura(Base):
    __tablename__ = 'facturas'
    id = Column(Integer, primary_key=True)
    numero = Column(String(20), unique=True, nullable=False)
    venta_id = Column(Integer, ForeignKey('ventas.id', ondelete='CASCADE'), unique=True, nullable=False)
    cliente_nombre = Column(String(160), nullable=False)
    cliente_documento = Column(String(20), nullable=False, default='')
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    descuento = Column(Numeric(12, 2), nullable=False, default=0)
    impuestos = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    estado = Column(String(20), nullable=False, default='Emitida')
    fecha = Column(String(20), nullable=False)
    venta = relationship('Venta', back_populates='factura')
    detalle = relationship('DetalleFactura', back_populates='factura', cascade='all, delete-orphan')


class DetalleFactura(Base):
    __tablename__ = 'detalle_facturas'
    id = Column(Integer, primary_key=True)
    factura_id = Column(Integer, ForeignKey('facturas.id', ondelete='CASCADE'), nullable=False)
    item_tipo = Column(String(20), nullable=False)
    nombre = Column(String(160), nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False, default=1)
    precio_unitario = Column(Numeric(12, 2), nullable=False, default=0)
    descuento = Column(Numeric(12, 2), nullable=False, default=0)
    impuesto = Column(Numeric(12, 2), nullable=False, default=0)
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    total = Column(Numeric(12, 2), nullable=False, default=0)
    factura = relationship('Factura', back_populates='detalle')


class Pqr(Base):
    __tablename__ = 'pqr'
    id = Column(Integer, primary_key=True)
    radicado = Column(String(20), unique=True, nullable=False)
    tipo = Column(String(20), nullable=False, default='Petición')
    asunto = Column(String(160), nullable=False)
    descripcion = Column(Text, nullable=False)
    estado = Column(String(20), nullable=False, default='Pendiente')
    respuesta = Column(Text, nullable=False, default='')
    cliente_id = Column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    cliente_nombre = Column(String(160), nullable=False)
    cliente_email = Column(String(120), nullable=False, default='')
    created_at = Column(String(20), nullable=False)
    updated_at = Column(String(20), nullable=False)


class Conversacion(Base):
    __tablename__ = 'conversaciones'
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='SET NULL'))
    titulo = Column(String(160), nullable=False, default='Conversación')
    created_at = Column(String(20), nullable=False)
    updated_at = Column(String(20), nullable=False)
    mensajes = relationship('Mensaje', back_populates='conversacion', cascade='all, delete-orphan')


class Mensaje(Base):
    __tablename__ = 'mensajes'
    id = Column(Integer, primary_key=True)
    conversacion_id = Column(Integer, ForeignKey('conversaciones.id', ondelete='CASCADE'), nullable=False)
    rol = Column(String(20), nullable=False)
    contenido = Column(Text, nullable=False)
    created_at = Column(String(20), nullable=False)
