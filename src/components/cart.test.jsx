import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const usuario = { id: 5, name: 'Ana', lastName: 'Pérez', email: 'ana@simonsc.com', role: 'Cliente' };

const catalogo = {
  productos: [{ id: 1, name: 'SimonC Vision One', description: 'Gafas VR autónomas.', price: 850000 }],
  servicios: [],
};

const pedido = vi.fn(() => Promise.resolve({
  message: 'Pedido registrado correctamente.',
  venta: { id: 7, numero: 'VT-0001', subtotal: 850000, impuestos: 161500, total: 1011500 },
  factura: { id: 3, numero: 'FV-0001' },
}));

const pagar = vi.fn(() => Promise.resolve({
  message: 'Transacción aprobada.',
  pago: {
    referencia: 'PG-000001', estado: 'Aprobado', monto: 1011500,
    metodo: 'tarjeta', entidad: 'Visa', ultimosDigitos: '1111',
  },
  venta: { numero: 'VT-0001', estado: 'Pagada' },
}));

const configDePagos = {
  metodos: ['tarjeta', 'pse', 'efectivo'],
  bancos: ['Bancolombia', 'Nequi'],
  puntosDePago: ['Efecty', 'Baloto'],
  tiposDeDocumento: ['CC', 'CE'],
  tarjetasDePrueba: [],
};

vi.mock('../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({})),
  authApi: { me: vi.fn(() => Promise.resolve({ user: usuario })) },
  catalogoApi: { publico: vi.fn(() => Promise.resolve(catalogo)) },
  ventasApi: { pedido },
  pagosApi: {
    config: vi.fn(() => Promise.resolve(configDePagos)),
    pagar,
  },
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
  pagar.mockClear();
});

describe('Carrito de compras', () => {
  it('agrega un producto del catálogo y lo lleva a la pasarela de pago', async () => {
    renderTienda();

    fireEvent.click(await screen.findByRole('button', { name: /agregar al carrito/i }));

    const boton = screen.getByRole('button', { name: /carrito, 1 artículo/i });
    fireEvent.click(boton);

    // La ventana del carrito lleva el logo, como todas las emergentes.
    const ventana = await screen.findByRole('dialog');
    expect(ventana.querySelector('img[alt="Logo SimonC"]')).not.toBeNull();
    expect(screen.getAllByText('SimonC Vision One').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: /ir a pagar/i }));

    await waitFor(() => expect(pedido).toHaveBeenCalledWith({ items: [{ tipo: 'producto', itemId: 1, cantidad: 1 }] }));

    // El pedido queda registrado y el carrito da paso a la pasarela de pago.
    await waitFor(() => expect(screen.getByText(/Compra VT-0001/)).not.toBeNull());
    expect(screen.getByText(/Total a pagar/)).not.toBeNull();

    // El formulario abre en tarjeta, que es el medio más usado.
    fireEvent.change(screen.getByLabelText(/nombre del titular/i), { target: { value: 'ANA PEREZ' } });
    fireEvent.change(screen.getByLabelText(/número de la tarjeta/i), { target: { value: '4111111111111111' } });
    fireEvent.change(screen.getByLabelText(/^vence$/i), { target: { value: '1230' } });
    fireEvent.change(screen.getByLabelText(/^código$/i), { target: { value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: /^pagar /i }));

    // El número de la tarjeta sale agrupado en pantalla, pero se manda limpio.
    await waitFor(() => expect(pagar).toHaveBeenCalledWith(expect.objectContaining({
      ventaId: 7, metodo: 'tarjeta', nombre: 'ANA PEREZ', numero: '4111111111111111',
      vencimiento: '12/30', cvv: '123', cuotas: 1,
    })));
    await waitFor(() => expect(screen.getByText(/Pago aprobado/)).not.toBeNull());
    expect(screen.getByText('PG-000001')).not.toBeNull();
    // La factura que salió con el pedido queda pagada.
    expect(screen.getByText(/FV-0001/)).not.toBeNull();
  });

  it('avisa cuando la tarjeta se rechaza y deja intentarlo otra vez', async () => {
    pagar.mockResolvedValueOnce({
      message: 'Fondos insuficientes.',
      pago: {
        referencia: 'PG-000002', estado: 'Rechazado', monto: 1011500,
        metodo: 'tarjeta', entidad: 'Visa', ultimosDigitos: '0000',
      },
      venta: { numero: 'VT-0001', estado: 'Registrada' },
    });
    renderTienda();

    fireEvent.click(await screen.findByRole('button', { name: /agregar al carrito/i }));
    fireEvent.click(screen.getByRole('button', { name: /carrito, 1 artículo/i }));
    await screen.findByRole('dialog');
    fireEvent.click(screen.getByRole('button', { name: /ir a pagar/i }));
    await waitFor(() => expect(screen.getByText(/Compra VT-0001/)).not.toBeNull());

    fireEvent.change(screen.getByLabelText(/nombre del titular/i), { target: { value: 'ANA PEREZ' } });
    fireEvent.change(screen.getByLabelText(/número de la tarjeta/i), { target: { value: '4000000200000000' } });
    fireEvent.change(screen.getByLabelText(/^vence$/i), { target: { value: '1230' } });
    fireEvent.change(screen.getByLabelText(/^código$/i), { target: { value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: /^pagar /i }));

    // Se dice el motivo y la compra sigue sin pagar, con opción de reintentar.
    await waitFor(() => expect(screen.getByText(/Fondos insuficientes/)).not.toBeNull());
    expect(screen.getByText(/Pago rechazado/)).not.toBeNull();
    expect(screen.getByRole('button', { name: /intentar de nuevo/i })).not.toBeNull();
  });

  it('cambia de medio de pago sin salir de la ventana', async () => {
    renderTienda();

    fireEvent.click(await screen.findByRole('button', { name: /agregar al carrito/i }));
    fireEvent.click(screen.getByRole('button', { name: /carrito, 1 artículo/i }));
    await screen.findByRole('dialog');
    fireEvent.click(screen.getByRole('button', { name: /ir a pagar/i }));
    await waitFor(() => expect(screen.getByText(/Compra VT-0001/)).not.toBeNull());

    // PSE pide banco y documento, no tarjeta.
    fireEvent.click(screen.getByRole('button', { name: /^pse$/i }));
    await waitFor(() => expect(screen.getByLabelText(/^banco$/i)).not.toBeNull());
    expect(screen.queryByLabelText(/número de la tarjeta/i)).toBeNull();
    fireEvent.change(screen.getByLabelText(/^banco$/i), { target: { value: 'Bancolombia' } });
    fireEvent.change(screen.getByLabelText(/número de documento/i), { target: { value: '1035487621' } });
    fireEvent.click(screen.getByRole('button', { name: /^pagar /i }));

    await waitFor(() => expect(pagar).toHaveBeenCalledWith(expect.objectContaining({
      ventaId: 7, metodo: 'pse', banco: 'Bancolombia', tipoDocumento: 'CC', documento: '1035487621',
    })));
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
