import asyncio
import os
import re
import sqlite3
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError
try:
    from .models import Base
    from .schemas import (
        CatalogResponseSchema,
        HealthResponseSchema,
        MessageResponseSchema,
        ProductsResponseSchema,
        RegistrationResponseSchema,
        ResourceCreateSchema,
        ResourceResponseSchema,
        ResourceStatusSchema,
        ResourceUpdateSchema,
        ServicesResponseSchema,
        SessionResponseSchema,
        TokenResponseSchema,
        UserCreateSchema,
        UserLoginSchema,
        UserResponseSchema,
        UsersResponseSchema,
        UserUpdateSchema,
    )
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
    from schemas import (
        CatalogResponseSchema,
        HealthResponseSchema,
        MessageResponseSchema,
        ProductsResponseSchema,
        RegistrationResponseSchema,
        ResourceCreateSchema,
        ResourceResponseSchema,
        ResourceStatusSchema,
        ResourceUpdateSchema,
        ServicesResponseSchema,
        SessionResponseSchema,
        TokenResponseSchema,
        UserCreateSchema,
        UserLoginSchema,
        UserResponseSchema,
        UsersResponseSchema,
        UserUpdateSchema,
    )
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

DESCRIPCION = """
API de **SimonC Realidad Virtual**, la tienda de gafas y servicios de realidad
virtual. Está construida con FastAPI y cubre catálogo, ventas, facturación,
PQR, reportes y un chatbot con inteligencia artificial.

### Cómo probar los endpoints protegidos

1. Pulsa el botón **Authorize** de arriba a la derecha.
2. Entra con una de las cuentas de ejemplo:
   `admin@simonsc.com` / `Admin1234` (Administrador),
   `empleado@simonsc.com` / `Empleado1234` (Empleado).
3. Todas las peticiones de esta página saldrán ya con el token puesto.

La sesión es un **JWT**. Los endpoints indican con un candado si piden sesión,
y varios además exigen un rol concreto: si el rol no alcanza, responden `403`.
"""

ETIQUETAS = [
    {'name': 'auth', 'description': 'Registro, inicio de sesión, recuperación de contraseña y estado del correo.'},
    {'name': 'usuarios', 'description': 'Administración de las cuentas y sus roles. Solo Administrador.'},
    {'name': 'catalogo', 'description': 'Productos y servicios. El catálogo público no necesita sesión.'},
    {'name': 'ventas', 'description': 'Ventas del panel y pedidos del carrito de la tienda.'},
    {'name': 'facturas', 'description': 'Emisión, consulta y descarga en PDF de las facturas.'},
    {'name': 'reportes', 'description': 'Reporte diario de ventas, exportable a PDF y a Excel.'},
    {'name': 'dashboard', 'description': 'Indicadores y gráficos del panel. Solo Administrador.'},
    {'name': 'pqr', 'description': 'Peticiones, quejas y reclamos, y la respuesta al cliente.'},
    {'name': 'chatbot', 'description': 'Asistente con inteligencia artificial sobre el catálogo real.'},
    {'name': 'sistema', 'description': 'Estado del servicio.'},
]

app = FastAPI(
    title='SimonC Realidad Virtual — API',
    version='2.0.0',
    description=DESCRIPCION,
    openapi_tags=ETIQUETAS,
    contact={'name': 'Simon Cardona Hincapie', 'url': 'https://github.com/SimonC5/react'},
    license_info={'name': 'Proyecto formativo SENA — ADSO ficha 3406211'},
)
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

# Los esquemas viven todos en schemas.py, con sus validaciones y sus ejemplos.
# Estos alias mantienen los nombres cortos que ya usaba el resto del archivo.
UserLogin = UserLoginSchema
UserUpdate = UserUpdateSchema
ResourceCreate = ResourceCreateSchema
ResourceStatus = ResourceStatusSchema

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


def fila_del_catalogo(tabla: str, registro_id: int) -> dict[str, Any]:
    """Un producto o un servicio por su id, o 404 si no existe."""
    conn = get_db_connection()
    try:
        fila = conn.execute(f'SELECT * FROM {tabla} WHERE id = ?', (registro_id,)).fetchone()
    finally:
        conn.close()
    if fila is None:
        raise HTTPException(status_code=404, detail='Registro no encontrado.')
    return dict(fila)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def public_user_row(user: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(user)
    return {
        'id': data.get('id'),
        'name': data.get('name'),
        'lastName': data.get('last_name') or '',
        'email': data.get('email'),
        'role': data.get('role'),
        'active': bool(data.get('active', 1)),
    }


@app.on_event('startup')
def startup_event():
    init_db()


@app.get(
    '/api/health',
    tags=['sistema'],
    summary='Estado del servicio',
    response_model=HealthResponseSchema,
)
async def health():
    """Comprueba que la API responde y con qué motor de base de datos corre.

    Es asíncrono a propósito: no toca la base de datos, así que atiende sin
    ocupar un hilo. Es el endpoint que consulta Render para saber si el
    servicio sigue vivo.
    """
    return {'status': 'ok', 'database': 'mysql' if usa_mysql() else 'sqlite'}


@app.post(
    '/api/auth/register',
    tags=['auth'],
    summary='Crear una cuenta de cliente',
    response_model=RegistrationResponseSchema,
    status_code=201,
    responses={409: {'description': 'El correo o el documento ya están registrados.'}},
)
def register(payload: UserCreateSchema):
    """Registra un cliente nuevo. La contraseña se guarda como hash, nunca en claro."""
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


@app.post('/api/usuarios/registro', include_in_schema=False, status_code=201)
def register_user_alias(payload: UserCreateSchema):
    return register(payload)


@app.post(
    '/api/auth/login',
    tags=['auth'],
    summary='Iniciar sesión y obtener el token',
    response_model=SessionResponseSchema,
    responses={401: {'description': 'Credenciales inválidas o usuario inactivo.'}},
)
def login(payload: UserLogin):
    """Devuelve el JWT y el usuario. Es el que usa el frontend de React."""
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


@app.get(
    '/api/auth/me',
    tags=['auth'],
    summary='Ver la sesión actual',
    dependencies=[Depends(get_current_user)],
)
def me(current_user: dict[str, Any] = Depends(get_current_user)):
    """Quién es el dueño del token, para que el frontend recupere la sesión."""
    return {'user': public_user_row(current_user)}


@app.post(
    '/api/auth/token',
    tags=['auth'],
    summary='Iniciar sesión desde /docs (OAuth2 password)',
    response_model=TokenResponseSchema,
    responses={401: {'description': 'Credenciales inválidas o usuario inactivo.'}},
)
def token_oauth2(form: OAuth2PasswordRequestForm = Depends()):
    """Mismo inicio de sesión, en el formato del flujo *OAuth2 password*.

    Es el que usa el botón **Authorize** de esta página: el correo va en el
    campo `username`. Devuelve el mismo JWT que `/api/auth/login`, pero con los
    nombres `access_token` y `token_type` que espera el estándar.
    """
    try:
        credenciales = UserLoginSchema(email=form.username, password=form.password)
    except ValidationError as exc:
        # Si `username` no es un correo, es una credencial mala, no un error
        # del formato de la petición: corresponde 401, igual que una clave mala.
        raise HTTPException(status_code=401, detail='Credenciales inválidas o usuario inactivo.') from exc
    sesion = login(credenciales)
    return {'access_token': sesion['token'], 'token_type': 'bearer'}


@app.get(
    '/api/users',
    tags=['usuarios'],
    summary='Listar usuarios',
    response_model=UsersResponseSchema,
    dependencies=[Depends(require_roles('Administrador'))],
)
def list_users(current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    """Todas las cuentas con su rol. Nunca devuelve la contraseña."""
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


@app.get(
    '/api/users/{user_id}',
    tags=['usuarios'],
    summary='Consultar un usuario',
    response_model=UserResponseSchema,
    responses={404: {'description': 'No existe ninguna cuenta con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
def get_user(user_id: int, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    """Una sola cuenta por su id."""
    conn = get_db_connection()
    try:
        fila = conn.execute(
            '''
            SELECT u.id, u.name, u.last_name AS lastName, u.document_type AS documentType,
                   u.document_number AS documentNumber, u.address, u.phone, u.email, u.active, r.name AS role
            FROM usuarios u
            JOIN roles r ON r.id = u.role_id
            WHERE u.id = ?
            ''',
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if fila is None:
        raise HTTPException(status_code=404, detail='Usuario no encontrado.')
    return dict(fila)


@app.post(
    '/api/users',
    tags=['usuarios'],
    summary='Crear una cuenta',
    status_code=201,
    dependencies=[Depends(require_roles('Administrador'))],
)
def create_user(payload: dict[str, Any], current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    """Crea una cuenta con el rol que indique el Administrador."""
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


@app.put(
    '/api/users/{user_id}',
    tags=['usuarios'],
    summary='Actualizar una cuenta',
    responses={404: {'description': 'No existe ninguna cuenta con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
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


@app.patch(
    '/api/users/{user_id}/status',
    tags=['usuarios'],
    summary='Activar o desactivar una cuenta',
    response_model=MessageResponseSchema,
    responses={404: {'description': 'No existe ninguna cuenta con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
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


@app.delete(
    '/api/users/{user_id}',
    tags=['usuarios'],
    summary='Eliminar una cuenta',
    response_model=MessageResponseSchema,
    responses={404: {'description': 'No existe ninguna cuenta con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
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


@app.get(
    '/api/catalogo',
    tags=['catalogo'],
    summary='Catálogo público de la tienda',
    response_model=CatalogResponseSchema,
)
async def public_catalog():
    """Catálogo de la web pública: solo lo publicado, sin necesidad de sesión.

    Es lo que alimenta las páginas de Productos y Servicios y el carrito, así
    que devuelve el id y el precio reales para que el pedido no dependa de
    datos escritos en el navegador.

    Es el endpoint más visitado (lo pide cualquiera que entre a la tienda, sin
    haber iniciado sesión), así que está escrito con ``async``. El controlador
    de la base de datos es bloqueante, y por eso la consulta se manda a un hilo
    aparte con ``asyncio.to_thread``: mientras responde la base de datos, el
    bucle de eventos queda libre para atender a los demás visitantes en vez de
    quedarse esperando.
    """
    return await asyncio.to_thread(_leer_catalogo_publico)


def _leer_catalogo_publico() -> dict[str, Any]:
    """La parte bloqueante de `public_catalog`, para correrla fuera del bucle."""
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


@app.get(
    '/api/products',
    tags=['catalogo'],
    summary='Listar products',
    response_model=ProductsResponseSchema,
)
def list_products(current_user: dict[str, Any] = Depends(get_current_user)):
    """Catálogo completo para el panel. El cliente solo ve lo publicado."""
    conn = get_db_connection()
    try:
        rows = conn.execute(f'SELECT * FROM productos{_solo_publicado(current_user)} ORDER BY id DESC').fetchall()
        return {'products': [dict(row) for row in rows]}
    finally:
        conn.close()


@app.get(
    '/api/products/{product_id}',
    tags=['catalogo'],
    summary='Consultar un producto',
    response_model=ResourceResponseSchema,
    responses={404: {'description': 'No existe ningún producto con ese id.'}},
)
def get_product(product_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    """Un solo producto por su id. Al cliente solo se le muestra si está publicado."""
    registro = fila_del_catalogo('productos', product_id)
    if not registro.get('active') and (current_user.get('role') or '') == 'Cliente':
        raise HTTPException(status_code=404, detail='Registro no encontrado.')
    return registro


@app.post(
    '/api/products',
    tags=['catalogo'],
    summary='Crear un producto',
    response_model=ResourceResponseSchema,
    status_code=201,
    dependencies=[Depends(require_roles('Administrador'))],
)
def create_product(payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    """Da de alta un producto y devuelve el registro recién creado."""
    if not payload.name or payload.price < 0:
        raise HTTPException(status_code=400, detail='Nombre y precio válido son obligatorios.')
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO productos (name, description, price, active) VALUES (?, ?, ?, 1)',
            (payload.name.strip(), payload.description.strip(), float(payload.price)),
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    finally:
        conn.close()
    return fila_del_catalogo('productos', nuevo_id)


@app.put(
    '/api/products/{product_id}',
    tags=['catalogo'],
    summary='Actualizar un producto',
    response_model=ResourceResponseSchema,
    responses={404: {'description': 'No existe ningún producto con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
def update_product(product_id: int, payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador'))):
    """Cambia nombre, descripción y precio, y devuelve cómo quedó."""
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
    finally:
        conn.close()
    return fila_del_catalogo('productos', product_id)


@app.patch(
    '/api/products/{product_id}/status',
    tags=['catalogo'],
    summary='Publicar o retirar un producto',
    response_model=MessageResponseSchema,
    responses={404: {'description': 'No existe ningún producto con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
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


@app.delete(
    '/api/products/{product_id}',
    tags=['catalogo'],
    summary='Eliminar un producto',
    response_model=MessageResponseSchema,
    responses={404: {'description': 'No existe ningún producto con ese id.'}},
    dependencies=[Depends(require_roles('Administrador'))],
)
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


@app.get(
    '/api/services',
    tags=['catalogo'],
    summary='Listar services',
    response_model=ServicesResponseSchema,
)
def list_services(current_user: dict[str, Any] = Depends(get_current_user)):
    """Catálogo completo para el panel. El cliente solo ve lo publicado."""
    conn = get_db_connection()
    try:
        rows = conn.execute(f'SELECT * FROM servicios{_solo_publicado(current_user)} ORDER BY id DESC').fetchall()
        return {'services': [dict(row) for row in rows]}
    finally:
        conn.close()


@app.get(
    '/api/services/{service_id}',
    tags=['catalogo'],
    summary='Consultar un servicio',
    response_model=ResourceResponseSchema,
    responses={404: {'description': 'No existe ningún servicio con ese id.'}},
)
def get_service(service_id: int, current_user: dict[str, Any] = Depends(get_current_user)):
    """Un solo servicio por su id. Al cliente solo se le muestra si está publicado."""
    registro = fila_del_catalogo('servicios', service_id)
    if not registro.get('active') and (current_user.get('role') or '') == 'Cliente':
        raise HTTPException(status_code=404, detail='Registro no encontrado.')
    return registro


@app.post(
    '/api/services',
    tags=['catalogo'],
    summary='Crear un servicio',
    response_model=ResourceResponseSchema,
    status_code=201,
    dependencies=[Depends(require_roles('Administrador', 'Empleado'))],
)
def create_service(payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador', 'Empleado'))):
    """Da de alta un servicio y devuelve el registro recién creado."""
    if not payload.name or payload.price < 0:
        raise HTTPException(status_code=400, detail='Nombre y precio válido son obligatorios.')
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO servicios (name, description, price, active) VALUES (?, ?, ?, 1)',
            (payload.name.strip(), payload.description.strip(), float(payload.price)),
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    finally:
        conn.close()
    return fila_del_catalogo('servicios', nuevo_id)


@app.put(
    '/api/services/{service_id}',
    tags=['catalogo'],
    summary='Actualizar un servicio',
    response_model=ResourceResponseSchema,
    responses={404: {'description': 'No existe ningún servicio con ese id.'}},
    dependencies=[Depends(require_roles('Administrador', 'Empleado'))],
)
def update_service(service_id: int, payload: ResourceCreate, current_user: dict[str, Any] = Depends(require_roles('Administrador', 'Empleado'))):
    """Cambia nombre, descripción y precio, y devuelve cómo quedó."""
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
    finally:
        conn.close()
    return fila_del_catalogo('servicios', service_id)


@app.patch(
    '/api/services/{service_id}/status',
    tags=['catalogo'],
    summary='Publicar o retirar un servicio',
    response_model=MessageResponseSchema,
    responses={404: {'description': 'No existe ningún servicio con ese id.'}},
    dependencies=[Depends(require_roles('Administrador', 'Empleado'))],
)
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


@app.delete(
    '/api/services/{service_id}',
    tags=['catalogo'],
    summary='Eliminar un servicio',
    response_model=MessageResponseSchema,
    responses={404: {'description': 'No existe ningún servicio con ese id.'}},
    dependencies=[Depends(require_roles('Administrador', 'Empleado'))],
)
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
