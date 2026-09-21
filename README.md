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
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` | Envío del correo de recuperación de contraseña. |

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
| Recuperación de contraseña | Enlace de un solo uso con vigencia de 60 minutos, enviado por correo. Si no hay SMTP configurado el enlace se imprime en la consola del backend, suficiente para desarrollo. El token se guarda solo como hash y nunca viaja en la respuesta de la API. |

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

Al arrancar, la API crea las tablas que falten a partir de `backend/schema.sql`
y siembra los roles, el administrador, el empleado y el catálogo. No hay que
ejecutar nada a mano en phpMyAdmin, aunque el archivo también se puede importar
desde ahí si se prefiere.

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

`railway.json` y `backend/Procfile` dejan el Backend listo para Railway con
`uvicorn main:app --host 0.0.0.0 --port $PORT`. Pasos:

1. Publica el Backend y define allí `JWT_SECRET`, `IA_API_KEY`, `FRONTEND_URL` y `CORS_ORIGINS`.
2. Publica el Frontend (`npm run build`, carpeta `dist/`) con `VITE_API_URL` apuntando a la URL
   pública de la API.
3. Verifica el flujo completo en producción y adjunta la URL pública como evidencia.
