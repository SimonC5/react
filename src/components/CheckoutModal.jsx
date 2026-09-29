import { useEffect, useMemo, useRef, useState } from 'react';
import Modal from './Modal';
import { pagosApi } from '../services/api';
import { formatoMoneda } from '../utils/formato';

const IVA = 0.19;

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
 * Formulario que se envía a PayU.
 *
 * PayU recibe el pedido por POST, no por dirección, así que se arma un
 * formulario de verdad y se envía solo. Va oculto: para el comprador es un
 * salto directo a la página de PayU.
 */
function FormularioPayU({ datos }) {
  const formulario = useRef(null);

  useEffect(() => {
    if (datos) formulario.current?.submit();
  }, [datos]);

  if (!datos) return null;

  return (
    <form ref={formulario} method="post" action={datos.url} className="hidden">
      {Object.entries(datos.campos).map(([nombre, valor]) => (
        <input key={nombre} type="hidden" name={nombre} value={valor} readOnly />
      ))}
    </form>
  );
}

/**
 * Pasarela de pago de la tienda.
 *
 * Recibe la venta que ya quedó registrada y cobra: o saltando a PayU, o con el
 * formulario de tarjeta de la pasarela simulada. Los importes no se calculan
 * aquí para cobrar: el total lo pone el servidor a partir de la venta. Lo que
 * se ve en pantalla es solo el desglose, para que el comprador sepa qué firma.
 */
function CheckoutModal({ abierto, onClose, venta, factura, onPagada }) {
  const [config, setConfig] = useState(null);
  const [medio, setMedio] = useState('payu');
  const [tarjeta, setTarjeta] = useState({ nombre: '', numero: '', vencimiento: '', cvv: '', cuotas: 1 });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);
  const [saltoPayu, setSaltoPayu] = useState(null);

  useEffect(() => {
    if (!abierto) return;
    setError('');
    setResultado(null);
    setSaltoPayu(null);
    pagosApi.config().then(setConfig).catch(() => setConfig(null));
  }, [abierto]);

  const totales = useMemo(() => {
    const total = Number(venta?.total || 0);
    const base = Number(venta?.subtotal || 0) || total / (1 + IVA);
    return { base, iva: total - base, total };
  }, [venta]);

  const irAPayu = async () => {
    setEnviando(true);
    setError('');
    try {
      setSaltoPayu(await pagosApi.iniciarPayu(venta.id));
    } catch (requestError) {
      setError(requestError.message);
      setEnviando(false);
    }
  };

  const pagarConTarjeta = async (event) => {
    event.preventDefault();
    setEnviando(true);
    setError('');
    try {
      const data = await pagosApi.pagarSimulado({
        ventaId: venta.id,
        nombre: tarjeta.nombre,
        numero: tarjeta.numero.replace(/\s/g, ''),
        vencimiento: tarjeta.vencimiento,
        cvv: tarjeta.cvv,
        cuotas: Number(tarjeta.cuotas) || 1,
      });
      setResultado(data);
      if (data.pago.estado === 'Aprobado') onPagada?.(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setEnviando(false);
    }
  };

  const aprobado = resultado?.pago?.estado === 'Aprobado';

  // En PayU el resultado lo decide el nombre del titular, no la tarjeta, así
  // que la que solo entiende la pasarela simulada no se enseña allí.
  const tarjetasDePrueba = (config?.tarjetasDePrueba || []).filter(
    (item) => medio === 'simulada' || item.donde !== 'simulada',
  );

  return (
    <Modal
      isOpen={abierto}
      onClose={onClose}
      title={resultado ? 'Resultado del pago' : 'Pagar la compra'}
      subtitle={venta ? `Compra ${venta.numero}` : ''}
    >
      <FormularioPayU datos={saltoPayu} />

      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      {resultado ? (
        <div className="space-y-4">
          <div
            className={`rounded-xl p-4 ${aprobado ? 'bg-emerald-500/10 text-emerald-200' : 'bg-amber-500/10 text-amber-200'}`}
          >
            <p className="text-lg font-bold">{aprobado ? 'Pago aprobado' : `Pago ${resultado.pago.estado.toLowerCase()}`}</p>
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
                {resultado.pago.franquicia} terminada en {resultado.pago.ultimosDigitos}
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
            {!aprobado && (
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
        <div className="space-y-5">
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

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setMedio('payu')}
              className={`rounded-lg border px-4 py-2 text-sm ${
                medio === 'payu' ? 'border-cyan-400 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 text-slate-300'
              }`}
            >
              PayU
            </button>
            <button
              type="button"
              onClick={() => setMedio('simulada')}
              className={`rounded-lg border px-4 py-2 text-sm ${
                medio === 'simulada' ? 'border-cyan-400 bg-cyan-500/10 text-cyan-200' : 'border-slate-700 text-slate-300'
              }`}
            >
              Tarjeta de crédito
            </button>
          </div>

          {medio === 'payu' ? (
            <div className="space-y-4">
              <p className="text-sm text-slate-400">
                Vas a salir a la página de PayU para pagar con tarjeta, PSE o en efectivo, y al terminar vuelves aquí.
              </p>
              {config?.payuPruebas && (
                <p className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-200">
                  PayU está en <strong>modo de pruebas</strong>: no se cobra dinero de verdad. Usa una de las tarjetas de
                  prueba de abajo y escribe <strong>APPROVED</strong> en el nombre del titular.
                </p>
              )}
              <button
                type="button"
                disabled={enviando}
                onClick={irAPayu}
                className="w-full rounded-lg bg-cyan-500 px-4 py-3 font-semibold text-slate-950 disabled:opacity-50"
              >
                {enviando ? 'Abriendo PayU...' : `Pagar ${formatoMoneda(totales.total)} con PayU`}
              </button>
            </div>
          ) : (
            <form onSubmit={pagarConTarjeta} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-nombre">
                  Nombre del titular
                </label>
                <input
                  id="pago-nombre"
                  required
                  maxLength="80"
                  className="field"
                  value={tarjeta.nombre}
                  onChange={(event) => setTarjeta({ ...tarjeta, nombre: event.target.value })}
                />
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
                  value={tarjeta.numero}
                  onChange={(event) => setTarjeta({ ...tarjeta, numero: agruparTarjeta(event.target.value) })}
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
                    value={tarjeta.vencimiento}
                    onChange={(event) => setTarjeta({ ...tarjeta, vencimiento: formatearVencimiento(event.target.value) })}
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
                    value={tarjeta.cvv}
                    onChange={(event) => setTarjeta({ ...tarjeta, cvv: event.target.value.replace(/\D/g, '') })}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-slate-300" htmlFor="pago-cuotas">
                    Cuotas
                  </label>
                  <select
                    id="pago-cuotas"
                    className="field"
                    value={tarjeta.cuotas}
                    onChange={(event) => setTarjeta({ ...tarjeta, cuotas: event.target.value })}
                  >
                    {[1, 3, 6, 12, 24].map((numero) => (
                      <option key={numero} value={numero}>
                        {numero}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <p className="text-xs text-slate-500">
                Esta pasarela es una simulación del sitio: no cobra dinero de verdad. No guardamos el número de la tarjeta ni el código de seguridad: del pago solo quedan la franquicia y los
                cuatro últimos dígitos.
              </p>

              <button
                type="submit"
                disabled={enviando}
                className="w-full rounded-lg bg-cyan-500 px-4 py-3 font-semibold text-slate-950 disabled:opacity-50"
              >
                {enviando ? 'Procesando...' : `Pagar ${formatoMoneda(totales.total)}`}
              </button>
            </form>
          )}

          {tarjetasDePrueba.length > 0 && (
            <details className="rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-sm">
              <summary className="cursor-pointer text-slate-300">Tarjetas de prueba</summary>
              <ul className="mt-2 space-y-1 text-slate-400">
                {tarjetasDePrueba.map((item) => (
                  <li key={item.numero}>
                    <span className="font-mono text-slate-200">{item.numero}</span> · {item.franquicia} ·{' '}
                    {medio === 'payu' ? 'Sirve en PayU' : item.resultado}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </Modal>
  );
}

export default CheckoutModal;
