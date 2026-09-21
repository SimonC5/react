/** Formatos compartidos por los paneles y los gráficos. */
export function formatoMoneda(valor) {
  return `$ ${Number(valor || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 })}`;
}

export function formatoNumero(valor) {
  return Number(valor || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 });
}

export function fechaCorta(valor) {
  if (!valor) return '';
  return String(valor).slice(0, 16).replace('T', ' ');
}

export function hoyISO() {
  const ahora = new Date();
  const desfase = ahora.getTimezoneOffset() * 60000;
  return new Date(ahora.getTime() - desfase).toISOString().slice(0, 10);
}
