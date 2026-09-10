const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem('simonsc_token');
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor. Inicia el backend con "npm run dev" dentro de la carpeta backend.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || 'No fue posible completar la solicitud.');
  return data;
}

export const authApi = {
  login: (body) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  register: (body) => apiRequest('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  me: () => apiRequest('/auth/me'),
  recover: (email) => apiRequest('/auth/recover', { method: 'POST', body: JSON.stringify({ email }) }),
};
export { API_URL };
