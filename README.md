## Tercer avance: API y base de datos

La aplicación separa el frontend React + Vite del backend FastAPI en `backend/app/`, con base de datos SQL, hashing y autenticación JWT.

1. Inicia Apache y MySQL desde el panel de XAMPP.
2. En phpMyAdmin importa `backend/schema.sql` o ejecútalo en la pestaña SQL.
3. Copia `backend/.env.example` como `backend/.env` y ajusta `DB_PASSWORD` si tu root tiene contraseña.
4. Configura y activa el entorno virtual Python: `python -m venv .venv` y en PowerShell `.venv\Scripts\Activate.ps1`.
5. Instala las dependencias principales: `pip install -r backend/requirements.txt` (`fastapi`, `uvicorn`, `SQLAlchemy`, JWT y validación de correo).
6. Ejecuta `cd backend && python -m uvicorn app.main:app --reload --port 8000`.
7. En otra terminal ejecuta `npm run dev` desde la raíz de Vite.
8. Abre `http://localhost:5173`.

Usuarios semilla para pruebas: `admin@simonsc.com` / `Admin1234` y `empleado@simonsc.com` / `Empleado1234`. El esquema SQL está en `backend/schema.sql` y crea la base `simonsc`. Usa Postman contra `http://localhost:3001/api` para probar los endpoints protegidos con `Authorization: Bearer <token>`.

La colección importable para Postman está en `postman/SimonC-API.postman_collection.json`.
# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
