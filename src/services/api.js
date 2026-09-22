/** Dominio desde el que se está viendo la página, si hay navegador. */
function dominioActual() {
  return typeof window === 'undefined' ? '' : (window.location?.hostname ?? '');
}

function apiPorDefecto(dominio) {
  // Sin dominio (o en el computador de uno) el backend corre al lado.
  if (!dominio || /^(localhost|127\.0\.0\.1)$/i.test(dominio)) return 'http://localhost:8000/api';
  // Publicado y sin VITE_API_URL. Antes se llamaba igual a localhost:8000, o
  // sea al computador del visitante, y el navegador lo bloqueaba sin explicar
  // nada. En Render los dos servicios del proyecto se llaman igual salvo el
  // sufijo, así que la API de "simonc-web.onrender.com" es
  // "simonc-api.onrender.com". Es una suposición, pero acierta en el despliegue
  // del proyecto y falla con un error claro en cualquier otro.
  return `https://${dominio.replace(/-web\b/, '-api')}/api`;
}

/**
 * Normaliza VITE_API_URL para el despliegue.
 *
 * En el panel del hosting lo normal es copiar el dominio tal cual
 * ("simonc-api.onrender.com") o con barra al final, y entonces todas las
 * peticiones fallan sin decir por qué. Se aceptan las tres formas: con o sin
 * "https://", con o sin "/api" y con o sin barra final.
 */
export function normalizarApiUrl(valor, dominio = dominioActual()) {
  let url = String(valor ?? '').trim().replace(/\/+$/, '');
  if (!url) return apiPorDefecto(dominio);
  if (!/^https?:\/\//i.test(url)) {
    const esLocal = /^(localhost|127\.0\.0\.1)(:|$)/i.test(url);
    url = `${esLocal ? 'http' : 'https'}://${url}`;
  }
  if (!alcanzableDesdeElNavegador(url)) return apiPorDefecto(dominio);
  return /\/api$/i.test(url) ? url : `${url}/api`;
}

/**
 * Descarta direcciones que el navegador no puede resolver.
 *
 * "simonc-api" no es una dirección de internet: es el nombre interno con el que
 * los servicios del hosting se hablan entre ellos, y es lo que Render entrega
 * al enlazar un servicio con otro en el blueprint. Al navegador del visitante
 * no le sirve, así que es mejor deducir la dirección pública que intentar una
 * que no existe.
 */
function alcanzableDesdeElNavegador(url) {
  let dominio;
  try {
    dominio = new URL(url).hostname;
  } catch {
    return false;
  }
  return dominio.includes('.') || /^localhost$/i.test(dominio);
}

const API_URL = normalizarApiUrl(import.meta.env.VITE_API_URL);

/**
 * Explica la caída según dónde esté corriendo la página.
 *
 * En el sitio publicado no sirve de nada decirle al visitante que arranque
 * uvicorn: lo que pasa es que la API no contesta, casi siempre porque el plan
 * gratuito la durmió o porque quedó apuntando a otra dirección. Por eso el
 * mensaje dice a qué dirección se intentó llamar.
 */
function errorDeConexion() {
  const dominio = dominioActual();
  if (!dominio || /^(localhost|127\.0\.0\.1)$/i.test(dominio)) {
    return 'No se pudo conectar con el servidor. Inicia el backend con "uvicorn main:app --reload" dentro de la carpeta backend.';
  }
  return `No se pudo conectar con el servidor (${API_URL}). Si el servicio estaba dormido puede tardar hasta un minuto en despertar: espera un momento y vuelve a intentar.`;
}

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
    throw new Error(errorDeConexion());
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
    throw new Error(errorDeConexion());
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
  pedido: (body) => apiRequest('/ventas/pedido', { method: 'POST', body: JSON.stringify(body) }),
};

// Catálogo público: lo que ven las páginas de Productos y Servicios.
export const catalogoApi = {
  publico: () => apiRequest('/catalogo'),
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
