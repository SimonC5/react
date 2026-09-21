import { useCallback, useEffect, useState } from 'react';
import { reportesApi } from '../../services/api';
import { fechaCorta, formatoMoneda, hoyISO } from '../../utils/formato';

/**
 * Reporte diario de ventas con exportación a PDF y a Excel.
 * Cubre los requerimientos 4, 5 y 6 del quinto avance.
 */
function ReportsModule() {
  const [fecha, setFecha] = useState(hoyISO());
  const [reporte, setReporte] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(
    (dia) =>
      reportesApi
        .diario(dia)
        .then((data) => {
          setReporte(data.reporte);
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );

  useEffect(() => {
    cargar(hoyISO());
  }, [cargar]);

  const exportar = async (formato) => {
    try {
      const nombre = formato === 'pdf' ? await reportesApi.descargarPdf(fecha) : await reportesApi.descargarExcel(fecha);
      setMensaje(`Reporte descargado como ${nombre}.`);
      setError('');
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const totales = reporte?.totales;

  return (
    <section id="reportes-panel" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <h2 className="text-xl font-bold text-white">Reporte diario de ventas</h2>

      {mensaje && <p className="rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-200">{mensaje}</p>}
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-300">
          Fecha del reporte
          <input type="date" className="field mt-1" value={fecha} onChange={(event) => setFecha(event.target.value)} />
        </label>
        <button type="button" className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950" onClick={() => cargar(fecha)}>
          Generar reporte
        </button>
        <button type="button" className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200" onClick={() => exportar('pdf')}>
          Exportar PDF
        </button>
        <button type="button" className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200" onClick={() => exportar('excel')}>
          Exportar Excel
        </button>
      </div>

      {totales && (
        <p className="text-sm text-slate-300">
          {totales.ventas} venta(s) · {totales.unidades} unidad(es) · Subtotal {formatoMoneda(totales.subtotal)} · Descuentos{' '}
          {formatoMoneda(totales.descuentos)} · Impuestos {formatoMoneda(totales.impuestos)} ·{' '}
          <span className="font-semibold text-cyan-300">Total {formatoMoneda(totales.total)}</span>
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm text-slate-300">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400">
              <th className="py-2 pr-4">Venta</th>
              <th className="py-2 pr-4">Fecha</th>
              <th className="py-2 pr-4">Cliente</th>
              <th className="py-2 pr-4">Productos y/o servicios</th>
              <th className="py-2 pr-4">Cantidad</th>
              <th className="py-2 pr-4">Valor</th>
              <th className="py-2">Estado</th>
            </tr>
          </thead>
          <tbody>
            {(reporte?.filas || []).map((fila) => (
              <tr key={fila.numero} className="border-b border-slate-800">
                <td className="py-3 pr-4 text-white">{fila.numero}</td>
                <td className="py-3 pr-4">{fechaCorta(fila.fecha)}</td>
                <td className="py-3 pr-4">{fila.cliente}</td>
                <td className="py-3 pr-4">{fila.descripcion}</td>
                <td className="py-3 pr-4">{fila.cantidad}</td>
                <td className="py-3 pr-4">{formatoMoneda(fila.total)}</td>
                <td className="py-3">{fila.estado}</td>
              </tr>
            ))}
            {reporte && !reporte.filas.length && (
              <tr>
                <td colSpan="7" className="py-4 text-slate-500">
                  No se registraron ventas en esta fecha.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default ReportsModule;
