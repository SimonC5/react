import { useEffect, useMemo, useState } from 'react';
import Modal from './Modal';
import { pagosApi } from '../services/api';
import { formatoMoneda } from '../utils/formato';

const IVA = 0.19;

const MEDIOS = [
  { clave: 'tarjeta', etiqueta: 'Tarjeta' },
  { clave: 'pse', etiqueta: 'PSE' },
  { clave: 'efectivo', etiqueta: 'Efectivo' },
];

const formularioVacio = {
  nombre: '',
  numero: '',
  vencimiento: '',
  cvv: '',
  cuotas: 1,
  banco: '',
  tipoDocumento: 'CC',
  documento: '',
  puntoDePago: '',
};

/** Deja el número de la tarjeta en grupos de cuatro mientras se escribe. */
function agruparTarjeta(valor) {
  const digitos = valor.replace(/\D/g, '').slice(0, 19);
  return digitos.replace(/(.{4})/g, '$1 ').trim();
}

/** Escribe el vencimiento como MM/AA sin que haya que teclear la barra. */
function formatearVencimiento(valor) {
  const digitos = valor.replace(/\D/g, '').slice(0, 4);
  return digitos.length <= 2 ? digitos : `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
}

/**
 * Pasarela de pago de la tienda.
 *
 * Es un formulario dentro del sitio: el comprador elige el medio de pago, llena
 * los datos y ve el resultado ahí mismo, sin cambiar de página.
 *
 * Los importes que se muestran son solo el desglose para que sepa qué está
 * pagando. Lo que se cobra lo calcula el servidor a partir de la venta.
 */
function CheckoutModal({ abierto, onClose, venta, factura, onPagada }) {
  const [config, setConfig] = useState(null);
  const [medio, setMedio] = useState('tarjeta');
  const [datos, setDatos] = useState(formularioVacio);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);

  useEffect(() => {
    if (!abierto) return;
    setError('');
    setResultado(null);
    setMedio('tarjeta');
    setDatos(formularioVacio);
    pagosApi.config().then(setConfig).catch(() => setConfig(null));
  }, [abierto]);

  const totales = useMemo(() => {
    const total = Number(venta?.total || 0);
    const base = Number(venta?.subtotal || 0) || total / (1 + IVA);
    return { base, iva: total - base, total };
  }, [venta]);

  const cambiar = (campo) => (event) => setDatos((actual) => ({ ...actual, [campo]: event.target.value }));

  const pagar = async (event) => {
    event.preventDefault();
    setEnviando(true);
    setError('');
    try {
      const respuesta = await pagosApi.pagar({
        ventaId: venta.id,
        metodo: medio,
        ...datos,
        numero: datos.numero.replace(/\s/g, ''),
        cuotas: Number(datos.cuotas) || 1,
      });
      setResultado(respuesta);
      if (respuesta.pago.estado === 'Aprobado') onPagada?.(respuesta);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setEnviando(false);
    }
  };

  const aprobado = resultado?.pago?.estado === 'Aprobado';
  const rechazado = resultado?.pago?.estado === 'Rechazado';
  const titulos = { Aprobado: 'Pago aprobado', Rechazado: 'Pago rechazado', Pendiente: 'Pago pendiente' };

  return (
    <Modal
      isOpen={abierto}
      onClose={onClose}
      title={resultado ? 'Resultado del pago' : 'Pagar la compra'}
      subtitle={venta ? `Compra ${venta.numero}` : ''}
    >
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      {resultado ? (
        <div className="space-y-4">
          <div
            className={`rounded-xl p-4 ${
              aprobado ? 'bg-emerald-500/10 text-emerald-200' : rechazado ? 'bg-red-500/10 text-red-300' : 'bg-amber-500/10 text-amber-200'
            }`}
          >
            <p className="text-lg font-bold">{titulos[resultado.pago.estado] || 'Resultado del pago'}</p>
            <p className="mt-1 text-sm">{resultado.message}</p>
          </div>

          <dl className="grid gap-2 rounded-xl border border-slate-800 bg-slate-950/40 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Referencia</dt>
              <dd className="font-semibold text-white">{resultado.pago.referencia}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Valor</dt>
              <dd className="font-semibold text-cyan-300">{formatoMoneda(resultado.pago.monto)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Medio de pago</dt>
              <dd className="text-slate-200">
                {resultado.pago.ultimosDigitos
                  ? `${resultado.pago.entidad} terminada en ${resultado.pago.ultimosDigitos}`
                  : resultado.pago.entidad}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Estado de la compra</dt>
              <dd className="text-slate-200">{resultado.venta?.estado}</dd>
            </div>
          </dl>

          {aprobado && factura && (
            <p className="text-sm text-slate-400">
              Tu factura {factura.numero} quedó pagada y la puedes descargar desde &quot;Mis facturas&quot;.
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            {rechazado && (
              <button
                type="button"
                className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200"
                onClick={() => setResultado(null)}
              >
                Intentar de nuevo
              </button>
            )}
            <button
              type="button"
              className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
              onClick={onClose}
            >
              Cerrar
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={pagar} className="space-y-5">
          <dl className="space-y-1 rounded-xl border border-slate-800 bg-slate-950/40 p-4 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-400">Subtotal</dt>
              <dd className="text-slate-200">{formatoMoneda(totales.base)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">IVA (19%)</dt>
              <dd className="text-slate-200">{formatoMoneda(totales.iva)}</dd>
            </div>
            <div className="flex justify-between border-t border-slate-800 pt-2 text-base">
              <dt className="font-semibold text-white">Total a pagar</dt>
              <dd className="font-bold text-cyan-300">{formatoMoneda(totales.total)}</dd>
            </div>
          </dl>

          <fieldset>
            <legend className="mb-2 text-sm text-slate-300">Medio de pago</legend>
            <div className="flex flex-wrap gap-2">
              {MEDIOS.map((item) => (
                <button
                  key={item.clave}
                  type="button"
                  onClick={() => setMedio(item.clave)}
                  aria-pressed={medio === item.clave}
                  className={`rounded-lg border px-4 py-2 text-sm ${
                    medio === item.clave
                      ? 'border-cyan-400 bg-cyan-500/10 text-cyan-200'
                      : 'border-slate-700 text-slate-300'
                  }`}
                >
                  {item.etiqueta}
                </button>
              ))}
            </div>
          </fieldset>

          {medio === 'tarjeta' && (
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-nombre">
                  Nombre del titular
                </label>
                <input id="pago-nombre" required maxLength="80" className="field" value={datos.nombre} onChange={cambiar('nombre')} />
              </div>

              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-numero">
                  Número de la tarjeta
                </label>
                <input
                  id="pago-numero"
                  required
                  inputMode="numeric"
                  placeholder="4111 1111 1111 1111"
                  className="field"
                  value={datos.numero}
                  onChange={(event) => setDatos({ ...datos, numero: agruparTarjeta(event.target.value) })}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-vence">
                    Vence
                  </label>
                  <input
                    id="pago-vence"
                    required
                    inputMode="numeric"
                    placeholder="MM/AA"
                    className="field"
                    value={datos.vencimiento}
                    onChange={(event) => setDatos({ ...datos, vencimiento: formatearVencimiento(event.target.value) })}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-cvv">
                    Código
                  </label>
                  <input
                    id="pago-cvv"
                    required
                    inputMode="numeric"
                    maxLength="4"
                    placeholder="123"
                    className="field"
                    value={datos.cvv}
                    onChange={(event) => setDatos({ ...datos, cvv: event.target.value.replace(/\D/g, '') })}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-cuotas">
                    Cuotas
                  </label>
                  <select id="pago-cuotas" className="field" value={datos.cuotas} onChange={cambiar('cuotas')}>
                    {[1, 3, 6, 12, 24].map((numero) => (
                      <option key={numero} value={numero}>
                        {numero}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {medio === 'pse' && (
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-banco">
                  Banco
                </label>
                <select id="pago-banco" required className="field" value={datos.banco} onChange={cambiar('banco')}>
                  <option value="">Elige tu banco</option>
                  {(config?.bancos || []).map((banco) => (
                    <option key={banco} value={banco}>
                      {banco}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-tipo-doc">
                    Tipo de documento
                  </label>
                  <select id="pago-tipo-doc" className="field" value={datos.tipoDocumento} onChange={cambiar('tipoDocumento')}>
                    {(config?.tiposDeDocumento || ['CC']).map((tipo) => (
                      <option key={tipo} value={tipo}>
                        {tipo}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-doc">
                    Número de documento
                  </label>
                  <input
                    id="pago-doc"
                    required
                    inputMode="numeric"
                    maxLength="15"
                    className="field"
                    value={datos.documento}
                    onChange={(event) => setDatos({ ...datos, documento: event.target.value.replace(/\D/g, '') })}
                  />
                </div>
              </div>
            </div>
          )}

          {medio === 'efectivo' && (
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-punto">
                  Dónde vas a pagar
                </label>
                <select id="pago-punto" required className="field" value={datos.puntoDePago} onChange={cambiar('puntoDePago')}>
                  <option value="">Elige el punto de pago</option>
                  {(config?.puntosDePago || []).map((punto) => (
                    <option key={punto} value={punto}>
                      {punto}
                    </option>
                  ))}
                </select>
              </div>
              <p className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-200">
                Te damos un código para pagar en el punto que elijas. La compra queda reservada y pasa a Pagada cuando
                recibamos el dinero.
              </p>
            </div>
          )}

          <p className="text-xs text-slate-500">
            No guardamos el número de la tarjeta ni el código de seguridad: del pago solo quedan la franquicia y los
            cuatro últimos dígitos.
          </p>

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg bg-cyan-500 px-4 py-3 font-semibold text-slate-950 disabled:opacity-50"
          >
            {enviando ? 'Procesando...' : `Pagar ${formatoMoneda(totales.total)}`}
          </button>

          {medio === 'tarjeta' && config?.tarjetasDePrueba?.length > 0 && (
            <details className="rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-sm">
              <summary className="cursor-pointer text-slate-300">Tarjetas de prueba</summary>
              <ul className="mt-2 space-y-1 text-slate-400">
                {config.tarjetasDePrueba.map((item) => (
                  <li key={item.numero}>
                    <span className="font-mono text-slate-200">{item.numero}</span> · {item.franquicia} · {item.resultado}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </form>
      )}
    </Modal>
  );
}

export default CheckoutModal;
