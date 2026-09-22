import { useState } from 'react';
import { Link } from 'react-router-dom';
import Modal from './Modal';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { ventasApi } from '../services/api';
import { formatoMoneda } from '../utils/formato';

function IconCart() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M3 4h2l2.2 11h10.2l1.8-8H6" />
      <circle cx="9" cy="19" r="1.4" />
      <circle cx="17" cy="19" r="1.4" />
    </svg>
  );
}

/** Carrito del sitio: botón con el contador y la ventana con el pedido. */
function CartButton() {
  const { items, unidades, total, cambiarCantidad, quitar, vaciar } = useCart();
  const { user } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  const confirmar = async () => {
    setEnviando(true);
    setError('');
    try {
      const data = await ventasApi.pedido({
        items: items.map((item) => ({ tipo: item.tipo, itemId: item.id, cantidad: item.cantidad })),
      });
      const factura = data.factura ? ` Tu factura ${data.factura.numero} ya está en "Mis facturas".` : '';
      setMensaje(`${data.message} Número ${data.venta.numero}.${factura}`);
      vaciar();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setEnviando(false);
    }
  };

  const abrir = () => {
    setMensaje('');
    setError('');
    setAbierto(true);
  };

  return (
    <>
      <button
        type="button"
        onClick={abrir}
        aria-label={`Carrito, ${unidades} artículo(s)`}
        className="relative flex items-center gap-2 rounded-full border border-cyan-400/30 bg-slate-900/60 px-3 py-2 text-sm text-cyan-200 transition hover:border-cyan-300/60 hover:bg-slate-800"
      >
        <IconCart />
        {unidades > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-cyan-400 px-1 text-[11px] font-bold text-slate-950">
            {unidades}
          </span>
        )}
      </button>

      <Modal
        isOpen={abierto}
        onClose={() => setAbierto(false)}
        title="Tu carrito"
        subtitle={unidades ? `${unidades} artículo(s) seleccionados.` : 'Todavía no has agregado nada.'}
      >
        {mensaje && <p className="rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-200">{mensaje}</p>}
        {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={`${item.tipo}-${item.id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/40 p-3"
            >
              <div className="min-w-[11rem] flex-1">
                <p className="font-semibold text-white">{item.nombre}</p>
                <p className="text-xs capitalize text-slate-500">
                  {item.tipo} · {formatoMoneda(item.precio)} c/u
                </p>
              </div>
              <div className="flex items-center gap-3">
                <label className="text-xs text-slate-400">
                  Cantidad
                  <input
                    type="number"
                    min="1"
                    className="field mt-1 w-20"
                    value={item.cantidad}
                    onChange={(event) => cambiarCantidad(item.tipo, item.id, Number(event.target.value))}
                  />
                </label>
                <span className="w-28 text-right font-semibold text-cyan-300">
                  {formatoMoneda(item.precio * item.cantidad)}
                </span>
                <button type="button" className="text-sm text-red-300" onClick={() => quitar(item.tipo, item.id)}>
                  Quitar
                </button>
              </div>
            </li>
          ))}
          {!items.length && <li className="text-sm text-slate-500">Agrega productos o servicios desde el catálogo.</li>}
        </ul>

        {items.length > 0 && (
          <>
            <p className="text-right text-sm text-slate-300">
              Total sin IVA <span className="font-semibold text-cyan-300">{formatoMoneda(total)}</span>
            </p>

            {!user && (
              <p className="rounded-lg bg-cyan-500/10 p-3 text-sm text-cyan-200">
                Para confirmar el pedido primero{' '}
                <Link to="/login" className="font-semibold underline" onClick={() => setAbierto(false)}>
                  inicia sesión
                </Link>
                .
              </p>
            )}

            <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
              <button type="button" className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200" onClick={vaciar}>
                Vaciar carrito
              </button>
              <button
                type="button"
                disabled={!user || enviando}
                onClick={confirmar}
                className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
              >
                {enviando ? 'Enviando...' : 'Confirmar pedido'}
              </button>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}

export default CartButton;
