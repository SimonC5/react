# Arquitectura MVC de SimonC

Documento de referencia de cómo está organizado el proyecto y cómo se mapea
sobre el patrón MVC. Refleja la estructura real del repositorio.

## Estructura

```text
react/
  src/                      Frontend React + Vite
    components/             Vista reutilizable (botones, formularios, header, chatbot)
      Modal.jsx             Ventana emergente común: lleva el logo y se dibuja en el <body>
      CartButton.jsx        Carrito del sitio público
      charts/               Gráficos SVG propios (barras y líneas)
      panel/                Módulos del panel: ventas, facturas, reportes, PQR, analítica
    pages/                  Vista por pantalla (inicio, productos, servicios, panel, ...)
    context/                Estado de sesión (AuthContext) y carrito (CartContext)
    services/               Acceso a la API (api.js)
    utils/                  Formato de moneda y fechas, rutas por rol
    App.jsx                 Enrutador y composición de vistas
  backend/                  API FastAPI sobre SQLite o MySQL
    main.py                 Aplicación, autenticación, usuarios, productos y servicios
    core.py                 Base de datos (SQLite o MySQL), JWT, roles y carga de backend/.env
    models.py / schemas.py  Modelos ORM y contratos de entrada/salida
    database.py             Creación inicial de tablas
    catalogo_demo.py        Catálogo de demostración: 20 gafas VR y 20 servicios
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

El backend soporta dos motores con el mismo código, elegidos con `DB_ENGINE`
en `backend/.env`:

- **SQLite** (por defecto) en `backend/data/simonsc.db`, creada al arrancar.
- **MySQL** (el de XAMPP o el del despliegue), cuyas tablas se crean al
  arrancar a partir de `backend/schema.sql`.

`core.py` traduce el SQL de SQLite al dialecto de MySQL (`?` a `%s`,
`INSERT OR IGNORE` a `INSERT IGNORE`) y normaliza los valores que devuelve
MySQL (`Decimal` a número, `DATETIME` a texto) para que la API responda igual
con cualquiera de los dos. La única consulta escrita por separado para cada
motor es la agrupación por día, semana y mes de los Dashboards.

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
- **Cliente**: solo sus compras, sus facturas y sus PQR. No tiene dashboard.

## Panel y carrito

El panel muestra una sección a la vez: el botón del menú lateral cambia lo que
se ve, no desplaza la página. La sesión se cierra desde ese menú.

El carrito vive en el sitio público (`CartContext` + `CartButton`) y se guarda
en el navegador. El catálogo con precios reales se pide a `GET /api/catalogo`,
que es público, y el pedido se confirma con `POST /api/ventas/pedido`: el
comprador sale del token y los precios del catálogo, nunca del navegador.

Ese pedido también emite la factura (`emitir_factura_de_venta`), de modo que el
cliente la ve en "Mis facturas" sin que nadie la genere a mano. El botón
"Generar una factura" del panel sigue existiendo para las ventas que registran
el Administrador o el Empleado.

## Catálogo

`backend/catalogo_demo.py` tiene los 20 visores y los 20 servicios que la API
siembra la primera vez que arranca, y la lista de artículos del avance anterior
que quedan desactivados. Nada se borra: las ventas antiguas siguen citando esos
nombres. Quien administra ve el catálogo entero; el Cliente y la tienda pública
solo ven lo que está activo.

Las imágenes de los visores se dibujan en el propio sitio
(`src/components/VrHeadset.jsx`), sin depender de fotos externas.
