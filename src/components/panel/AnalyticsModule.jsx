import { useCallback, useEffect, useState } from 'react';
import Modal from '../Modal';
import BarChart from '../charts/BarChart';
import LineChart from '../charts/LineChart';
import StatCard from '../charts/StatCard';
import { dashboardApi } from '../../services/api';
import { formatoMoneda, formatoNumero } from '../../utils/formato';

const filtrosVacios = { agrupacion: 'dia', fechaInicio: '', fechaFin: '', producto: '', servicio: '', estado: '', cliente: '' };

/**
 * Dashboard con Cards de indicadores, gráfico de barras y gráfico lineal.
 * Toda la información se calcula en FastAPI a partir de la base de datos.
 * Cubre los requerimientos 10, 11, 12, 13 y 15 del quinto avance.
 */
function AnalyticsModule({ rol }) {
  const [resumen, setResumen] = useState(null);
  const [series, setSeries] = useState(null);
  const [opciones, setOpciones] = useState({ productos: [], servicios: [], clientes: [], estadosVenta: [] });
  const [filtros, setFiltros] = useState(filtrosVacios);
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const [error, setError] = useState('');

  const cargarSeries = useCallback(
    (filtrosActivos) =>
      dashboardApi
        .ventas(filtrosActivos)
        .then((data) => {
          setSeries(data);
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );

  useEffect(() => {
    dashboardApi.resumen().then(setResumen).catch((requestError) => setError(requestError.message));
    dashboardApi.filtros().then(setOpciones).catch(() => undefined);
    cargarSeries(filtrosVacios);
  }, [cargarSeries]);

  const titulo = rol === 'Administrador' ? 'Dashboard administrativo' : `Dashboard de ${rol?.toLowerCase()}`;

  return (
    <section id="dashboard-panel" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div>
          <h2 className="text-xl font-bold text-white">{titulo}</h2>
          <p className="mt-1 text-sm text-slate-400">
            Indicadores calculados en tiempo real desde FastAPI y la base de datos.
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
          onClick={() => setFiltrosAbiertos(true)}
        >
          Filtros de los gráficos
        </button>
      </div>

      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(resumen?.tarjetas || []).map((tarjeta) => (
          <StatCard key={tarjeta.clave} titulo={tarjeta.titulo} valor={tarjeta.valor} formato={tarjeta.formato} />
        ))}
      </div>

      <Modal
        isOpen={filtrosAbiertos}
        onClose={() => setFiltrosAbiertos(false)}
        title="Filtros de los gráficos"
        subtitle="Elige el periodo y acota los datos que quieres ver."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-slate-300">
            Agrupar por
            <select className="field mt-1" value={filtros.agrupacion} onChange={(event) => setFiltros({ ...filtros, agrupacion: event.target.value })}>
              <option value="dia">Día</option>
              <option value="semana">Semana</option>
              <option value="mes">Mes</option>
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Desde
            <input type="date" className="field mt-1" value={filtros.fechaInicio} onChange={(event) => setFiltros({ ...filtros, fechaInicio: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Hasta
            <input type="date" className="field mt-1" value={filtros.fechaFin} onChange={(event) => setFiltros({ ...filtros, fechaFin: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Producto
            <select className="field mt-1" value={filtros.producto} onChange={(event) => setFiltros({ ...filtros, producto: event.target.value })}>
              <option value="">Todos</option>
              {opciones.productos.map((nombre) => (
                <option key={nombre} value={nombre}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Servicio
            <select className="field mt-1" value={filtros.servicio} onChange={(event) => setFiltros({ ...filtros, servicio: event.target.value })}>
              <option value="">Todos</option>
              {opciones.servicios.map((nombre) => (
                <option key={nombre} value={nombre}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Estado
            <select className="field mt-1" value={filtros.estado} onChange={(event) => setFiltros({ ...filtros, estado: event.target.value })}>
              <option value="">Todos</option>
              {opciones.estadosVenta.map((nombre) => (
                <option key={nombre} value={nombre}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Cliente
            <select className="field mt-1" value={filtros.cliente} onChange={(event) => setFiltros({ ...filtros, cliente: event.target.value })}>
              <option value="">Todos</option>
              {opciones.clientes.map((nombre) => (
                <option key={nombre} value={nombre}>
                  {nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200"
            onClick={() => {
              setFiltros(filtrosVacios);
              cargarSeries(filtrosVacios);
              setFiltrosAbiertos(false);
            }}
          >
            Limpiar
          </button>
          <button
            type="button"
            className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
            onClick={() => {
              cargarSeries(filtros);
              setFiltrosAbiertos(false);
            }}
          >
            Aplicar filtros
          </button>
        </div>
      </Modal>

      {series && (
        <p className="text-sm text-slate-400">
          {formatoNumero(series.totales.ventas)} venta(s) · {formatoMoneda(series.totales.monto)} en el periodo consultado.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <BarChart title="Monto vendido por periodo" data={series?.barras || []} formatValue={formatoMoneda} />
        <LineChart title="Número de ventas por periodo" data={series?.lineal || []} formatValue={formatoNumero} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
          <h3 className="mb-3 text-lg font-bold text-white">Productos y servicios más vendidos</h3>
          <ul className="space-y-2 text-sm text-slate-300">
            {(series?.topItems || []).map((item) => (
              <li key={`${item.tipo}-${item.nombre}`} className="flex justify-between gap-3 border-b border-slate-800 pb-2">
                <span>
                  {item.nombre} <span className="text-xs capitalize text-slate-500">({item.tipo})</span>
                </span>
                <span className="font-semibold text-cyan-300">{formatoMoneda(item.total)}</span>
              </li>
            ))}
            {!series?.topItems?.length && <li className="text-slate-500">Sin datos para los filtros seleccionados.</li>}
          </ul>
        </div>

        <BarChart
          title="PQR por estado"
          data={resumen?.pqrPorEstado || []}
          formatValue={formatoNumero}
          emptyLabel="Aún no hay solicitudes registradas."
        />
      </div>
    </section>
  );
}

export default AnalyticsModule;
