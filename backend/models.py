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
