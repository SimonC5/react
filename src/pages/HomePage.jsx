import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Carousel from '../components/Carousel';
import VrHeadset from '../components/VrHeadset';
import { catalogoApi } from '../services/api';
import { formatoMoneda } from '../utils/formato';

function HomePage() {
  const [destacados, setDestacados] = useState({ productos: [], servicios: [] });

  useEffect(() => {
    catalogoApi
      .publico()
      .then((data) => setDestacados({ productos: data.productos || [], servicios: data.servicios || [] }))
      // La portada no muestra errores: si la API no responde, se ve sin destacados.
      .catch(() => setDestacados({ productos: [], servicios: [] }));
  }, []);

  return (
    <section className="space-y-12 py-6">
      <div className="neon-panel rounded-[2rem] bg-gradient-to-br from-cyan-500/10 via-slate-900 to-violet-500/10 p-8 text-white shadow-[0_25px_80px_rgba(34,211,238,0.12)] sm:p-10 lg:p-12">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">Página principal</p>
        <h1 className="neon-text max-w-2xl text-4xl font-black tracking-tight text-transparent bg-gradient-to-r from-cyan-300 via-sky-300 to-violet-400 bg-clip-text sm:text-5xl">
          Bienvenido a SimonC
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
          Tu tienda de realidad virtual: visores para jugar, entrenar y trabajar, más los servicios que hacen falta para
          ponerlos a funcionar.
        </p>
      </div>

      <div id="productos" className="space-y-4 scroll-mt-24">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-300">Productos</p>
            <h2 className="mt-2 text-3xl font-bold text-white">Gafas destacadas</h2>
          </div>
          <Link to="/productos" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
            Ver todo el catálogo
          </Link>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {destacados.productos.slice(0, 3).map((producto, posicion) => (
            <article key={producto.id} className="overflow-hidden rounded-3xl border border-slate-700 bg-slate-900/80 shadow-xl shadow-slate-950/30">
              <VrHeadset variante={posicion} className="h-56 w-full object-cover" />
              <div className="space-y-3 p-5">
                <h3 className="text-xl font-semibold text-white">{producto.name}</h3>
                <p className="text-sm leading-6 text-slate-300">{producto.description}</p>
                <p className="text-lg font-bold text-cyan-300">{formatoMoneda(producto.price)}</p>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div id="servicios" className="rounded-[2rem] border border-slate-700 bg-slate-900/80 p-8 shadow-xl shadow-slate-950/20 scroll-mt-24">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-violet-300">Servicios</p>
        <h2 className="mt-2 text-3xl font-bold text-white">Todo lo que necesitas para empezar</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {destacados.servicios.slice(0, 6).map((servicio) => (
            <div key={servicio.id} className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4 text-slate-200">
              {servicio.name}
            </div>
          ))}
        </div>
        <Link to="/servicios" className="mt-6 inline-block text-sm font-semibold text-violet-300 hover:text-violet-200">
          Ver todos los servicios
        </Link>
      </div>

      <Carousel />
    </section>
  );
}

export default HomePage;
