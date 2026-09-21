import { formatoMoneda, formatoNumero } from '../../utils/formato';

/** Indicador numérico del dashboard, presentado como Card. */
function StatCard({ titulo, valor, formato = 'numero', detalle }) {
  const texto = formato === 'moneda' ? formatoMoneda(valor) : formatoNumero(valor);

  return (
    <article className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">{titulo}</p>
      <p className="mt-2 text-3xl font-black text-white">{texto}</p>
      {detalle && <p className="mt-1 text-xs text-slate-400">{detalle}</p>}
    </article>
  );
}

export default StatCard;
