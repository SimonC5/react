const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const TOKEN_KEY = 'simonsc_token';

function authHeaders() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.append(key, value);
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : '';
}

export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...options.headers },
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor. Inicia el backend con "uvicorn main:app --reload" dentro de la carpeta backend.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.message || 'No fue posible completar la solicitud.');
  return data;
}

/** Descarga un archivo protegido (PDF o Excel) respetando el token JWT. */
export async function apiDownload(path, fallbackName) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { headers: authHeaders() });
  } catch {
    throw new Error('No se pudo conectar con el servidor para descargar el archivo.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'No fue posible generar el archivo.');
  }

  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = match ? match[1] : fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return match ? match[1] : fallbackName;
}

export const authApi = {
  login: (body) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  register: (body) => apiRequest('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  me: () => apiRequest('/auth/me'),
  recover: (email) => apiRequest('/auth/recover', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (body) => apiRequest('/auth/reset-password', { method: 'POST', body: JSON.stringify(body) }),
};

export const ventasApi = {
  crear: (body) => apiRequest('/ventas', { method: 'POST', body: JSON.stringify(body) }),
  listar: (filtros) => apiRequest(`/ventas${buildQuery(filtros)}`),
  detalle: (id) => apiRequest(`/ventas/${id}`),
  cambiarEstado: (id, estado) => apiRequest(`/ventas/${id}/estado`, { method: 'PATCH', body: JSON.stringify({ estado }) }),
};

export const facturasApi = {
  generar: (ventaId) => apiRequest('/facturas', { method: 'POST', body: JSON.stringify({ ventaId }) }),
  listar: (filtros) => apiRequest(`/facturas${buildQuery(filtros)}`),
  detalle: (id) => apiRequest(`/facturas/${id}`),
  descargar: (id, numero) => apiDownload(`/facturas/${id}/pdf`, `factura-${numero}.pdf`),
};

export const reportesApi = {
  diario: (fecha) => apiRequest(`/reportes/ventas/diario${buildQuery({ fecha })}`),
  descargarPdf: (fecha) => apiDownload(`/reportes/ventas/diario.pdf${buildQuery({ fecha })}`, `reporte-ventas-${fecha}.pdf`),
  descargarExcel: (fecha) => apiDownload(`/reportes/ventas/diario.xlsx${buildQuery({ fecha })}`, `reporte-ventas-${fecha}.xlsx`),
};

export const dashboardApi = {
  resumen: () => apiRequest('/dashboard/resumen'),
  ventas: (filtros) => apiRequest(`/dashboard/ventas${buildQuery(filtros)}`),
  filtros: () => apiRequest('/dashboard/filtros'),
};

export const pqrApi = {
  crear: (body) => apiRequest('/pqr', { method: 'POST', body: JSON.stringify(body) }),
  listar: (filtros) => apiRequest(`/pqr${buildQuery(filtros)}`),
  gestionar: (id, body) => apiRequest(`/pqr/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
};

export const chatbotApi = {
  estado: () => apiRequest('/chatbot/estado'),
  enviar: (mensaje, conversacionId) =>
    apiRequest('/chatbot/mensajes', { method: 'POST', body: JSON.stringify({ mensaje, conversacionId }) }),
  conversacion: (id) => apiRequest(`/chatbot/conversaciones/${id}`),
};

export { API_URL };
