# FastAPI frente a Django REST Framework en SimonC Realidad Virtual

Análisis del porqué de la tecnología elegida para el backend de este proyecto,
contrastando FastAPI con la alternativa más habitual en Python, Django REST
Framework (DRF). No es una comparación en abstracto: cada punto se apoya en
código que está en este repositorio.

## Resumen

| Aspecto | FastAPI (lo elegido) | Django REST Framework |
| --- | --- | --- |
| Validación de datos | Pydantic v2, con los tipos de Python | `Serializer` propios de DRF |
| Documentación | OpenAPI automática en `/docs` y `/redoc` | Requiere `drf-spectacular` o similar |
| Asincronía | Nativa (`async def`, ASGI) | Parcial; el ORM sigue siendo síncrono |
| ORM | Libre; aquí SQLAlchemy 2.0 | Django ORM, obligatorio |
| Panel de administración | No trae | `django.contrib.admin`, listo para usar |
| Autenticación | Se arma (aquí, JWT propio) | Incluida, con sesiones y permisos |
| Tamaño del proyecto | Mínimo: solo lo que se usa | Estructura completa desde el inicio |

## Por qué FastAPI en este proyecto

**La validación son los mismos tipos de Python.** En `backend/schemas.py` un
esquema declara el contrato y la validación a la vez:

```python
class UserCreateSchema(BaseModel):
    documentNumber: str = Field(min_length=6, max_length=12, pattern=r'^\d+$')
    password: str = Field(min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def password_requires_letters_and_numbers(cls, value: str) -> str:
        ...
```

En DRF lo equivalente es un `serializers.Serializer` con sus campos y sus
métodos `validate_<campo>`. Funciona igual de bien, pero es una jerarquía de
clases propia del framework: lo que se aprende ahí no se reutiliza fuera. Los
esquemas de Pydantic son objetos de Python corrientes, y el editor los
autocompleta porque son anotaciones de tipo normales.

**La documentación sale sola.** `/docs` y `/redoc` se generan del mismo código,
con los `summary`, las descripciones, los ejemplos y el botón **Authorize** que
declaran las rutas de `backend/main.py`. En DRF hay que instalar y configurar
`drf-spectacular` para llegar a algo parecido, y mantener la documentación
alineada a mano cuando cambia un serializer.

**El frontend no es de Django.** La vista de este proyecto es React + Vite
(`src/`), que se publica como sitio estático aparte. Media parte de Django
—plantillas, formularios, `django.contrib.admin`, el sistema de sesiones— no se
usaría, y aun así habría que arrastrarla, configurarla y desplegarla. FastAPI
trae solo la capa HTTP.

**Asincronía real.** `GET /api/catalogo` y `GET /api/health` son `async def`.
El catálogo es el endpoint más visitado, porque lo pide cualquier visitante sin
haber iniciado sesión; como el controlador de la base de datos es bloqueante, la
consulta se manda a otro hilo con `asyncio.to_thread` y el bucle de eventos
queda libre para atender a los demás. El envío del correo de recuperación va por
`BackgroundTasks` (`backend/recuperacion.py`), de modo que la respuesta sale sin
esperar al proveedor. Django admite vistas `async` desde la versión 3.1, pero su
ORM sigue siendo síncrono, así que en la práctica la ganancia es menor sin
reescribir el acceso a datos.

**El ORM se elige aparte.** Aquí conviven dos formas de hablar con la base:
`backend/models.py` declara el modelo relacional con SQLAlchemy 2.0 (`Mapped`,
`mapped_column`, `relationship`), y el resto del backend consulta con SQL
directo a través de `backend/core.py`, que traduce la misma sentencia a SQLite o
a MySQL. Eso permite que el proyecto corra sobre el XAMPP del aprendiz y sobre
el SQLite del servidor sin cambiar una línea. Con Django el ORM no es opcional y
cambiar de motor pasa por su capa de migraciones.

## Dónde habría ganado Django REST Framework

Ser honesto con la comparación también es parte del análisis:

- **Panel de administración gratis.** `django.contrib.admin` habría dado el CRUD
  de usuarios, productos y servicios sin escribirlo. Aquí ese panel es código
  propio: `src/pages/DashboardPage.jsx` y los endpoints de `backend/main.py`.
- **Autenticación y permisos incluidos.** DRF trae usuarios, grupos y permisos.
  En este proyecto el JWT, los roles y el `require_roles` están escritos a mano
  en `backend/core.py`.
- **Migraciones.** `makemigrations` / `migrate` es más completo que crear las
  tablas al arrancar, que es lo que hace `init_db()` en `backend/main.py`.
- **Convención sobre configuración.** En un equipo grande, que todos los
  proyectos Django se parezcan tiene un valor que un proyecto FastAPI, que cada
  uno organiza a su manera, no da.

## Conclusión

Para una API que sirve a un frontend React, que debe documentarse sola para la
sustentación y que corre en un plan gratuito con recursos limitados, FastAPI
pesa menos y entrega más rápido lo que este proyecto necesita. Django REST
Framework habría sido la mejor elección si el proyecto hubiera necesitado
también las pantallas de administración, o si el equipo ya tuviera otros
proyectos en Django con los que compartir convenciones.
