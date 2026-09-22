import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Login from './Login';
import { AuthProvider } from '../context/AuthContext';

const renderLogin = () => render(<MemoryRouter><AuthProvider><Login /></AuthProvider></MemoryRouter>);

const pasarAlPasoDeClave = (email = 'ana@example.com') => {
  fireEvent.change(screen.getByLabelText(/correo electrónico/i), { target: { value: email } });
  fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));
};

afterEach(() => {
  cleanup();
});

describe('Inicio de sesión en dos pasos', () => {
  it('el primer paso solo pide el correo y valida su formato', () => {
    renderLogin();

    expect(screen.queryByLabelText(/contraseña/i)).toBeNull();

    fireEvent.change(screen.getByLabelText(/correo electrónico/i), { target: { value: 'correo-invalido' } });
    fireEvent.click(screen.getByRole('button', { name: /siguiente/i }));

    expect(screen.getByText(/correo electrónico inválido/i)).not.toBeNull();
    expect(screen.queryByLabelText(/contraseña/i)).toBeNull();
  });

  it('con un correo válido pasa al segundo paso y pide la contraseña', () => {
    renderLogin();
    pasarAlPasoDeClave();

    expect(screen.getByText('ana@example.com')).not.toBeNull();
    expect(screen.getByLabelText(/contraseña/i)).not.toBeNull();
    expect(screen.queryByLabelText(/correo electrónico/i)).toBeNull();
  });

  it('valida la longitud de la contraseña en el segundo paso', () => {
    renderLogin();
    pasarAlPasoDeClave();

    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: /iniciar sesión/i }));

    expect(screen.getByText(/debe tener al menos 8 caracteres/i)).not.toBeNull();
  });

  it('el botón Cambiar regresa al paso del correo', () => {
    renderLogin();
    pasarAlPasoDeClave();

    fireEvent.click(screen.getByRole('button', { name: /cambiar/i }));

    expect(screen.getByLabelText(/correo electrónico/i)).not.toBeNull();
    expect(screen.queryByLabelText(/contraseña/i)).toBeNull();
  });
});

describe('Register modal', () => {
  it('abre el modal y valida el formulario de registro', () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /crear una cuenta/i }));
    fireEvent.click(screen.getByRole('button', { name: /registrarse/i }));

    expect(screen.getByText(/nombre es obligatorio/i)).not.toBeNull();
    // Los máximos de cada campo, tal como los pidió tomas.
    const limites = {
      'register-name': 20,
      'register-lastName': 20,
      'register-documentNumber': 12,
      'register-address': 50,
      'register-phone': 15,
      'register-email': 30,
      'register-password': 20,
      'register-confirmPassword': 20,
    };
    for (const [id, maximo] of Object.entries(limites)) {
      expect(document.getElementById(id).maxLength).toBe(maximo);
    }
    // Y que el formulario los muestre: cuatro campos comparten el de 20.
    expect(screen.getAllByText(/máximo 20 caracteres/i)).toHaveLength(4);
  });

  it('el número de documento descarta lo que no sea un número', () => {
    renderLogin();

    fireEvent.click(screen.getByRole('button', { name: /crear una cuenta/i }));
    const documento = screen.getByLabelText(/número de documento/i);
    fireEvent.change(documento, { target: { value: '12ab34-56 78' } });

    expect(documento.value).toBe('12345678');
  });
});

describe('Recuperación de cuenta', () => {
  it('muestra el logo y el aviso de recuperación por correo', () => {
    renderLogin();
    pasarAlPasoDeClave();

    fireEvent.click(screen.getByRole('button', { name: /¿olvidaste tu contraseña\?/i }));

    expect(screen.getByAltText(/logo simonc/i)).not.toBeNull();
    expect(screen.getByText(/se le enviará un correo electrónico.*recuperar la cuenta perdida/i)).not.toBeNull();
  });
});
