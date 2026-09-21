import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({ products: [], services: [] })),
  authApi: { me: vi.fn(() => Promise.resolve({ user: { id: 1, name: 'Ana', role: 'Cliente' } })) },
  ventasApi: { listar: vi.fn(() => Promise.resolve({ ventas: [], resumen: { cantidad: 0, total: 0 } })) },
  pqrApi: {
    listar: vi.fn(() => Promise.resolve({ pqr: [] })),
    crear: vi.fn(() => Promise.resolve({ message: 'Solicitud radicada con el número PQR-000001.' })),
    gestionar: vi.fn(() => Promise.resolve({})),
  },
  chatbotApi: {
    enviar: vi.fn(() => Promise.resolve({ conversacionId: 7, respuesta: 'Puedes radicar una PQR desde tu panel.' })),
  },
  facturasApi: { listar: vi.fn(() => Promise.resolve({ facturas: [] })) },
  reportesApi: { diario: vi.fn(() => Promise.resolve({ reporte: { fecha: '2026-09-21', filas: [], totales: {} } })) },
  dashboardApi: {
    resumen: vi.fn(() => Promise.resolve({ tarjetas: [], pqrPorEstado: [] })),
    ventas: vi.fn(() => Promise.resolve({ barras: [], lineal: [], topItems: [], totales: { ventas: 0, monto: 0 } })),
    filtros: vi.fn(() => Promise.resolve({ productos: [], servicios: [], clientes: [], estadosVenta: [] })),
  },
}));

const { chatbotApi, pqrApi } = await import('../../services/api');
const { default: PqrModule } = await import('./PqrModule');
const { default: Chatbot } = await import('../Chatbot');
const { AuthProvider } = await import('../../context/AuthContext');

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('Módulo de PQR', () => {
  beforeEach(() => {
    pqrApi.crear.mockClear();
  });

  it('radica una solicitud y muestra el número de radicado', async () => {
    render(<PqrModule puedeGestionar={false} />);

    fireEvent.change(screen.getByLabelText(/asunto/i), { target: { value: 'Demora en la entrega' } });
    fireEvent.change(screen.getByLabelText(/descripción/i), { target: { value: 'El pedido llegó tarde.' } });
    fireEvent.click(screen.getByRole('button', { name: /radicar solicitud/i }));

    await waitFor(() => expect(screen.getByText(/PQR-000001/)).not.toBeNull());
    expect(pqrApi.crear).toHaveBeenCalledWith({
      tipo: 'Petición',
      asunto: 'Demora en la entrega',
      descripcion: 'El pedido llegó tarde.',
    });
  });

  it('solo ofrece los botones de gestión a administrador y empleado', () => {
    render(<PqrModule puedeGestionar={false} />);

    expect(screen.queryByRole('button', { name: /^en proceso$/i })).toBeNull();
  });
});

describe('Chatbot de atención al cliente', () => {
  const renderChatbot = () => {
    localStorage.setItem('simonsc_token', 'token-de-prueba');
    return render(
      <AuthProvider>
        <Chatbot />
      </AuthProvider>,
    );
  };

  it('envía la pregunta al backend y muestra la respuesta del asistente', async () => {
    renderChatbot();

    await waitFor(() => expect(screen.getByRole('button', { name: /abrir el asistente virtual/i })).not.toBeNull());
    fireEvent.click(screen.getByRole('button', { name: /abrir el asistente virtual/i }));

    fireEvent.change(screen.getByLabelText(/mensaje para el asistente/i), { target: { value: 'Quiero poner una queja' } });
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }));

    await waitFor(() => expect(screen.getByText(/radicar una PQR desde tu panel/i)).not.toBeNull());
    expect(chatbotApi.enviar).toHaveBeenCalledWith('Quiero poner una queja', null);
  });
});
