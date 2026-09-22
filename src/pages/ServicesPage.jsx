import { useEffect, useState } from 'react';
import { catalogoApi } from '../services/api';
import { useCart } from '../context/CartContext';
import { formatoMoneda } from '../utils/formato';

function ServicesPage() {
  const { agregar } = useCart();
  const [servicios, setServicios] = useState([]);
  const [error, setError] = useState('');
  const [agregado, setAgregado] = useState('');

  useEffect(() => {
    catalogoApi
      .publico()
      .then((data) => setServicios(data.servicios || []))
      .catch((requestError) => setError(requestError.message));
  }, []);

  const alAgregar = (servicio) => {
    agregar({ tipo: 'servicio', id: servicio.id, nombre: servicio.name, precio: Number(servicio.price || 0) });
    setAgregado(servicio.name);
  };

  return (
    <section className="space-y-8 py-6">
      <div className="rounded-[2rem] bg-gradient-to-r from-violet-500/10 via-slate-900 to-cyan-500/10 p-8 text-white shadow-[0_25px_80px_rgba(168,85,247,0.12)]">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-300">Servicios</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Servicios de realidad virtual</h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Instalación, capacitación, desarrollo a medida, tours 360 y simuladores de entrenamiento. Todo lo que hace falta
          para que la realidad virtual funcione de verdad en tu empresa.
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-500/10 p-4 text-sm text-red-300">{error}</p>}
      {agregado && (
        <p className="rounded-xl bg-emerald-500/10 p-4 text-sm text-emerald-200">
          "{agregado}" se agregó al carrito. Ábrelo arriba para confirmar el pedido.
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {servicios.map((servicio) => (
          <div key={servicio.id} className="flex flex-col rounded-3xl border border-slate-700 bg-slate-900/80 p-6 shadow-xl shadow-slate-950/20">
            <div className="mb-4 inline-flex self-start rounded-full border border-violet-400/40 bg-violet-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-violet-200">
              {servicio.name}
            </div>
            <p className="flex-1 text-base leading-7 text-slate-300">{servicio.description}</p>
            <p className="mt-4 text-lg font-bold text-cyan-300">{formatoMoneda(servicio.price)}</p>
            <button
              type="button"
              onClick={() => alAgregar(servicio)}
              className="mt-4 self-start rounded-full bg-gradient-to-r from-violet-500 to-cyan-500 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
            >
              Agregar al carrito
            </button>
          </div>
        ))}
        {!servicios.length && !error && <p className="text-sm text-slate-400">Cargando el catálogo...</p>}
      </div>
    </section>
  );
}

export default ServicesPage;
