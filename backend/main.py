import os
import re
import sqlite3
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
try:
    from .models import Base
    from .schemas import UserCreateSchema
    from .database import initialize_models
    from .core import (
        aplicar_schema_sql,
        usa_mysql,
        DATA_DIR,
        DB_PATH,
        create_access_token,
        dominio_publico,
        get_current_user,
        get_db_connection,
        hash_password,
        require_roles,
        verify_password,
    )
    from .catalogo_demo import RETIRADOS as CATALOGO_RETIRADO, SEED as SEED_CATALOGO
    from .comercial import init_comercial_db
    from .recuperacion import init_recuperacion_db
    from . import chatbot, dashboard, facturas, pqr, recuperacion, reportes, ventas
except ImportError:
    from models import Base
    from schemas import UserCreateSchema
    from database import initialize_models
    from core import (
        aplicar_schema_sql,
        usa_mysql,
        DATA_DIR,
        DB_PATH,
        create_access_token,
        dominio_publico,
        get_current_user,
        get_db_connection,
        hash_password,
        require_roles,
        verify_password,
    )
    from catalogo_demo import RETIRADOS as CATALOGO_RETIRADO, SEED as SEED_CATALOGO
    from comercial import init_comercial_db
    from recuperacion import init_recuperacion_db
    import chatbot, dashboard, facturas, pqr, recuperacion, reportes, ventas

DEFAULT_ORIGINS = [
    'http://localhost:5173', 'http://127.0.0.1:5173',
    'http://localhost:5174', 'http://127.0.0.1:5174',
    'http://localhost:5175', 'http://127.0.0.1:5175',
    'http://localhost:5176', 'http://127.0.0.1:5176',
]



# En producción el dominio del Frontend se configura con FRONTEND_URL / CORS_ORIGINS.
EXTRA_ORIGINS = list(dict.fromkeys(
    origen
    for origen in (
        dominio_publico(valor)
        for valor in f"{os.getenv('CORS_ORIGINS', '')},{os.getenv('FRONTEND_URL', '')}".split(',')
    )
    if origen
))

app = FastAPI(title='SimonC API', version='2.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_ORIGINS + EXTRA_ORIGINS,
    allow_origin_regex=os.getenv('CORS_ORIGIN_REGEX') or None,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

for modulo in (ventas, facturas, reportes, dashboard, pqr, chatbot, recuperacion):
    app.include_router(modulo.router)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    lastName: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = 'Cliente'

class ResourceCreate(BaseModel):
    name: str
    description: str = ''
    price: float = 0

class ResourceStatus(BaseModel):
    active: bool

def init_db():
    if not usa_mysql():
        DATA_DIR.mkdir(exist_ok=True, parents=True)
        initialize_models(DB_PATH)
    conn = get_db_connection()
    try:
        if usa_mysql():
            # En MySQL el esquema es el de backend/schema.sql, que ya trae los
            # tipos propios del motor (INT AUTO_INCREMENT, DECIMAL, DATETIME).
            aplicar_schema_sql(conn)
        else:
            conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS permisos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS role_permisos (
                role_id INTEGER NOT NULL,
                permiso_id INTEGER NOT NULL,
                PRIMARY KEY (role_id, permiso_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                document_number TEXT NOT NULL UNIQUE,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                role_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            );

            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS servicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
            )

        roles = ['Administrador', 'Empleado', 'Cliente']
        for role_name in roles:
            conn.execute('INSERT OR IGNORE INTO roles (name) VALUES (?)', (role_name,))

        permissions = ['users:read', 'users:write', 'products:read', 'products:write', 'services:read', 'services:write']
        for perm_name in permissions:
            conn.execute('INSERT OR IGNORE INTO permisos (name) VALUES (?)', (perm_name,))

        rows = conn.execute('SELECT id, name FROM roles').fetchall()
        role_map = {row['name']: row['id'] for row in rows}
        perms = conn.execute('SELECT id, name FROM permisos').fetchall()
        permission_map = {row['name']: row['id'] for row in perms}

        grants = {
            'Administrador': list(permission_map.keys()),
            'Empleado': ['services:read', 'services:write'],
            'Cliente': ['products:read', 'services:read'],
        }
        for role_name, granted_permissions in grants.items():
            role_id = role_map[role_name]
            for permission_name in granted_permissions:
                conn.execute(
                    'INSERT OR IGNORE INTO role_permisos (role_id, permiso_id) VALUES (?, ?)',
                    (role_id, permission_map[permission_name]),
                )

        admin_password = hash_password('Admin1234')
        employee_password = hash_password('Empleado1234')

        conn.execute(
            'INSERT OR IGNORE INTO usuarios (name, last_name, document_type, document_number, address, phone, email, password_hash, active, role_id) VALUES (?,?,?,?,?,?,?,?,?,?)',
            ('Admin', 'SimonC', 'CC', '1000000001', 'Oficina principal', '3000000000', 'admin@simonsc.com', admin_password, 1, role_map['Administrador'])
        )
        conn.execute(
            'INSERT OR IGNORE INTO usuarios (name, last_name, document_type, document_number, address, phone, email, password_hash, active, role_id) VALUES (?,?,?,?,?,?,?,?,?,?)',
            ('Empleado', 'SimonC', 'CC', '1000000002', 'Oficina principal', '3000000001', 'empleado@simonsc.com', employee_password, 1, role_map['Empleado'])
        )

        # "name" no tiene restricción UNIQUE, así que INSERT OR IGNORE no evitaba
        # nada y el catálogo se duplicaba en cada arranque del backend.
        for table, name, description, price in SEED_CATALOGO:
            # Se comprueba antes de insertar porque "name" no es UNIQUE y la
            # forma con WHERE NOT EXISTS no es portable entre SQLite y MySQL.
            existe = conn.execute(f'SELECT 1 FROM {table} WHERE name = ?', (name,)).fetchone()
            if existe is None:
                conn.execute(
                    f'INSERT INTO {table} (name, description, price, active) VALUES (?, ?, ?, 1)',
                    (name, description, price),
                )

        # El catálogo genérico del avance anterior se oculta de la tienda, que
        # ahora es de realidad virtual. No se borra: hay ventas que lo citan.
        for table, name in CATALOGO_RETIRADO:
            conn.execute(f'UPDATE {table} SET active = 0 WHERE name = ?', (name,))

        conn.commit()

        if usa_mysql():
            # Las tablas ya existen por schema.sql; falta sembrar la demo.
            init_comercial_db(conn, crear_tablas=False)
        else:
            init_comercial_db(conn)
            init_recuperacion_db(conn)
    finally:
        conn.close()


def normalize_email(value: str) -> str:
    return value.strip().lower()


def public_user_row(user: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(user)
    return {
        'id': data.get('id'),
        'name': data.get('name'),
        'lastName': data.get('last_name'),
        'email': data.get('email'),
        'role': data.get('role'),
        'active': bool(data.get('active', 1)),
    }


@app.on_event('startup')
def startup_event():
    init_db()


@app.get('/api/health')
def health():
    return {'status': 'ok', 'database': 'sqlite'}


@app.post('/api/auth/register')
def register(payload: UserCreateSchema):
    if not payload.name or not payload.lastName or not payload.address or not payload.documentNumber:
        raise HTTPException(status_code=400, detail='Revisa los datos del usuario.')
    if len(payload.password) < 8 or not any(ch.isalpha() for ch in payload.password) or not any(ch.isdigit() for ch in payload.password):
        raise HTTPException(status_code=400, detail='La contraseña debe tener al menos 8 caracteres, letras y números.')
    email = normalize_email(payload.email)
    conn = get_db_connection()
    try:
        role = conn.execute('SELECT id FROM roles WHERE name = ?', ('Cliente',)).fetchone()
        if role is None:
            raise HTTPException(status_code=500, detail='No se pudo definir el rol del cliente.')
        try:
            cursor = conn.execute(
                'INSERT INTO usuarios (name, last_name, document_type, document_number, address, phone, email, password_hash, active, role_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)',
                (payload.name.strip(), payload.lastName.strip(), payload.documentType, payload.documentNumber.strip(), payload.address.strip(), payload.phone.strip(), email, hash_password(payload.password), role['id']),
            )
            conn.commit()
            user_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail='El correo o documento ya está registrado.') from exc
        return {
            'message': 'Registro completado con éxito.',
            'user': {
                'id': user_id,
                'name': payload.name.strip(),
                'lastName': payload.lastName.strip(),
                'email': email,
                'role': 'Cliente',
                'active': True,
            },
        }
    finally:
        conn.close()


@app.post('/api/usuarios/registro')
def register_user_alias(payload: UserCreateSchema):
    return register(payload)


@app.post('/api/auth/login')
def login(payload: UserLogin):
    email = normalize_email(str(payload.email))
    conn = get_db_connection()
    try:
        user = conn.execute(
            '''
            SELECT u.*, r.name AS role
            FROM usuarios u
            JOIN roles r ON r.id = u.role_id
            WHERE u.email = ?
            ''',
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if user is None or not user['active'] or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Credenciales inválidas o usuario inactivo.')

    token = create_access_token({'id': user['id'], 'name': user['name'], 'email': user['email'], 'role': user['role']})
    return {'token': token, 'user': public_user_row(user)}


@app.get('/api/auth/me', dependencies=[Depends(get_current_user)])
def me(current_user: dict[str, Any] = Depends(get_current_user)):
    return {'user': public_user_row(current_user)}


@app.get('/api/users', dependencies=[Depends(require_roles('Administrador'))])
def list_users(current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            '''
            SELECT u.id, u.name, u.last_name AS lastName, u.document_type AS documentType, u.document_number AS documentNumber,
                   u.address, u.phone, u.email, u.active, r.name AS role
            FROM usuarios u
            JOIN roles r ON r.id = u.role_id
            ORDER BY u.id DESC
            '''
        ).fetchall()
        return {'users': [dict(row) for row in rows]}
    finally:
        conn.close()


@app.post('/api/users', dependencies=[Depends(require_roles('Administrador'))])
def create_user(payload: dict[str, Any], current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    role_name = payload.get('role', 'Cliente')
    if not payload.get('name') or not payload.get('lastName') or not payload.get('documentNumber') or not payload.get('address') or not payload.get('password'):
        raise HTTPException(status_code=400, detail='Datos de usuario incompletos o inválidos.')
    if len(str(payload.get('password'))) < 8:
        raise HTTPException(status_code=400, detail='La contraseña debe tener al menos 8 caracteres.')
    # La misma regla que el registro público: este endpoint recibe un diccionario
    # suelto, así que el documento hay que revisarlo aquí a mano.
    if not re.fullmatch(r'\d{6,12}', str(payload.get('documentNumber', ''))):
        raise HTTPException(status_code=400, detail='El documento debe contener entre 6 y 12 dígitos numéricos.')

    conn = get_db_connection()
    try:
        role = conn.execute('SELECT id FROM roles WHERE name = ?', (role_name,)).fetchone()
        if role is None:
            raise HTTPException(status_code=400, detail='Rol inválido.')
        try:
            cursor = conn.execute(
                'INSERT INTO usuarios (name, last_name, document_type, document_number, address, phone, email, password_hash, active, role_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)',
                (
                    str(payload['name']).strip(),
                    str(payload['lastName']).strip(),
                    str(payload.get('documentType', 'CC')),
                    str(payload['documentNumber']).strip(),
                    str(payload['address']).strip(),
                    str(payload.get('phone', '')).strip(),
                    str(payload['email']).strip().lower(),
                    hash_password(str(payload['password'])),
                    role['id'],
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail='No fue posible crear el usuario.') from exc
        return {'id': cursor.lastrowid}
    finally:
        conn.close()


@app.put('/api/users/{user_id}', dependencies=[Depends(require_roles('Administrador'))])
def update_user(user_id: int, payload: UserUpdate, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    if not payload.name or not payload.lastName or not payload.email:
        raise HTTPException(status_code=400, detail='Datos de usuario inválidos.')

    conn = get_db_connection()
    try:
        role = conn.execute('SELECT id FROM roles WHERE name = ?', (payload.role or 'Cliente',)).fetchone()
        if role is None:
            raise HTTPException(status_code=400, detail='Rol inválido.')
        updated = conn.execute(
            'UPDATE usuarios SET name = ?, last_name = ?, address = ?, phone = ?, email = ?, role_id = ? WHERE id = ?',
            (
                payload.name.strip(),
                payload.lastName.strip(),
                (payload.address or '').strip(),
                (payload.phone or '').strip(),
                str(payload.email).strip().lower(),
                role['id'],
                user_id,
            ),
        )
        conn.commit()
        if updated.rowcount == 0:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        return {'message': 'Usuario actualizado.'}
    finally:
        conn.close()


@app.patch('/api/users/{user_id}/status', dependencies=[Depends(require_roles('Administrador'))])
def patch_user_status(user_id: int, payload: ResourceStatus, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    conn = get_db_connection()
    try:
        updated = conn.execute('UPDATE usuarios SET active = ? WHERE id = ?', (1 if payload.active else 0, user_id))
        conn.commit()
        if updated.rowcount == 0:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        return {'message': 'Estado actualizado.'}
    finally:
        conn.close()


@app.delete('/api/users/{user_id}', dependencies=[Depends(require_roles('Administrador'))])
def delete_user(user_id: int, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    conn = get_db_connection()
    try:
        deleted = conn.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
        conn.commit()
        if deleted.rowcount == 0:
            raise HTTPException(status_code=404, detail='Usuario no encontrado.')
        return {'message': 'Usuario eliminado.'}
    finally:
        conn.close()


def get_resource_list(table: str):
    def handler(current_user: dict[str, Any] = Depends(get_current_user)):
        conn = get_db_connection()
        try:
            rows = conn.execute(f'SELECT * FROM {table}{_solo_publicado(current_user)} ORDER BY id DESC').fetchall()
            return {table.replace('productos', 'products').replace('servicios', 'services'): [dict(row) for row in rows]}
        finally:
            conn.close()

    return handler


@app.get('/api/catalogo')
def public_catalog():
    """Catálogo de la web pública: solo lo publicado, sin necesidad de sesión.

    Es lo que alimenta las páginas de Productos y Servicios y el carrito, así
    que devuelve el id y el precio reales para que el pedido no dependa de
    datos escritos en el navegador.
    """
    conn = get_db_connection()
    try:
        productos = conn.execute(
            'SELECT id, name, description, price FROM productos WHERE active = 1 ORDER BY id'
        ).fetchall()
        servicios = conn.execute(
            'SELECT id, name, description, price FROM servicios WHERE active = 1 ORDER BY id'
        ).fetchall()
        return {
            'productos': [dict(row) for row in productos],
            'servicios': [dict(row) for row in servicios],
        }
    finally:
        conn.close()


def _solo_publicado(current_user: dict[str, Any]) -> str:
    """El Cliente solo consulta el catálogo publicado; quien lo administra lo ve entero."""
    return ' WHERE active = 1' if current_user.get('role') == 'Cliente' else ''


@app.get('/api/products')
def list_products(current_user: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        rows = conn.execute(f'SELECT * FROM productos{_solo_publicado(current_user)} ORDER BY id DESC').fetchall()
        return {'products': [dict(row) for row in rows]}
    finally:
        conn.close()


@app.post('/api/products', dependencies=[Depends(require_roles('Administrador'))])
def create_product(payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    if not payload.name or payload.price < 0:
        raise HTTPException(status_code=400, detail='Nombre y precio válido son obligatorios.')
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO productos (name, description, price, active) VALUES (?, ?, ?, 1)',
            (payload.name.strip(), payload.description.strip(), float(payload.price)),
        )
        conn.commit()
        return {'id': cursor.lastrowid}
    finally:
        conn.close()


@app.put('/api/products/{product_id}', dependencies=[Depends(require_roles('Administrador'))])
def update_product(product_id: int, payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    if not payload.name or payload.price < 0:
        raise HTTPException(status_code=400, detail='Nombre y precio válido son obligatorios.')
    conn = get_db_connection()
    try:
        updated = conn.execute(
            'UPDATE productos SET name = ?, description = ?, price = ? WHERE id = ?',
            (payload.name.strip(), payload.description.strip(), float(payload.price), product_id),
        )
        conn.commit()
        if updated.rowcount == 0:
            raise HTTPException(status_code=404, detail='Registro no encontrado.')
        return {'message': 'Registro actualizado.'}
    finally:
        conn.close()


@app.patch('/api/products/{product_id}/status', dependencies=[Depends(require_roles('Administrador'))])
def change_product_status(product_id: int, payload: ResourceStatus, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    conn = get_db_connection()
    try:
        updated = conn.execute('UPDATE productos SET active = ? WHERE id = ?', (1 if payload.active else 0, product_id))
        conn.commit()
        if updated.rowcount == 0:
            raise HTTPException(status_code=404, detail='Registro no encontrado.')
        return {'message': 'Estado actualizado.'}
    finally:
        conn.close()


@app.delete('/api/products/{product_id}', dependencies=[Depends(require_roles('Administrador'))])
def delete_product(product_id: int, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    conn = get_db_connection()
    try:
        deleted = conn.execute('DELETE FROM productos WHERE id = ?', (product_id,))
        conn.commit()
        if deleted.rowcount == 0:
            raise HTTPException(status_code=404, detail='Registro no encontrado.')
        return {'message': 'Producto eliminado.'}
    finally:
        conn.close()


@app.get('/api/services')
def list_services(current_user: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        rows = conn.execute(f'SELECT * FROM servicios{_solo_publicado(current_user)} ORDER BY id DESC').fetchall()
        return {'services': [dict(row) for row in rows]}
    finally:
        conn.close()


@app.post('/api/services', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def create_service(payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador', 'Empleado'))):
    if not payload.name or payload.price < 0:
        raise HTTPException(status_code=400, detail='Nombre y precio válido son obligatorios.')
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO servicios (name, description, price, active) VALUES (?, ?, ?, 1)',
            (payload.name.strip(), payload.description.strip(), float(payload.price)),
        )
        conn.commit()
        return {'id': cursor.lastrowid}
    finally:
        conn.close()


@app.put('/api/services/{service_id}', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def update_service(service_id: int, payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador', 'Empleado'))):
    if not payload.name or payload.price < 0:
        raise HTTPException(status_code=400, detail='Nombre y precio válido son obligatorios.')
    conn = get_db_connection()
    try:
        updated = conn.execute(
            'UPDATE servicios SET name = ?, description = ?, price = ? WHERE id = ?',
            (payload.name.strip(), payload.description.strip(), float(payload.price), service_id),
        )
        conn.commit()
        if updated.rowcount == 0:
            raise HTTPException(status_code=404, detail='Registro no encontrado.')
        return {'message': 'Registro actualizado.'}
    finally:
        conn.close()


@app.patch('/api/services/{service_id}/status', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def change_service_status(service_id: int, payload: ResourceStatus, current_user: dict[str, Any] = Depends(require_roles('Administrador', 'Empleado'))):
    conn = get_db_connection()
    try:
        updated = conn.execute('UPDATE servicios SET active = ? WHERE id = ?', (1 if payload.active else 0, service_id))
        conn.commit()
        if updated.rowcount == 0:
            raise HTTPException(status_code=404, detail='Registro no encontrado.')
        return {'message': 'Estado actualizado.'}
    finally:
        conn.close()


@app.delete('/api/services/{service_id}', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def delete_service(service_id: int, current_user: dict[str, Any] = Depends(require_roles('Administrador', 'Empleado'))):
    conn = get_db_connection()
    try:
        deleted = conn.execute('DELETE FROM servicios WHERE id = ?', (service_id,))
        conn.commit()
        if deleted.rowcount == 0:
            raise HTTPException(status_code=404, detail='Registro no encontrado.')
        return {'message': 'Servicio eliminado.'}
    finally:
        conn.close()


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host='0.0.0.0', port=3001, reload=True)
