import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { pagosApi } from '../services/api';
import { formatoMoneda } from '../utils/formato';

const TITULOS = {
  Aprobado: 'Pago aprobado',
  Rechazado: 'Pago rechazado',
  Pendiente: 'Pago pendiente',
  Error: 'La pasarela reportó un error',
};

const COLORES = {
  Aprobado: 'bg-emerald-500/10 text-emerald-200',
  Rechazado: 'bg-red-500/10 text-red-300',
  Pendiente: 'bg-amber-500/10 text-amber-200',
  Error: 'bg-red-500/10 text-red-300',
};

/**
 * Pantalla a la que PayU devuelve el navegador después de cobrar.
 *
 * Lo que trae la dirección no se cree por sí solo: se le manda entero al
 * backend, que comprueba la firma de PayU antes de dar el pago por bueno. Sin
 * eso, cualquiera podría abrir esta página con "transactionState=4" y marcarse
 * la compra como pagada.
 */
function PaymentResultPage() {
  const [parametros] = useSearchParams();
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    const datos = Object.fromEntries(parametros.entries());
    if (!datos.referenceCode) {
      setError('Esta página se abre al volver de la pasarela de pago.');
      setCargando(false);
      return;
    }
    pagosApi
      .confirmarPayu(datos)
      .then(setResultado)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setCargando(false));
  }, [parametros]);

  if (cargando) {
    return <div className="py-20 text-center text-slate-400">Confirmando el pago...</div>;
  }

  const estado = resultado?.pago?.estado;

  return (
    <section className="mx-auto max-w-2xl py-12">
      <div className="space-y-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
        <h1 className="text-2xl font-bold text-white">
          {error ? 'No se pudo confirmar el pago' : TITULOS[estado] || 'Resultado del pago'}
        </h1>

        {error ? (
          <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>
        ) : (
          <>
            <p className={`rounded-lg p-3 text-sm ${COLORES[estado] || 'bg-slate-800 text-slate-200'}`}>
              {resultado.message}
            </p>

            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Referencia</dt>
                <dd className="font-semibold text-white">{resultado.pago.referencia}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Valor</dt>
                <dd className="font-semibold text-cyan-300">{formatoMoneda(resultado.pago.monto)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Compra</dt>
                <dd className="text-slate-200">{resultado.venta?.numero}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Estado de la compra</dt>
                <dd className="text-slate-200">{resultado.venta?.estado}</dd>
              </div>
            </dl>
          </>
        )}

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            to="/panel/cliente"
            className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Ver mis compras
          </Link>
          <Link to="/productos" className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200">
            Seguir comprando
          </Link>
        </div>
      </div>
    </section>
  );
}

export default PaymentResultPage;
