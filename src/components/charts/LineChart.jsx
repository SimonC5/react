/**
 * Gráfico lineal en SVG para ver la evolución de las ventas en el tiempo.
 */
function LineChart({ data = [], title, formatValue = (value) => value, emptyLabel = 'Sin datos para los filtros seleccionados.' }) {
  if (!data.length) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        {title && <h3 className="text-lg font-bold text-white">{title}</h3>}
        <p className="mt-3 text-sm text-slate-400">{emptyLabel}</p>
      </div>
    );
  }

  const valores = data.map((punto) => Number(punto.valor) || 0);
  const maximo = Math.max(...valores, 1);
  const paso = data.length > 1 ? 100 / (data.length - 1) : 0;
  const puntos = valores.map((valor, indice) => {
    const x = data.length > 1 ? indice * paso : 50;
    const y = 58 - (valor / maximo) * 52;
    return { x, y, valor, etiqueta: data[indice].etiqueta };
  });
  const trazo = puntos.map((punto, indice) => `${indice === 0 ? 'M' : 'L'}${punto.x.toFixed(2)},${punto.y.toFixed(2)}`).join(' ');
  const area = `${trazo} L${puntos[puntos.length - 1].x.toFixed(2)},58 L${puntos[0].x.toFixed(2)},58 Z`;

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      {title && <h3 className="mb-4 text-lg font-bold text-white">{title}</h3>}

      <svg viewBox="0 0 100 60" preserveAspectRatio="none" role="img" aria-label={title} className="h-48 w-full">
        {[0, 15, 30, 45, 60].map((y) => (
          <line key={y} x1="0" y1={y} x2="100" y2={y} stroke="#1e293b" strokeWidth="0.3" />
        ))}
        <path d={area} fill="#22d3ee" opacity="0.12" />
        <path d={trazo} fill="none" stroke="#38bdf8" strokeWidth="0.8" strokeLinejoin="round" strokeLinecap="round" />
        {puntos.map((punto) => (
          <circle key={punto.etiqueta} cx={punto.x} cy={punto.y} r="1" fill="#e0f2fe">
            <title>{`${punto.etiqueta}: ${formatValue(punto.valor)}`}</title>
          </circle>
        ))}
      </svg>

      <ul className="mt-4 grid gap-1 text-xs text-slate-400 sm:grid-cols-2">
        {data.map((punto) => (
          <li key={punto.etiqueta} className="flex justify-between gap-3">
            <span>{punto.etiqueta}</span>
            <span className="font-semibold text-sky-300">{formatValue(Number(punto.valor) || 0)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default LineChart;
