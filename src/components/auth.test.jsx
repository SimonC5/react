import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Login from './Login';
import { AuthProvider } from '../context/AuthContext';

const renderLogin = () => render(<MemoryRouter><AuthProvider><Login /></AuthProvider></MemoryRouter>);

afterEach(() => {
  cleanup();
});

describe('Login form', () => {
  it('muestra errores cuando los datos ingresados son inválidos', () => {
    renderLogin();

    fireEvent.change(screen.getByLabelText(/correo electrónico/i), {
      target: { value: 'correo-invalido' },
    });
    fireEvent.change(screen.getByLabelText(/contraseña/i), {
      target: { value: '123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    expect(screen.getByText(/correo electrónico inválido/i)).not.toBeNull();
    expect(screen.getByText(/debe tener al menos 8 caracteres/i)).not.toBeNull();
  });
});

describe('Register modal', () => {
  it('abre el modal y valida el formulario de registro', () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /crear una cuenta/i }));
    fireEvent.click(screen.getByRole('button', { name: /registrarse/i }));

    expect(screen.getByText(/nombre es obligatorio/i)).not.toBeNull();
    expect(screen.getAllByText(/máximo 80 caracteres/i)).toHaveLength(2);
  });
});

describe('Recuperación de cuenta', () => {
  it('muestra el logo y el aviso de recuperación por correo', () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /¿olvidaste tu contraseña\?/i }));

    expect(screen.getByAltText(/logo simonc/i)).not.toBeNull();
    expect(screen.getByText(/se le enviará un correo electrónico.*recuperar la cuenta perdida/i)).not.toBeNull();
  });
});
