/**
 * Gráfico de barras en SVG. Recibe los datos ya calculados por FastAPI.
 */
function BarChart({ data = [], title, formatValue = (value) => value, emptyLabel = 'Sin datos para los filtros seleccionados.' }) {
  if (!data.length) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        {title && <h3 className="text-lg font-bold text-white">{title}</h3>}
        <p className="mt-3 text-sm text-slate-400">{emptyLabel}</p>
      </div>
    );
  }

  const maximo = Math.max(...data.map((punto) => Number(punto.valor) || 0), 1);
  const ancho = 100 / data.length;

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      {title && <h3 className="mb-4 text-lg font-bold text-white">{title}</h3>}

      <svg viewBox="0 0 100 60" preserveAspectRatio="none" role="img" aria-label={title} className="h-48 w-full">
        {[0, 15, 30, 45, 60].map((y) => (
          <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="#1e293b" strokeWidth="0.3" />
        ))}
        {data.map((punto, indice) => {
          const valor = Number(punto.valor) || 0;
          const alto = (valor / maximo) * 52;
          return (
            <rect
              key={punto.etiqueta}
              x={indice * ancho + ancho * 0.2}
              y={58 - alto}
              width={ancho * 0.6}
              height={Math.max(alto, 0.4)}
              rx="0.6"
              fill="#22d3ee"
            >
              <title>{`${punto.etiqueta}: ${formatValue(valor)}`}</title>
            </rect>
          );
        })}
      </svg>

      <ul className="mt-4 grid gap-1 text-xs text-slate-400 sm:grid-cols-2">
        {data.map((punto) => (
          <li key={punto.etiqueta} className="flex justify-between gap-3">
            <span>{punto.etiqueta}</span>
            <span className="font-semibold text-cyan-300">{formatValue(Number(punto.valor) || 0)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default BarChart;
