import { useCallback, useEffect, useState } from 'react';
import { pagosApi } from '../../services/api';
import { fechaCorta, formatoMoneda } from '../../utils/formato';

const filtrosVacios = { estado: '', referencia: '' };

// La pasarela se guarda en minúscula; en pantalla se escribe como se llama.
const PASARELAS = { payu: 'PayU', simulada: 'Simulada' };

const COLORES = {
  Aprobado: 'bg-emerald-500/15 text-emerald-300',
  Rechazado: 'bg-red-500/15 text-red-300',
  Pendiente: 'bg-amber-500/15 text-amber-300',
  Error: 'bg-red-500/15 text-red-300',
};

/**
 * Historial de la pasarela de pago.
 *
 * Quien administra ve todos los cobros; el Cliente solo los suyos, porque el
 * filtro lo aplica el servidor y no esta pantalla.
 */
function PaymentsModule({ titulo = 'Pagos' }) {
  const [filtros, setFiltros] = useState(filtrosVacios);
  const [pagos, setPagos] = useState([]);
  const [resumen, setResumen] = useState({ cantidad: 0, aprobado: 0 });
  const [error, setError] = useState('');

  const cargar = useCallback(
    (filtrosActivos) =>
      pagosApi
        .listar(filtrosActivos)
        .then((data) => {
          setPagos(data.pagos || []);
          setResumen(data.resumen || { cantidad: 0, aprobado: 0 });
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );

  useEffect(() => {
    cargar(filtrosVacios);
  }, [cargar]);

  const buscar = (event) => {
    event.preventDefault();
    cargar(filtros);
  };

  return (
    <div className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-white">{titulo}</h2>
        <p className="text-sm text-slate-400">
          {resumen.cantidad} pago(s) · <span className="font-semibold text-emerald-300">{formatoMoneda(resumen.aprobado)}</span>{' '}
          aprobado
        </p>
      </div>

      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      <form onSubmit={buscar} className="grid gap-3 sm:grid-cols-3">
        <label className="text-sm text-slate-300">
          Referencia
          <input
            className="field mt-1"
            value={filtros.referencia}
            onChange={(event) => setFiltros({ ...filtros, referencia: event.target.value })}
          />
        </label>
        <label className="text-sm text-slate-300">
          Estado
          <select
            className="field mt-1"
            value={filtros.estado}
            onChange={(event) => setFiltros({ ...filtros, estado: event.target.value })}
          >
            <option value="">Todos</option>
            <option value="Aprobado">Aprobado</option>
            <option value="Rechazado">Rechazado</option>
            <option value="Pendiente">Pendiente</option>
            <option value="Error">Error</option>
          </select>
        </label>
        <div className="flex items-end gap-2">
          <button type="submit" className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950">
            Buscar
          </button>
          <button
            type="button"
            onClick={() => {
              setFiltros(filtrosVacios);
              cargar(filtrosVacios);
            }}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200"
          >
            Limpiar
          </button>
        </div>
      </form>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm text-slate-300">
          <thead className="text-xs uppercase tracking-[0.2em] text-slate-500">
            <tr>
              <th className="px-3 py-2">Referencia</th>
              <th className="px-3 py-2">Fecha</th>
              <th className="px-3 py-2">Pasarela</th>
              <th className="px-3 py-2">Medio</th>
              <th className="px-3 py-2">Valor</th>
              <th className="px-3 py-2">Estado</th>
            </tr>
          </thead>
          <tbody>
            {pagos.map((pago) => (
              <tr key={pago.id} className="border-t border-slate-800">
                <td className="px-3 py-2 font-semibold text-white">{pago.referencia}</td>
                <td className="px-3 py-2">{fechaCorta(pago.fecha)}</td>
                <td className="px-3 py-2">{PASARELAS[pago.pasarela] || pago.pasarela}</td>
                <td className="px-3 py-2">
                  {pago.ultimosDigitos
                    ? `${pago.franquicia} ····${pago.ultimosDigitos}`
                    : 'El que eligió en PayU'}
                </td>
                <td className="px-3 py-2 font-medium text-cyan-300">{formatoMoneda(pago.monto)}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${COLORES[pago.estado] || ''}`}>
                    {pago.estado}
                  </span>
                  {pago.motivo && <p className="mt-1 text-xs text-slate-500">{pago.motivo}</p>}
                </td>
              </tr>
            ))}
            {!pagos.length && (
              <tr>
                <td colSpan="6" className="px-3 py-6 text-center text-slate-500">
                  Todavía no hay pagos registrados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PaymentsModule;
