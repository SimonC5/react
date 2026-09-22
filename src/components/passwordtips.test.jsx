import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import PasswordTips from './PasswordTips';

afterEach(() => {
  cleanup();
});

/** Devuelve el texto de la recomendación junto con su marca (✓ o •). */
const marcaDe = (texto) => screen.getByText(texto).parentElement.textContent;

describe('Recomendaciones de contraseña segura', () => {
  it('muestra las cinco recomendaciones aunque no se haya escrito nada', () => {
    render(<PasswordTips password="" />);

    expect(screen.getByText(/Al menos 12 caracteres/i)).not.toBeNull();
    expect(screen.getByText(/mayúscula/i)).not.toBeNull();
    expect(screen.getByText(/minúscula/i)).not.toBeNull();
    expect(screen.getByText(/número \(0-9\)/i)).not.toBeNull();
    expect(screen.getByText(/símbolo especial/i)).not.toBeNull();
  });

  it('marca solo las recomendaciones que la contraseña cumple', () => {
    // Doce caracteres, con minúsculas y números, pero sin mayúscula ni símbolo.
    render(<PasswordTips password="contrasena12" />);

    expect(marcaDe(/Al menos 12 caracteres/i)).toContain('✓');
    expect(marcaDe(/minúscula/i)).toContain('✓');
    expect(marcaDe(/número \(0-9\)/i)).toContain('✓');
    expect(marcaDe(/mayúscula/i)).toContain('•');
    expect(marcaDe(/símbolo especial/i)).toContain('•');
  });

  it('marca las cinco cuando la contraseña las cumple todas', () => {
    render(<PasswordTips password="RealidadVR#2026" />);

    for (const texto of [/Al menos 12 caracteres/i, /mayúscula/i, /minúscula/i, /número \(0-9\)/i, /símbolo especial/i]) {
      expect(marcaDe(texto)).toContain('✓');
    }
  });
});
