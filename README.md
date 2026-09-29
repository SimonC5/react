# SimonC — Quinto avance (React + Vite → FastAPI → Base de datos SQL)

Aplicación Full Stack de la agencia SimonC. El Frontend es React 19 + Vite + Tailwind 4 y el
Backend es FastAPI con base de datos SQL, autenticación JWT y roles. El quinto avance añade
gestión comercial, reportes, Dashboards, PQR y un chatbot con Inteligencia Artificial.

## Cómo ejecutar el proyecto

1. Crea y activa el entorno virtual de Python:
   `python -m venv .venv` y en PowerShell `.venv\Scripts\Activate.ps1` (en Linux/macOS `source .venv/bin/activate`).
2. Instala las dependencias del Backend: `pip install -r backend/requirements.txt`.
3. Copia `backend/.env.example` como `backend/.env` y ajusta los valores (ver *Variables de entorno*).
4. Levanta la API: `cd backend && python -m uvicorn main:app --reload --port 8000`.
   La base SQLite `backend/data/simonsc.db` se crea sola con las tablas y los datos iniciales.
5. En otra terminal, desde la raíz: `npm install` y `npm run dev`.
6. Abre `http://localhost:5173`. La documentación interactiva de la API está en `http://localhost:8000/docs`.

Usuarios de prueba: `admin@simonsc.com` / `Admin1234` y `empleado@simonsc.com` / `Empleado1234`.
Cualquier persona puede registrarse desde el sitio y queda con el rol Cliente.

En `/docs`, el botón **Authorize** inicia sesión con esas mismas cuentas (el correo va en el
campo `username`) y deja todas las peticiones de la página firmadas con el token.

## Documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — cómo está organizado el proyecto y su mapeo MVC.
- [`docs/comparativa-fastapi-django-rest.md`](docs/comparativa-fastapi-django-rest.md) — por qué
  FastAPI y no Django REST Framework, con el código del proyecto como ejemplo.

## Variables de entorno

Raíz (`.env`, a partir de `.env.example`):

| Variable | Para qué sirve |
| --- | --- |
| `VITE_API_URL` | URL de la API que consume el Frontend. |
| `VITE_WHATSAPP_NUMBER` | Número del botón de WhatsApp. |

Backend (`backend/.env`, a partir de `backend/.env.example`):

| Variable | Para qué sirve |
| --- | --- |
| `DB_ENGINE` | `sqlite` (por defecto) o `mysql`. |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Datos del MySQL cuando `DB_ENGINE=mysql`. |
| `DATABASE_URL` | Alternativa de una línea: `mysql://usuario:clave@host:3306/simonsc`. |
| `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRES_IN` | Firma y vigencia de los tokens. |
| `FRONTEND_URL`, `CORS_ORIGINS` | Dominios autorizados por CORS en producción. |
| `IA_API_KEY` | Clave del proveedor de IA que usa el chatbot. |
| `IA_API_URL`, `IA_MODEL`, `IA_TIMEOUT` | Endpoint, modelo y tiempo de espera del proveedor. |
| `EMAIL_API_KEY`, `EMAIL_FROM` | Envío de correo por API web. Es la forma recomendada y **la única que funciona en el plan gratuito de Render**, que bloquea la salida a los puertos de SMTP. La clave sale de una cuenta gratuita de [Brevo](https://www.brevo.com) (SMTP & API → API Keys) y `EMAIL_FROM` es el correo verificado allí. |
| `SMTP_USER`, `SMTP_PASSWORD` | Envío por SMTP, para el computador propio o un plan de pago. Con Gmail, Outlook o Yahoo no hace falta nada más: el servidor se deduce del dominio. Con Gmail la contraseña es una **contraseña de aplicación** de 16 letras ([myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)), no la de la cuenta. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USE_TLS`, `SMTP_USE_SSL` | Opcionales, solo para un proveedor que no sea de los conocidos. |

`backend/core.py` carga `backend/.env` al arrancar, así que basta con escribir las variables
en ese archivo. Las variables reales del entorno tienen prioridad, que es lo que usa el despliegue.

La API Key **nunca** se publica en GitHub ni se escribe en el código: se lee de `backend/.env`,
que está en `.gitignore`, y en producción se configura como variable de entorno del servicio.
Si no hay clave configurada, el chatbot sigue respondiendo con la información real del catálogo.

## Módulos del quinto avance

| Área | Qué hace |
| --- | --- |
| Ventas | Registro de ventas desde el sitio con productos y servicios, detalle por línea, descuentos e IVA, e historial filtrable por fecha, cliente, producto, servicio, estado y valor. |
| Reportes | Reporte diario de ventas en pantalla y exportable a PDF y a Excel (`.xlsx`). |
| Facturación | Generación de la factura a partir de una venta, consulta por número, cliente, estado o fecha, y descarga en PDF. |
| Dashboards | Cards de indicadores, gráfico de barras y gráfico lineal por día, semana o mes, con filtros y diferenciados por rol. |
| PQR | Radicación y seguimiento de peticiones, quejas y reclamos con estados Pendiente, En proceso, Respondida y Cerrada. |
| Chatbot | Asistente en el sitio que responde a través de FastAPI usando el servicio de IA configurado. |
| Pasarela de pago | El carrito registra el pedido y después cobra, con un formulario dentro del propio sitio: **tarjeta** (validada con Luhn), **PSE** eligiendo banco, y **efectivo** con un código para Efecty o Baloto. Un pago aprobado deja la venta y su factura en Pagada; uno rechazado dice por qué y la compra se puede volver a pagar desde *Mis compras*; el de efectivo queda Pendiente hasta que entre el dinero. De la tarjeta solo se guardan la franquicia y los cuatro últimos dígitos. |
| Recuperación de contraseña | Enlace de un solo uso con vigencia de 60 minutos, enviado por correo en texto y HTML. Si no hay SMTP configurado el enlace se imprime en la consola del backend y la pantalla lo dice, en vez de prometer un correo que no sale. El token se guarda solo como hash y nunca viaja en la respuesta de la API. |
| Servidor de correo | El administrador ve en el panel (Dashboard → Servidor de correo) si está configurado, por dónde salen los correos, qué falta si no, y puede enviarse un correo de prueba. Avisa aparte si está configurado por SMTP corriendo en Render, donde el plan gratuito lo bloquea. |

Los Dashboards no tienen datos escritos a mano: React consume los endpoints de FastAPI y
FastAPI calcula los indicadores y las series con consultas a la base de datos.

## Endpoints nuevos

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/api/ventas` | Registra una venta con su detalle. |
| GET | `/api/ventas` | Historial con filtros. |
| GET | `/api/ventas/{id}` | Venta y su detalle. |
| PATCH | `/api/ventas/{id}/estado` | Cambia el estado de la venta. |
| GET | `/api/reportes/ventas/diario` | Reporte diario en JSON. |
| GET | `/api/reportes/ventas/diario.pdf` | Reporte diario en PDF. |
| GET | `/api/reportes/ventas/diario.xlsx` | Reporte diario en Excel. |
| POST | `/api/facturas` | Genera la factura de una venta. |
| GET | `/api/facturas` | Consulta de facturas con filtros. |
| GET | `/api/facturas/{id}` | Factura y su detalle. |
| GET | `/api/facturas/{id}/pdf` | Descarga la factura en PDF. |
| PATCH | `/api/facturas/{id}/estado` | Cambia el estado de la factura. |
| GET | `/api/dashboard/resumen` | Indicadores tipo Card según el rol. |
| GET | `/api/dashboard/ventas` | Series para los gráficos, con filtros. |
| GET | `/api/dashboard/filtros` | Valores disponibles para los selectores. |
| POST | `/api/pqr` | Radica una solicitud. |
| GET | `/api/pqr` | Lista y filtra solicitudes. |
| GET | `/api/pqr/{id}` | Consulta una solicitud. |
| PATCH | `/api/pqr/{id}` | Actualiza estado y respuesta. |
| POST | `/api/chatbot/mensajes` | Envía un mensaje y devuelve la respuesta. |
| GET | `/api/chatbot/conversaciones` | Conversaciones del usuario. |
| GET | `/api/chatbot/conversaciones/{id}` | Mensajes de una conversación. |
| GET | `/api/chatbot/estado` | Indica si hay servicio de IA configurado. |
| GET | `/api/pagos/config` | Medios de pago, bancos, puntos de pago y tarjetas de prueba. |
| POST | `/api/pagos` | Cobra una venta con el medio elegido. |
| GET | `/api/pagos` | Historial de pagos, filtrable por estado y referencia. |
| GET | `/api/pagos/{id}` | Detalle de un pago. |

Todos requieren `Authorization: Bearer <token>`. Los reportes y el registro de ventas son de
Administrador y Empleado; un Cliente solo ve sus propias ventas, facturas y PQR.

## Base de datos

El backend funciona con dos motores y el mismo código. Se elige en `backend/.env`.

**SQLite (por defecto).** No hay nada que instalar: la base se crea sola en
`backend/data/simonsc.db` la primera vez que arranca la API.

**MySQL (XAMPP).** En el panel de XAMPP arranca *MySQL* y luego pon en `backend/.env`:

```
DB_ENGINE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=simonsc
DB_USER=root
DB_PASSWORD=
```

Al arrancar, la API crea la base si no existe y dentro las tablas que falten, a
partir de `backend/schema.sql`, y siembra los roles, el administrador, el
empleado y el catálogo. No hay que crear ni importar nada a mano en phpMyAdmin,
aunque el archivo también se puede importar desde ahí si se prefiere.

Lo único que cambia entre los dos motores es la forma de agrupar por día,
semana y mes en los Dashboards (`backend/dashboard.py`); el resto del SQL se
escribe una sola vez y `backend/core.py` lo traduce.

### Diagrama de relaciones

Las 14 tablas son InnoDB y llevan sus claves foráneas con nombre
(`fk_ventas_cliente`, `fk_detalle_ventas_venta`, …), así que el **Diseñador**
de phpMyAdmin dibuja las 12 relaciones solo: entra a la base `simonsc` y abre
la pestaña *Diseñador*.

La única relación que no aparece es `detalle_ventas.item_id`, porque apunta a
`productos` o a `servicios` según el valor de `item_tipo` y MySQL no admite una
clave foránea con dos destinos posibles.

Para que además salgan **colocadas** y no amontonadas, ejecuta una vez
`backend/designer_layout.sql` desde la pestaña SQL de phpMyAdmin. Deja las
tablas en columnas de izquierda a derecha siguiendo las dependencias. Se puede
repetir sin problema: rehace la distribución desde cero.


Tablas del quinto avance: `ventas`, `detalle_ventas`, `facturas`, `detalle_facturas`, `pqr`,
`conversaciones` y `mensajes`, además de las de los avances anteriores. El script SQL completo
está en `backend/schema.sql`. En desarrollo la API usa SQLite y crea todo automáticamente.

## Pruebas

- Frontend: `npm test` (Vitest).
- Backend: `pip install -r backend/requirements-dev.txt` y `python -m pytest backend`.
  Las pruebas corren sobre una base temporal y cubren ventas, reportes PDF/Excel, facturación,
  Dashboards, PQR, chatbot, recuperación de contraseña y permisos por rol.
  La misma suite pasa con los dos motores: `python -m pytest backend` usa SQLite y
  `DB_ENGINE=mysql DB_NAME=simonsc_test python -m pytest backend` usa MySQL.
- Postman: importa `postman/SimonC-API.postman_collection.json`, ejecuta *Login JWT*, copia el
  token en la variable `token` y prueba los grupos Ventas, Reportes, Facturación, Dashboards,
  PQR y Chatbot con IA.
- Calidad: `npm run lint` y `npm run build`.

## Despliegue

El proyecto trae la configuración lista para dos plataformas gratuitas:

- **Render** (`render.yaml`): un solo repositorio, dos servicios (la API en Python y
  el Frontend estático), **ya enlazados entre sí**: Render inyecta el dominio de
  cada servicio en el otro, así que no hay que copiar URLs a mano. Es el camino
  recomendado.
- **Railway** (`railway.json`, `backend/Procfile`): para el Backend, con
  `uvicorn main:app --host 0.0.0.0 --port $PORT`.

El Frontend es una SPA, así que necesita reenviar cualquier ruta a `index.html`.
Eso ya está resuelto: `public/_redirects` (Netlify/Render estático) y `vercel.json`
(Vercel). Sin esto, recargar en `/panel/admin` daría 404.

Pasos:

1. Publica el Backend y define allí `JWT_SECRET`, `IA_API_KEY`, `FRONTEND_URL` y
   `CORS_ORIGINS`. La clave de IA se escribe solo en el panel del proveedor de
   hosting, nunca en el repositorio.
2. Publica el Frontend con `VITE_API_URL` apuntando a la URL pública de la API.
3. Verifica el flujo completo en producción y adjunta la URL pública como evidencia.

`VITE_API_URL` y los orígenes de CORS se normalizan, así que sirven tal como se
copian del panel del hosting: con o sin `https://`, con o sin `/api` y con o sin
barra al final. Es el error más fácil de cometer y el que menos se diagnostica,
porque el síntoma es que todo falla sin explicación.
