import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EmailModule from './EmailModule';
import RecoverPassword from '../RecoverPassword';
import { authApi } from '../../services/api';

vi.mock('../../services/api', () => ({
  apiRequest: vi.fn(() => Promise.resolve({})),
  authApi: {
    correoEstado: vi.fn(),
    probarCorreo: vi.fn(),
    recover: vi.fn(),
  },
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('Servidor de correo en el panel del administrador', () => {
  it('cuando falta configurarlo dice qué falta y cómo hacerlo', async () => {
    authApi.correoEstado.mockResolvedValue({
      configurado: false,
      motivo: 'Falta SMTP_PASSWORD.',
      servidor: '',
      remitente: '',
    });

    render(<EmailModule />);

    expect(await screen.findByText(/sin configurar/i)).not.toBeNull();
    expect(screen.getByText(/falta smtp_password/i)).not.toBeNull();
    expect(screen.getByText(/contraseña de aplicación/i)).not.toBeNull();
  });

  it('cuando está configurado muestra desde dónde salen los correos', async () => {
    authApi.correoEstado.mockResolvedValue({
      configurado: true,
      motivo: '',
      servidor: 'smtp.gmail.com:587',
      remitente: 'SimonC Realidad Virtual <tienda@gmail.com>',
    });

    render(<EmailModule />);

    expect(await screen.findByText(/^configurado$/i)).not.toBeNull();
    expect(screen.getByText(/smtp\.gmail\.com:587/)).not.toBeNull();
  });

  it('el correo de prueba muestra el motivo cuando no sale', async () => {
    authApi.correoEstado.mockResolvedValue({ configurado: true, motivo: '', servidor: 'smtp.gmail.com:587', remitente: 'x' });
    authApi.probarCorreo.mockResolvedValue({ enviado: false, message: 'Gmail rechazó la contraseña de aplicación.' });

    render(<EmailModule />);
    await screen.findByText(/^configurado$/i);

    fireEvent.change(screen.getByLabelText(/enviar una prueba a/i), { target: { value: 'tomas@gmail.com' } });
    fireEvent.click(screen.getByRole('button', { name: /enviar correo de prueba/i }));

    expect(await screen.findByText(/gmail rechazó/i)).not.toBeNull();
    expect(authApi.probarCorreo).toHaveBeenCalledWith('tomas@gmail.com');
  });
});

describe('Pantalla de recuperar contraseña', () => {
  const pedirEnlace = () => {
    fireEvent.change(screen.getByLabelText(/correo electrónico/i), { target: { value: 'tomas@gmail.com' } });
    fireEvent.click(screen.getByRole('button', { name: /recuperar contraseña/i }));
  };

  it('no promete un correo cuando el servidor no está configurado', async () => {
    authApi.recover.mockResolvedValue({ message: 'Si el correo existe, recibirás instrucciones.', correoConfigurado: false });

    render(<RecoverPassword onBack={() => {}} />);
    pedirEnlace();

    expect(await screen.findByText(/todavía no está configurado/i)).not.toBeNull();
    expect(screen.queryByText(/correo no deseado/i)).toBeNull();
  });

  it('cuando sí está configurado recuerda mirar el correo no deseado', async () => {
    authApi.recover.mockResolvedValue({ message: 'Si el correo existe, recibirás instrucciones.', correoConfigurado: true });

    render(<RecoverPassword onBack={() => {}} />);
    pedirEnlace();

    await waitFor(() => expect(screen.getByText(/correo no deseado/i)).not.toBeNull());
    expect(screen.queryByText(/todavía no está configurado/i)).toBeNull();
  });
});
