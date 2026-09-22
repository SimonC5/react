import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const usuario = { id: 5, name: 'Ana', lastName: 'Pérez', email: 'ana@simonsc.com', role: 'Cliente' };

const catalogo = {
  productos: [{ id: 1, name: 'Branding Premium', description: 'Identidad visual.', price: 850000 }],
  servicios: [],
};

const pedido = vi.fn(() => Promise.resolve({ message: 'Pedido registrado correctamente.', venta: { numero: 'VT-0001' } }));

vi.mock('../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({})),
  authApi: { me: vi.fn(() => Promise.resolve({ user: usuario })) },
  catalogoApi: { publico: vi.fn(() => Promise.resolve(catalogo)) },
  ventasApi: { pedido },
  chatbotApi: { enviar: vi.fn(() => Promise.resolve({})) },
}));

const { default: CartButton } = await import('./CartButton');
const { default: ProductsPage } = await import('../pages/ProductsPage');
const { AuthProvider } = await import('../context/AuthContext');
const { CartProvider } = await import('../context/CartContext');

const renderTienda = () => {
  localStorage.setItem('simonsc_token', 'token-de-prueba');
  return render(
    <MemoryRouter>
      <AuthProvider>
        <CartProvider>
          <CartButton />
          <ProductsPage />
        </CartProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
};

afterEach(() => {
  cleanup();
  localStorage.clear();
  pedido.mockClear();
});

describe('Carrito de compras', () => {
  it('agrega un producto del catálogo y confirma el pedido', async () => {
    renderTienda();

    fireEvent.click(await screen.findByRole('button', { name: /agregar al carrito/i }));

    const boton = screen.getByRole('button', { name: /carrito, 1 artículo/i });
    fireEvent.click(boton);

    // La ventana del carrito lleva el logo, como todas las emergentes.
    const ventana = await screen.findByRole('dialog');
    expect(ventana.querySelector('img[alt="Logo SimonC"]')).not.toBeNull();
    expect(screen.getAllByText('Branding Premium').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: /confirmar pedido/i }));

    await waitFor(() => expect(pedido).toHaveBeenCalledWith({ items: [{ tipo: 'producto', itemId: 1, cantidad: 1 }] }));
    await waitFor(() => expect(screen.getByText(/VT-0001/)).not.toBeNull());
  });

  it('guarda el carrito en el navegador para que sobreviva a una recarga', async () => {
    renderTienda();

    fireEvent.click(await screen.findByRole('button', { name: /agregar al carrito/i }));

    await waitFor(() => {
      const guardado = JSON.parse(localStorage.getItem('simonsc_carrito') || '[]');
      expect(guardado).toHaveLength(1);
      expect(guardado[0]).toMatchObject({ tipo: 'producto', id: 1, cantidad: 1 });
    });
  });
});
