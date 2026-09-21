import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiRequest, facturasApi, ventasApi } from '../../services/api';
import { fechaCorta, formatoMoneda } from '../../utils/formato';

const IVA = 0.19;
const lineaVacia = { tipo: 'producto', itemId: '', cantidad: 1, descuento: 0 };
const filtrosVacios = { fechaInicio: '', fechaFin: '', cliente: '', estado: '', producto: '', servicio: '' };

/**
 * Registro de ventas desde el sitio e historial consultable con filtros.
 * Cubre los requerimientos 1, 2 y 3 del quinto avance.
 */
function SalesModule({ puedeRegistrar }) {
  const [productos, setProductos] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [cabecera, setCabecera] = useState({ cliente: '', clienteDocumento: '', observaciones: '' });
  const [lineas, setLineas] = useState([{ ...lineaVacia }]);
  const [filtros, setFiltros] = useState(filtrosVacios);
  const [ventas, setVentas] = useState([]);
  const [resumen, setResumen] = useState({ cantidad: 0, total: 0 });
  const [seleccionada, setSeleccionada] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');

  const catalogo = useMemo(
    () => ({
      producto: productos,
      servicio: servicios,
    }),
    [productos, servicios],
  );

  const cargarVentas = useCallback(
    (filtrosActivos = filtros) =>
      ventasApi
        .listar(filtrosActivos)
        .then((data) => {
          setVentas(data.ventas || []);
          setResumen(data.resumen || { cantidad: 0, total: 0 });
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [filtros],
  );

  useEffect(() => {
    Promise.all([apiRequest('/products'), apiRequest('/services')])
      .then(([datosProductos, datosServicios]) => {
        setProductos(datosProductos.products || []);
        setServicios(datosServicios.services || []);
      })
      .catch((requestError) => setError(requestError.message));
  }, []);

  useEffect(() => {
    cargarVentas(filtrosVacios);
    // Solo en el montaje: los filtros se aplican con el botón "Buscar".
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totales = useMemo(() => {
    let subtotal = 0;
    let descuentos = 0;
    lineas.forEach((linea) => {
      const item = (catalogo[linea.tipo] || []).find((fila) => String(fila.id) === String(linea.itemId));
      if (!item) return;
      const bruto = Number(item.price || 0) * Number(linea.cantidad || 0);
      const descuento = Math.min(Number(linea.descuento || 0), bruto);
      subtotal += bruto - descuento;
      descuentos += descuento;
    });
    const impuestos = subtotal * IVA;
    return { subtotal, descuentos, impuestos, total: subtotal + impuestos };
  }, [lineas, catalogo]);

  const actualizarLinea = (indice, cambios) =>
    setLineas((actuales) => actuales.map((linea, posicion) => (posicion === indice ? { ...linea, ...cambios } : linea)));

  const registrarVenta = async (event) => {
    event.preventDefault();
    setMensaje('');
    const items = lineas
      .filter((linea) => linea.itemId)
      .map((linea) => ({
        tipo: linea.tipo,
        itemId: Number(linea.itemId),
        cantidad: Number(linea.cantidad || 1),
        descuento: Number(linea.descuento || 0),
      }));

    if (!items.length) {
      setError('Agrega al menos un producto o servicio a la venta.');
      return;
    }

    try {
      const data = await ventasApi.crear({ ...cabecera, items });
      setMensaje(`${data.message} Número ${data.venta.numero}.`);
      setError('');
      setCabecera({ cliente: '', clienteDocumento: '', observaciones: '' });
      setLineas([{ ...lineaVacia }]);
      await cargarVentas(filtros);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const generarFactura = async (venta) => {
    try {
      const data = await facturasApi.generar(venta.id);
      setMensaje(`${data.message} Número ${data.factura.numero}.`);
      setError('');
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const verDetalle = async (venta) => {
    try {
      const data = await ventasApi.detalle(venta.id);
      setSeleccionada(data.venta);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <section id="ventas-panel" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <h2 className="text-xl font-bold text-white">Ventas</h2>

      {mensaje && <p className="rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-200">{mensaje}</p>}
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      {puedeRegistrar && (
        <form onSubmit={registrarVenta} className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <h3 className="font-semibold text-white">Registrar una venta</h3>

          <div className="grid gap-3 md:grid-cols-3">
            <label className="text-sm text-slate-300">
              Cliente
              <input
                required
                className="field mt-1"
                value={cabecera.cliente}
                onChange={(event) => setCabecera({ ...cabecera, cliente: event.target.value })}
              />
            </label>
            <label className="text-sm text-slate-300">
              Documento
              <input
                className="field mt-1"
                value={cabecera.clienteDocumento}
                onChange={(event) => setCabecera({ ...cabecera, clienteDocumento: event.target.value })}
              />
            </label>
            <label className="text-sm text-slate-300">
              Observaciones
              <input
                className="field mt-1"
                value={cabecera.observaciones}
                onChange={(event) => setCabecera({ ...cabecera, observaciones: event.target.value })}
              />
            </label>
          </div>

          <div className="space-y-3">
            {lineas.map((linea, indice) => (
              <div key={indice} className="grid gap-3 md:grid-cols-5">
                <label className="text-sm text-slate-300">
                  Tipo
                  <select
                    className="field mt-1"
                    value={linea.tipo}
                    onChange={(event) => actualizarLinea(indice, { tipo: event.target.value, itemId: '' })}
                  >
                    <option value="producto">Producto</option>
                    <option value="servicio">Servicio</option>
                  </select>
                </label>
                <label className="text-sm text-slate-300 md:col-span-2">
                  {linea.tipo === 'producto' ? 'Producto' : 'Servicio'}
                  <select
                    className="field mt-1"
                    value={linea.itemId}
                    onChange={(event) => actualizarLinea(indice, { itemId: event.target.value })}
                  >
                    <option value="">Selecciona una opción</option>
                    {(catalogo[linea.tipo] || []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name} — {formatoMoneda(item.price)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm text-slate-300">
                  Cantidad
                  <input
                    type="number"
                    min="1"
                    step="1"
                    className="field mt-1"
                    value={linea.cantidad}
                    onChange={(event) => actualizarLinea(indice, { cantidad: event.target.value })}
                  />
                </label>
                <label className="text-sm text-slate-300">
                  Descuento
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    className="field mt-1"
                    value={linea.descuento}
                    onChange={(event) => actualizarLinea(indice, { descuento: event.target.value })}
                  />
                </label>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200"
                onClick={() => setLineas((actuales) => [...actuales, { ...lineaVacia }])}
              >
                Agregar línea
              </button>
              {lineas.length > 1 && (
                <button
                  type="button"
                  className="rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200"
                  onClick={() => setLineas((actuales) => actuales.slice(0, -1))}
                >
                  Quitar última
                </button>
              )}
            </div>

            <p className="text-sm text-slate-300">
              Subtotal {formatoMoneda(totales.subtotal)} · Descuentos {formatoMoneda(totales.descuentos)} · IVA{' '}
              {formatoMoneda(totales.impuestos)} ·{' '}
              <span className="font-semibold text-cyan-300">Total {formatoMoneda(totales.total)}</span>
            </p>
          </div>

          <button type="submit" className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950">
            Registrar venta
          </button>
        </form>
      )}

      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
        <h3 className="font-semibold text-white">Historial de ventas</h3>

        <div className="grid gap-3 md:grid-cols-6">
          <label className="text-sm text-slate-300">
            Desde
            <input type="date" className="field mt-1" value={filtros.fechaInicio} onChange={(event) => setFiltros({ ...filtros, fechaInicio: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Hasta
            <input type="date" className="field mt-1" value={filtros.fechaFin} onChange={(event) => setFiltros({ ...filtros, fechaFin: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Cliente
            <input className="field mt-1" value={filtros.cliente} onChange={(event) => setFiltros({ ...filtros, cliente: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Producto
            <input className="field mt-1" value={filtros.producto} onChange={(event) => setFiltros({ ...filtros, producto: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Servicio
            <input className="field mt-1" value={filtros.servicio} onChange={(event) => setFiltros({ ...filtros, servicio: event.target.value })} />
          </label>
          <label className="text-sm text-slate-300">
            Estado
            <select className="field mt-1" value={filtros.estado} onChange={(event) => setFiltros({ ...filtros, estado: event.target.value })}>
              <option value="">Todos</option>
              <option value="Registrada">Registrada</option>
              <option value="Pagada">Pagada</option>
              <option value="Anulada">Anulada</option>
            </select>
          </label>
        </div>

        <div className="flex gap-2">
          <button type="button" className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950" onClick={() => cargarVentas(filtros)}>
            Buscar
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200"
            onClick={() => {
              setFiltros(filtrosVacios);
              cargarVentas(filtrosVacios);
            }}
          >
            Limpiar
          </button>
        </div>

        <p className="text-sm text-slate-400">
          {resumen.cantidad} venta(s) · Total {formatoMoneda(resumen.total)}
        </p>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm text-slate-300">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400">
                <th className="py-2 pr-4">Número</th>
                <th className="py-2 pr-4">Fecha</th>
                <th className="py-2 pr-4">Cliente</th>
                <th className="py-2 pr-4">Total</th>
                <th className="py-2 pr-4">Estado</th>
                <th className="py-2">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {ventas.map((venta) => (
                <tr key={venta.id} className="border-b border-slate-800">
                  <td className="py-3 pr-4 text-white">{venta.numero}</td>
                  <td className="py-3 pr-4">{fechaCorta(venta.fecha)}</td>
                  <td className="py-3 pr-4">{venta.cliente}</td>
                  <td className="py-3 pr-4">{formatoMoneda(venta.total)}</td>
                  <td className="py-3 pr-4">{venta.estado}</td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className="text-cyan-300" onClick={() => verDetalle(venta)}>
                        Detalle
                      </button>
                      {puedeRegistrar && (
                        <button type="button" className="text-emerald-300" onClick={() => generarFactura(venta)}>
                          Facturar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {!ventas.length && (
                <tr>
                  <td colSpan="6" className="py-4 text-slate-500">
                    No hay ventas para los filtros seleccionados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {seleccionada && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
          <div className="w-full max-w-2xl rounded-3xl border border-slate-700 bg-slate-900 p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-xl font-bold text-white">Venta {seleccionada.numero}</h3>
              <button type="button" className="text-xl text-slate-400" onClick={() => setSeleccionada(null)} aria-label="Cerrar detalle">
                ×
              </button>
            </div>

            <p className="text-sm text-slate-300">
              Cliente: {seleccionada.cliente} · Documento: {seleccionada.clienteDocumento || 'No registrado'} · Fecha:{' '}
              {fechaCorta(seleccionada.fecha)}
            </p>

            <table className="mt-4 min-w-full text-left text-sm text-slate-300">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="py-2 pr-4">Tipo</th>
                  <th className="py-2 pr-4">Descripción</th>
                  <th className="py-2 pr-4">Cantidad</th>
                  <th className="py-2 pr-4">Precio</th>
                  <th className="py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {(seleccionada.detalle || []).map((linea) => (
                  <tr key={linea.id} className="border-b border-slate-800">
                    <td className="py-2 pr-4 capitalize">{linea.tipo}</td>
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
          </div>
        </div>
      )}
    </section>
  );
}

export default SalesModule;
