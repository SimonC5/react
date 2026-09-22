import { describe, expect, it } from 'vitest';
import { normalizarApiUrl } from './api';

describe('Dirección de la API en el despliegue', () => {
  it('acepta el dominio como lo copia uno del panel del hosting', () => {
    const esperado = 'https://simonc-api.onrender.com/api';
    expect(normalizarApiUrl('simonc-api.onrender.com')).toBe(esperado);
    expect(normalizarApiUrl('https://simonc-api.onrender.com')).toBe(esperado);
    expect(normalizarApiUrl('https://simonc-api.onrender.com/')).toBe(esperado);
    expect(normalizarApiUrl('https://simonc-api.onrender.com/api')).toBe(esperado);
    expect(normalizarApiUrl('https://simonc-api.onrender.com/api/')).toBe(esperado);
    expect(normalizarApiUrl('  simonc-api.onrender.com/api  ')).toBe(esperado);
  });

  it('sin configurar apunta al backend local', () => {
    expect(normalizarApiUrl(undefined)).toBe('http://localhost:8000/api');
    expect(normalizarApiUrl('')).toBe('http://localhost:8000/api');
  });

  it('publicado y sin configurar, busca la API del mismo despliegue', () => {
    // Llamar a localhost desde el sitio publicado es llamar al computador del
    // visitante: el navegador lo bloquea y no hay forma de entrar.
    expect(normalizarApiUrl('', 'simonc-web.onrender.com')).toBe('https://simonc-api.onrender.com/api');
    expect(normalizarApiUrl(undefined, 'simonc-web.onrender.com')).toBe('https://simonc-api.onrender.com/api');
  });

  it('lo configurado manda sobre la suposición', () => {
    expect(normalizarApiUrl('otra-api.onrender.com', 'simonc-web.onrender.com')).toBe('https://otra-api.onrender.com/api');
  });

  it('no fuerza https cuando es el backend local', () => {
    expect(normalizarApiUrl('localhost:8000')).toBe('http://localhost:8000/api');
    expect(normalizarApiUrl('127.0.0.1:8000/api')).toBe('http://127.0.0.1:8000/api');
  });
});
