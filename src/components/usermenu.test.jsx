import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const usuario = { id: 3, name: 'Ana', lastName: 'Pérez', email: 'ana@simonsc.com', role: 'Cliente' };

vi.mock('../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({})),
  authApi: { me: vi.fn(() => Promise.resolve({ user: usuario })) },
  chatbotApi: { enviar: vi.fn(() => Promise.resolve({})) },
}));

const { default: UserMenu } = await import('./UserMenu');
const { AuthProvider } = await import('../context/AuthContext');

const renderUserMenu = () => {
  localStorage.setItem('simonsc_token', 'token-de-prueba');
  return render(
    <MemoryRouter>
      <AuthProvider>
        <UserMenu />
      </AuthProvider>
    </MemoryRouter>,
  );
};

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('Menú del usuario en el header', () => {
  it('muestra el nombre y abre el acceso al panel al hacer clic', async () => {
    renderUserMenu();

    const boton = await screen.findByRole('button', { name: /menú de ana/i });
    expect(screen.getByText('Ana')).not.toBeNull();
    expect(screen.queryByRole('button', { name: /entrar al panel/i })).toBeNull();

    fireEvent.click(boton);

    await waitFor(() => expect(screen.getByRole('button', { name: /entrar al panel/i })).not.toBeNull());
    expect(screen.getByText('ana@simonsc.com')).not.toBeNull();
    expect(screen.getByRole('button', { name: /cerrar sesión/i })).not.toBeNull();
  });

  it('cierra el menú con la tecla Escape', async () => {
    renderUserMenu();

    fireEvent.click(await screen.findByRole('button', { name: /menú de ana/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /entrar al panel/i })).not.toBeNull());

    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => expect(screen.queryByRole('button', { name: /entrar al panel/i })).toBeNull());
  });
});
