"""Esquemas Pydantic de validación de peticiones y respuestas.

Cada recurso tiene tres esquemas separados, que es lo que pide el criterio de
modelado: **Create** para el alta, **Update** para la edición (todo opcional, se
cambia solo lo que llega) y **Response** para la salida, que nunca incluye la
contraseña. Los ``Response`` se declaran en las rutas con ``response_model``, de
modo que la documentación de ``/docs`` muestra la forma exacta de la respuesta y
FastAPI filtra cualquier campo de más que venga de la base de datos.

Aquí están los de autenticación, usuarios y catálogo. Los del quinto avance
viven junto al router que los usa, para que cada módulo se lea completo:

- Ventas y pedidos del carrito: ``ventas.py`` (``VentaItem``, ``VentaCreate``,
  ``VentaEstado``, ``PedidoItem``, ``PedidoCreate``).
- Facturación: ``facturas.py`` (``FacturaCreate``, ``FacturaEstado``).
- Pasarela de pago: ``pagos.py`` (``PagoTarjeta``, ``PagoPayU``, ``PagoResponse``).
- PQR: ``pqr.py`` (``PqrCreate``, ``PqrUpdate``).
- Chatbot con IA: ``chatbot.py`` (``MensajeEntrada``).
- Recuperación de contraseña: ``recuperacion.py`` (``SolicitudRecuperacion``,
  ``CambioDeClave``).

Los modelos ORM (SQLAlchemy) de todas las entidades, incluidas las nuevas, están
en ``models.py``.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def ejemplo(valor: dict) -> ConfigDict:
    """Ejemplo que ``/docs`` muestra precargado en el cuerpo de la petición."""
    return ConfigDict(json_schema_extra={'examples': [valor]})


class UserCreateSchema(BaseModel):
    """Datos con los que un visitante crea su cuenta de cliente."""

    model_config = ejemplo({
        'name': 'Ana', 'lastName': 'Restrepo', 'documentType': 'CC',
        'documentNumber': '1035487621', 'address': 'Carrera 45 numero 12-30',
        'phone': '3001234567', 'email': 'ana.restrepo@correo.com', 'password': 'Cliente1234',
    })

    name: str = Field(min_length=2, max_length=80)
    lastName: str = Field(min_length=2, max_length=80)
    documentType: str = Field(default='CC', max_length=20)
    documentNumber: str = Field(min_length=6, max_length=12, pattern=r'^\d+$')
    address: str = Field(min_length=8, max_length=150)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def password_requires_letters_and_numbers(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError('La contraseña debe incluir letras y números.')
        return value


class UserLoginSchema(BaseModel):
    """Credenciales del inicio de sesión."""

    model_config = ejemplo({'email': 'admin@simonsc.com', 'password': 'Admin1234'})

    email: EmailStr
    # Al entrar no se valida el largo: la contraseña o es la correcta o no lo
    # es, y exigir aquí la política daría un 422 donde corresponde un 401.
    password: str


class UserUpdateSchema(BaseModel):
    """Edición de un usuario: solo se cambia lo que venga."""

    model_config = ejemplo({'name': 'Ana María', 'lastName': 'Restrepo', 'email': 'ana.restrepo@correo.com'})

    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    lastName: Optional[str] = Field(default=None, min_length=2, max_length=80)
    address: Optional[str] = Field(default=None, min_length=8, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default='Cliente', max_length=40)


class ResourceCreateSchema(BaseModel):
    """Alta de un producto o de un servicio del catálogo."""

    model_config = ejemplo({
        'name': 'Visor Nebula Quest 8',
        'description': 'Gafas de realidad virtual con seguimiento de manos.',
        'price': 3200000,
    })

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=255)
    price: float = Field(default=0, ge=0)


class ResourceUpdateSchema(BaseModel):
    """Edición de un producto o servicio: solo se cambia lo que venga."""

    model_config = ejemplo({'price': 2950000})

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    price: Optional[float] = Field(default=None, ge=0)


class ResourceStatusSchema(BaseModel):
    """Publicar o retirar del catálogo sin borrar el registro."""

    model_config = ejemplo({'active': False})

    active: bool


class AuthRecoverySchema(BaseModel):
    """Correo al que enviar el enlace para crear una contraseña nueva."""

    model_config = ejemplo({'email': 'ana.restrepo@correo.com'})

    email: EmailStr


# --- Esquemas de salida ----------------------------------------------------
# Van en ``response_model``. Ninguno expone el hash de la contraseña, aunque la
# consulta a la base de datos traiga la fila completa: FastAPI recorta lo que no
# esté declarado aquí.

class UserResponseSchema(BaseModel):
    """Un usuario tal como lo devuelve la API."""

    # Las columnas opcionales pueden venir en NULL de la base de datos; para
    # quien lee la respuesta eso es una cadena vacía, no un dato ausente.
    @field_validator('lastName', 'documentType', 'documentNumber', 'address', 'phone', mode='before')
    @classmethod
    def sin_nulos(cls, value):
        return '' if value is None else value

    id: int
    name: str
    lastName: str = ''
    email: EmailStr
    documentType: str = ''
    documentNumber: str = ''
    address: str = ''
    phone: str = ''
    role: str
    active: bool = True


class UsersResponseSchema(BaseModel):
    users: list[UserResponseSchema]


class ResourceResponseSchema(BaseModel):
    """Un producto o un servicio tal como lo devuelve la API."""

    @field_validator('description', mode='before')
    @classmethod
    def sin_nulos(cls, value):
        return '' if value is None else value

    id: int
    name: str
    description: str = ''
    price: float = 0
    active: bool = True


class ProductsResponseSchema(BaseModel):
    products: list[ResourceResponseSchema]


class ServicesResponseSchema(BaseModel):
    services: list[ResourceResponseSchema]


class ArticuloPublicoSchema(BaseModel):
    """Un artículo del catálogo público: lo justo para pintarlo y pedirlo."""

    @field_validator('description', mode='before')
    @classmethod
    def sin_nulos(cls, value):
        return '' if value is None else value

    id: int
    name: str
    description: str = ''
    price: float = 0


class CatalogResponseSchema(BaseModel):
    """Catálogo de la tienda pública, sin necesidad de sesión."""

    productos: list[ArticuloPublicoSchema]
    servicios: list[ArticuloPublicoSchema]


class RegistrationResponseSchema(BaseModel):
    """Confirmación del registro, con la cuenta recién creada."""

    message: str
    user: UserResponseSchema


class SessionResponseSchema(BaseModel):
    """Respuesta del inicio de sesión: el token y el usuario que entró."""

    token: str
    user: UserResponseSchema


class TokenResponseSchema(BaseModel):
    """Formato que espera el botón **Authorize** de ``/docs`` (OAuth2)."""

    access_token: str
    token_type: str = 'bearer'


class MessageResponseSchema(BaseModel):
    """Respuesta de las operaciones que solo confirman lo que pasó."""

    message: str


class HealthResponseSchema(BaseModel):
    """Estado de la API y motor de base de datos en uso."""

    status: str
    database: str
