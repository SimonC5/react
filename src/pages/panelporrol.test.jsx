import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({ products: [], services: [] })),
  authApi: { me: vi.fn(() => Promise.resolve({ user: { id: 1, name: 'Ana', role: 'Cliente' } })) },
  ventasApi: { listar: vi.fn(() => Promise.resolve({ ventas: [], resumen: { cantidad: 0, total: 0 } })) },
  pqrApi: { listar: vi.fn(() => Promise.resolve({ pqr: [] })) },
  facturasApi: { listar: vi.fn(() => Promise.resolve({ facturas: [] })) },
  reportesApi: { diario: vi.fn(() => Promise.resolve({ reporte: { fecha: '2026-09-22', filas: [], totales: {} } })) },
  dashboardApi: {
    resumen: vi.fn(() => Promise.resolve({ tarjetas: [], pqrPorEstado: [] })),
    ventas: vi.fn(() => Promise.resolve({ barras: [], lineal: [], topItems: [], totales: { ventas: 0, monto: 0 } })),
    filtros: vi.fn(() => Promise.resolve({ productos: [], servicios: [], clientes: [], estadosVenta: [] })),
  },
}));

const { MemoryRouter } = await import('react-router-dom');
const { authApi } = await import('../services/api');
const { AuthProvider } = await import('../context/AuthContext');
const { default: DashboardPage } = await import('./DashboardPage');

afterEach(() => {
  cleanup();
  localStorage.clear();
});

/** Entra al panel con el rol pedido y espera a que cargue el menú. */
async function abrirPanelComo(role) {
  authApi.me.mockResolvedValue({ user: { id: 1, name: 'Ana', role } });
  localStorage.setItem('simonsc_token', 'token-de-prueba');
  render(
    <MemoryRouter>
      <AuthProvider>
        <DashboardPage role={role} />
      </AuthProvider>
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getByRole('button', { name: /PQR/i })).not.toBeNull());
}

const enElMenu = (texto) => screen.queryByRole('button', { name: texto });

describe('Qué ve cada rol en el panel', () => {
  it('el administrador tiene dashboard, catálogo y usuarios', async () => {
    await abrirPanelComo('Administrador');

    expect(enElMenu(/^dashboard$/i)).not.toBeNull();
    expect(enElMenu(/^productos$/i)).not.toBeNull();
    expect(enElMenu(/^servicios$/i)).not.toBeNull();
    expect(enElMenu(/^usuarios$/i)).not.toBeNull();
  });

  it('el empleado opera pero no entra al dashboard', async () => {
    await abrirPanelComo('Empleado');

    expect(enElMenu(/^dashboard$/i)).toBeNull();
    expect(enElMenu(/^usuarios$/i)).toBeNull();
    // Lo suyo sigue estando: ventas, facturación, reportes y el catálogo.
    expect(enElMenu(/^ventas$/i)).not.toBeNull();
    expect(enElMenu(/^reportes$/i)).not.toBeNull();
    expect(enElMenu(/^productos$/i)).not.toBeNull();
  });

  it('el cliente solo ve lo suyo, sin catálogo dentro del panel', async () => {
    await abrirPanelComo('Cliente');

    expect(enElMenu(/^dashboard$/i)).toBeNull();
    expect(enElMenu(/^productos$/i)).toBeNull();
    expect(enElMenu(/^servicios$/i)).toBeNull();
    expect(enElMenu(/^reportes$/i)).toBeNull();
    expect(enElMenu(/^mis compras$/i)).not.toBeNull();
    expect(enElMenu(/^mis facturas$/i)).not.toBeNull();
  });
});
