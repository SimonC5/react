"""Módulo de PQR: peticiones, quejas y reclamos con su ciclo de estados."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

try:
    from .core import get_current_user, get_db_connection, require_roles
    from .comercial import ESTADOS_PQR, TIPOS_PQR, next_number, now_iso, pqr_row
except ImportError:
    from core import get_current_user, get_db_connection, require_roles
    from comercial import ESTADOS_PQR, TIPOS_PQR, next_number, now_iso, pqr_row

router = APIRouter(prefix='/api/pqr', tags=['pqr'])


class PqrCreate(BaseModel):
    tipo: str = 'Petición'
    asunto: str
    descripcion: str
    cliente: Optional[str] = None
    clienteEmail: Optional[str] = None


class PqrUpdate(BaseModel):
    estado: Optional[str] = None
    respuesta: Optional[str] = None


@router.post('')
@router.post('/', include_in_schema=False)
def registrar_pqr(payload: PqrCreate, usuario: dict[str, Any] = Depends(get_current_user)):
    """Cualquier usuario autenticado puede radicar una solicitud."""
    if payload.tipo not in TIPOS_PQR:
        raise HTTPException(status_code=400, detail=f'Tipo inválido. Use uno de: {", ".join(TIPOS_PQR)}.')
    if not payload.asunto.strip() or not payload.descripcion.strip():
        raise HTTPException(status_code=400, detail='El asunto y la descripción son obligatorios.')

    nombre = (payload.cliente or f"{usuario.get('name', '')} {usuario.get('last_name', '')}").strip()
    correo = (payload.clienteEmail or usuario.get('email') or '').strip()
    momento = now_iso()

    conn = get_db_connection()
    try:
        radicado = next_number(conn, 'pqr', 'PQR')
        cursor = conn.execute(
            '''
            INSERT INTO pqr (radicado, tipo, asunto, descripcion, estado, respuesta, cliente_id, cliente_nombre,
                             cliente_email, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (radicado, payload.tipo, payload.asunto.strip(), payload.descripcion.strip(), 'Pendiente', '',
             usuario.get('id'), nombre, correo, momento, momento),
        )
        conn.commit()
        fila = conn.execute('SELECT * FROM pqr WHERE id = ?', (cursor.lastrowid,)).fetchone()
        return {'message': f'Solicitud radicada con el número {radicado}.', 'pqr': pqr_row(fila)}
    finally:
        conn.close()


@router.get('')
@router.get('/', include_in_schema=False)
def listar_pqr(
    usuario: dict[str, Any] = Depends(get_current_user),
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    radicado: Optional[str] = None,
    limite: int = Query(100, ge=1, le=500),
):
    """Listado de PQR. El cliente solo consulta las que radicó."""
    filtros = ['1 = 1']
    parametros: list[Any] = []

    if estado:
        filtros.append('estado = ?')
        parametros.append(estado)
    if tipo:
        filtros.append('tipo = ?')
        parametros.append(tipo)
    if radicado:
        filtros.append('radicado LIKE ?')
        parametros.append(f'%{radicado}%')
    if usuario.get('role') == 'Cliente':
        filtros.append('cliente_id = ?')
        parametros.append(usuario.get('id'))

    conn = get_db_connection()
    try:
        filas = conn.execute(
            f'SELECT * FROM pqr WHERE {" AND ".join(filtros)} ORDER BY created_at DESC, id DESC LIMIT ?',
            (*parametros, limite),
        ).fetchall()
        return {'pqr': [pqr_row(fila) for fila in filas], 'estados': list(ESTADOS_PQR), 'tipos': list(TIPOS_PQR)}
    finally:
        conn.close()


@router.get('/{pqr_id}')
def obtener_pqr(pqr_id: int, usuario: dict[str, Any] = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        fila = conn.execute('SELECT * FROM pqr WHERE id = ?', (pqr_id,)).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail='La solicitud no existe.')
        if usuario.get('role') == 'Cliente' and fila['cliente_id'] != usuario.get('id'):
            raise HTTPException(status_code=403, detail='No tienes permisos para consultar esta solicitud.')
        return {'pqr': pqr_row(fila)}
    finally:
        conn.close()


@router.patch('/{pqr_id}', dependencies=[Depends(require_roles('Administrador', 'Empleado'))])
def gestionar_pqr(pqr_id: int, payload: PqrUpdate):
    """Actualiza el estado o la respuesta de una solicitud."""
    if payload.estado is not None and payload.estado not in ESTADOS_PQR:
        raise HTTPException(status_code=400, detail=f'Estado inválido. Use uno de: {", ".join(ESTADOS_PQR)}.')

    conn = get_db_connection()
    try:
        fila = conn.execute('SELECT * FROM pqr WHERE id = ?', (pqr_id,)).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail='La solicitud no existe.')

        estado = payload.estado or fila['estado']
        respuesta = fila['respuesta'] if payload.respuesta is None else payload.respuesta.strip()
        conn.execute(
            'UPDATE pqr SET estado = ?, respuesta = ?, updated_at = ? WHERE id = ?',
            (estado, respuesta, now_iso(), pqr_id),
        )
        conn.commit()
        actualizada = conn.execute('SELECT * FROM pqr WHERE id = ?', (pqr_id,)).fetchone()
        return {'message': 'Solicitud actualizada.', 'pqr': pqr_row(actualizada)}
    finally:
        conn.close()
