import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const usuario = { id: 1, name: 'Admin', lastName: 'SimonC', email: 'admin@simonsc.com', role: 'Administrador' };

vi.mock('../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({})),
  authApi: { me: vi.fn(() => Promise.resolve({ user: usuario })) },
  catalogoApi: { publico: vi.fn(() => Promise.resolve({ products: [], services: [] })) },
  chatbotApi: { enviar: vi.fn(() => Promise.resolve({})) },
}));

const { default: Header } = await import('./Header');
const { AuthProvider } = await import('../context/AuthContext');
const { CartProvider } = await import('../context/CartContext');

const renderHeader = (ruta) => {
  localStorage.setItem('simonsc_token', 'token-de-prueba');
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <AuthProvider>
        <CartProvider>
          <Header />
        </CartProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
};

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('Logo del encabezado', () => {
  it('lo muestra en el sitio público', async () => {
    renderHeader('/');
    await waitFor(() => expect(screen.getByAltText(/logo simonc/i)).not.toBeNull());
  });

  it('no lo repite dentro del panel, porque ya está en la barra lateral', async () => {
    renderHeader('/panel/admin');
    // El menú del usuario sí tiene que seguir estando.
    await waitFor(() => expect(screen.getByRole('button', { name: /menú de admin/i })).not.toBeNull());
    expect(screen.queryByAltText(/logo simonc/i)).toBeNull();
  });
});
