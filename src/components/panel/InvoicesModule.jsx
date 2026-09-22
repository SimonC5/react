import { useCallback, useEffect, useState } from 'react';
import Modal from '../Modal';
import { facturasApi, ventasApi } from '../../services/api';
import { fechaCorta, formatoMoneda } from '../../utils/formato';

const filtrosVacios = { numero: '', cliente: '', estado: '', fechaInicio: '', fechaFin: '' };

/**
 * Consulta y descarga de facturas de venta.
 * Cubre los requerimientos 8 y 9 del quinto avance.
 */
function InvoicesModule({ titulo = 'Facturación', puedeGenerar = false }) {
  const [filtros, setFiltros] = useState(filtrosVacios);
  const [facturas, setFacturas] = useState([]);
  const [seleccionada, setSeleccionada] = useState(null);
  const [generacionAbierta, setGeneracionAbierta] = useState(false);
  const [sinFacturar, setSinFacturar] = useState([]);
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(
    (filtrosActivos) =>
      facturasApi
        .listar(filtrosActivos)
        .then((data) => {
          setFacturas(data.facturas || []);
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );

  useEffect(() => {
    cargar(filtrosVacios);
  }, [cargar]);

  /** Abre la ventana con las ventas que todavía no tienen factura. */
  const abrirGeneracion = async () => {
    setGeneracionAbierta(true);
    try {
      const [ventasData, facturasData] = await Promise.all([ventasApi.listar({}), facturasApi.listar({})]);
      const yaFacturadas = new Set((facturasData.facturas || []).map((factura) => factura.ventaId));
      setSinFacturar((ventasData.ventas || []).filter((venta) => !yaFacturadas.has(venta.id) && venta.estado !== 'Anulada'));
      setError('');
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const generar = async (venta) => {
    try {
      const data = await facturasApi.generar(venta.id);
      setMensaje(`${data.message} Número ${data.factura.numero}.`);
      setError('');
      setGeneracionAbierta(false);
      await cargar(filtrosVacios);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const descargar = async (factura) => {
    try {
      const nombre = await facturasApi.descargar(factura.id, factura.numero);
      setMensaje(`Factura descargada como ${nombre}.`);
      setError('');
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const verDetalle = async (factura) => {
    try {
      const data = await facturasApi.detalle(factura.id);
      setSeleccionada(data.factura);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <section id="facturas-panel" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <h2 className="text-xl font-bold text-white">{titulo}</h2>

      {mensaje && <p className="rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-200">{mensaje}</p>}
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      {puedeGenerar && (
        <button
          type="button"
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
          onClick={abrirGeneracion}
        >
          Generar una factura
        </button>
      )}

      <Modal
        isOpen={generacionAbierta}
        onClose={() => setGeneracionAbierta(false)}
        title="Generar una factura"
        subtitle="Elige la venta que quieres facturar."
      >
        <ul className="space-y-2">
          {sinFacturar.map((venta) => (
            <li
              key={venta.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/40 p-3"
            >
              <span className="text-sm text-slate-300">
                <span className="font-semibold text-white">{venta.numero}</span> · {venta.cliente} ·{' '}
                {formatoMoneda(venta.total)}
              </span>
              <button
                type="button"
                className="rounded-lg bg-cyan-500 px-3 py-1.5 text-sm font-semibold text-slate-950"
                onClick={() => generar(venta)}
              >
                Facturar
              </button>
            </li>
          ))}
          {!sinFacturar.length && <li className="text-sm text-slate-500">Todas las ventas ya están facturadas.</li>}
        </ul>
      </Modal>

      <div className="grid gap-3 md:grid-cols-5">
        <label className="text-sm text-slate-300">
          Número
          <input className="field mt-1" value={filtros.numero} onChange={(event) => setFiltros({ ...filtros, numero: event.target.value })} />
        </label>
        <label className="text-sm text-slate-300">
          Cliente
          <input className="field mt-1" value={filtros.cliente} onChange={(event) => setFiltros({ ...filtros, cliente: event.target.value })} />
        </label>
        <label className="text-sm text-slate-300">
          Estado
          <select className="field mt-1" value={filtros.estado} onChange={(event) => setFiltros({ ...filtros, estado: event.target.value })}>
            <option value="">Todos</option>
            <option value="Emitida">Emitida</option>
            <option value="Pagada">Pagada</option>
            <option value="Anulada">Anulada</option>
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
      </div>

      <div className="flex gap-2">
        <button type="button" className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950" onClick={() => cargar(filtros)}>
          Buscar facturas
        </button>
        <button
          type="button"
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200"
          onClick={() => {
            setFiltros(filtrosVacios);
            cargar(filtrosVacios);
          }}
        >
          Limpiar
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm text-slate-300">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400">
              <th className="py-2 pr-4">Factura</th>
              <th className="py-2 pr-4">Venta</th>
              <th className="py-2 pr-4">Fecha</th>
              <th className="py-2 pr-4">Cliente</th>
              <th className="py-2 pr-4">Total</th>
              <th className="py-2 pr-4">Estado</th>
              <th className="py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {facturas.map((factura) => (
              <tr key={factura.id} className="border-b border-slate-800">
                <td className="py-3 pr-4 text-white">{factura.numero}</td>
                <td className="py-3 pr-4">{factura.ventaNumero}</td>
                <td className="py-3 pr-4">{fechaCorta(factura.fecha)}</td>
                <td className="py-3 pr-4">{factura.cliente}</td>
                <td className="py-3 pr-4">{formatoMoneda(factura.total)}</td>
                <td className="py-3 pr-4">{factura.estado}</td>
                <td className="py-3">
                  <div className="flex flex-wrap gap-2">
                    <button type="button" className="text-cyan-300" onClick={() => verDetalle(factura)}>
                      Detalle
                    </button>
                    <button type="button" className="text-emerald-300" onClick={() => descargar(factura)}>
                      Descargar PDF
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!facturas.length && (
              <tr>
                <td colSpan="7" className="py-4 text-slate-500">
                  No hay facturas para los filtros seleccionados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Modal
        isOpen={Boolean(seleccionada)}
        onClose={() => setSeleccionada(null)}
        title={`Factura ${seleccionada?.numero || ''}`}
      >
        {seleccionada && (
          <>
            <p className="text-sm text-slate-300">
              Cliente: {seleccionada.cliente} · Documento: {seleccionada.clienteDocumento || 'No registrado'} · Fecha:{' '}
              {fechaCorta(seleccionada.fecha)}
            </p>

            <table className="mt-4 min-w-full text-left text-sm text-slate-300">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="py-2 pr-4">Descripción</th>
                  <th className="py-2 pr-4">Cantidad</th>
                  <th className="py-2 pr-4">Precio</th>
                  <th className="py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {(seleccionada.detalle || []).map((linea) => (
                  <tr key={linea.id} className="border-b border-slate-800">
                    <td className="py-2 pr-4">{linea.nombre}</td>
                    <td className="py-2 pr-4">{linea.cantidad}</td>
                    <td className="py-2 pr-4">{formatoMoneda(linea.precioUnitario)}</td>
                    <td className="py-2">{formatoMoneda(linea.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="mt-4 text-right text-sm text-slate-300">
              Subtotal {formatoMoneda(seleccionada.subtotal)} · Impuestos {formatoMoneda(seleccionada.impuestos)} ·{' '}
              <span className="font-semibold text-cyan-300">Total {formatoMoneda(seleccionada.total)}</span>
            </p>
          </>
        )}
      </Modal>
    </section>
  );
}

export default InvoicesModule;
