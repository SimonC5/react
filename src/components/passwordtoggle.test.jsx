import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import Input from './Input';

afterEach(cleanup);

describe('Ojo para mostrar la contraseña', () => {
  it('cambia el campo entre oculto y visible, y vuelve', () => {
    render(<Input id="clave" label="Contraseña" type="password" defaultValue="Cliente1234" />);

    const campo = document.getElementById('clave');
    expect(campo.getAttribute('type')).toBe('password');

    fireEvent.click(screen.getByRole('button', { name: /mostrar contraseña/i }));
    expect(campo.getAttribute('type')).toBe('text');

    fireEvent.click(screen.getByRole('button', { name: /ocultar contraseña/i }));
    expect(campo.getAttribute('type')).toBe('password');
  });

  it('no aparece en los campos que no son de contraseña', () => {
    render(<Input id="correo" label="Correo" type="email" />);
    expect(screen.queryByRole('button', { name: /contraseña/i })).toBeNull();
  });

  it('cada campo lleva su propio ojo, sin arrastrar al otro', () => {
    render(
      <>
        <Input id="clave1" label="Contraseña" type="password" />
        <Input id="clave2" label="Confirmación" type="password" />
      </>,
    );

    const ojos = screen.getAllByRole('button', { name: /mostrar contraseña/i });
    expect(ojos).toHaveLength(2);

    fireEvent.click(ojos[0]);
    expect(document.getElementById('clave1').getAttribute('type')).toBe('text');
    expect(document.getElementById('clave2').getAttribute('type')).toBe('password');
  });

  it('sigue mostrando el máximo de caracteres y la ayuda', () => {
    render(<Input id="clave" label="Contraseña" type="password" maxLength={20} hint="Mínimo 8 caracteres." />);
    expect(screen.getByText(/máximo 20 caracteres/i)).not.toBeNull();
    expect(screen.getByText(/mínimo 8 caracteres/i)).not.toBeNull();
  });
});
