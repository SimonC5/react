# Arquitectura MVC de SimonC

Documento de referencia de cómo está organizado el proyecto y cómo se mapea
sobre el patrón MVC. Refleja la estructura real del repositorio.

## Estructura

```text
react/
  src/                      Frontend React + Vite
    components/             Vista reutilizable (botones, formularios, header, chatbot)
      charts/               Gráficos SVG propios (barras y líneas)
      panel/                Módulos del panel: ventas, facturas, reportes, PQR, analítica
    pages/                  Vista por pantalla (inicio, productos, servicios, panel, ...)
    context/                Estado de sesión (AuthContext)
    services/               Acceso a la API (api.js)
    utils/                  Formato de moneda y fechas, rutas por rol
    App.jsx                 Enrutador y composición de vistas
  backend/                  API FastAPI sobre SQLite
    main.py                 Aplicación, autenticación, usuarios, productos y servicios
    core.py                 Base de datos, JWT, roles y carga de backend/.env
    models.py / schemas.py  Modelos ORM y contratos de entrada/salida
    database.py             Creación inicial de tablas
    comercial.py            Esquema y utilidades de las tablas comerciales
    ventas.py               Ventas y detalle de ventas
    facturas.py             Facturación y descarga en PDF
    reportes.py             Reporte diario de ventas
    dashboard.py            Indicadores y series para los dashboards
    pqr.py                  Peticiones, quejas y reclamos
    chatbot.py              Atención al cliente con IA
    recuperacion.py         Recuperación de contraseña por enlace
    documentos.py           Generación de PDF y Excel
    test_api.py             Pruebas de la API
  postman/                  Colección de Postman de todos los endpoints
```

## Mapeo MVC

### Frontend React

- **Model**: `src/context` (sesión y rol) y `src/services/api.js` (acceso a datos).
- **View**: `src/pages` y `src/components`.
- **Controller**: los manejadores de eventos y la navegación dentro de cada
  página o componente.

React no implementa el MVC clásico de servidor; esta separación es la
adaptación habitual del patrón a una SPA.

### Backend FastAPI

- **Model**: `models.py`, `database.py`, `comercial.py` y las consultas SQL de
  cada módulo.
- **View**: `schemas.py` y los diccionarios de respuesta, que definen el
  contrato JSON.
- **Controller**: los endpoints de `main.py` y de cada router
  (`ventas.py`, `facturas.py`, `reportes.py`, `dashboard.py`, `pqr.py`,
  `chatbot.py`, `recuperacion.py`).

El frontend apunta a esta API mediante `VITE_API_URL`, con
`http://localhost:8000/api` por defecto.

## Base de datos

SQLite en `backend/data/simonsc.db`, creada automáticamente al arrancar. El
equivalente en MySQL para la entrega está en `backend/schema.sql`.

Tablas: `roles`, `usuarios`, `productos`, `servicios`, `ventas`,
`detalle_ventas`, `facturas`, `detalle_facturas`, `pqr`, `conversaciones`,
`mensajes` y `recuperaciones`.

## Configuración

Todas las claves y credenciales se leen de variables de entorno. `core.py`
carga `backend/.env` al arrancar, y las variables reales del sistema tienen
prioridad sobre ese archivo, que es lo que necesita el despliegue.

`backend/.env` está excluido del repositorio; la plantilla sin valores es
`backend/.env.example`. La clave del proveedor de IA (`IA_API_KEY`) nunca se
escribe en el código ni se publica.

## Roles

- **Administrador**: todo, incluida la gestión de usuarios y del catálogo de productos.
- **Empleado**: ventas, facturas, reportes, PQR y servicios.
- **Cliente**: solo sus compras, sus facturas y sus PQR.
