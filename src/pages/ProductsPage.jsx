import { useEffect, useState } from 'react';
import { catalogoApi } from '../services/api';
import { useCart } from '../context/CartContext';
import { formatoMoneda } from '../utils/formato';

// Imagen de cada producto del catálogo. Si el administrador crea uno nuevo se
// usa la de reserva, así la página nunca queda con un hueco.
const imagenes = {
  'Branding Premium': 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=80',
  'E-commerce Avanzado': 'https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80',
  'Landing Pages': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
  'Dashboard Empresarial': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80',
};
const imagenPorDefecto = 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80';

function ProductsPage() {
  const { agregar } = useCart();
  const [productos, setProductos] = useState([]);
  const [error, setError] = useState('');
  const [agregado, setAgregado] = useState('');

  useEffect(() => {
    catalogoApi
      .publico()
      .then((data) => setProductos(data.productos || []))
      .catch((requestError) => setError(requestError.message));
  }, []);

  const alAgregar = (producto) => {
    agregar({ tipo: 'producto', id: producto.id, nombre: producto.name, precio: Number(producto.price || 0) });
    setAgregado(producto.name);
  };

  return (
    <section className="space-y-8 py-6">
      <div className="rounded-[2rem] bg-gradient-to-r from-cyan-500/10 via-slate-900 to-violet-500/10 p-8 text-white shadow-[0_25px_80px_rgba(34,211,238,0.12)]">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">Productos</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Nuestra oferta digital</h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Soluciones pensadas para empresas que desean crecer con presencia digital, branding sólido y tecnología que mejore cada interacción.
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-500/10 p-4 text-sm text-red-300">{error}</p>}
      {agregado && (
        <p className="rounded-xl bg-emerald-500/10 p-4 text-sm text-emerald-200">
          "{agregado}" se agregó al carrito. Ábrelo arriba para confirmar el pedido.
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {productos.map((producto) => (
          <article
            key={producto.id}
            className="flex flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-900/80 shadow-xl shadow-slate-950/20"
          >
            <img src={imagenes[producto.name] || imagenPorDefecto} alt={producto.name} className="h-52 w-full object-cover" />
            <div className="flex flex-1 flex-col gap-3 p-5">
              <h2 className="text-xl font-semibold text-white">{producto.name}</h2>
              <p className="flex-1 text-sm leading-6 text-slate-300">{producto.description}</p>
              <p className="text-lg font-bold text-cyan-300">{formatoMoneda(producto.price)}</p>
              <button
                type="button"
                onClick={() => alAgregar(producto)}
                className="rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110"
              >
                Agregar al carrito
              </button>
            </div>
          </article>
        ))}
        {!productos.length && !error && <p className="text-sm text-slate-400">Cargando el catálogo...</p>}
      </div>
    </section>
  );
}

export default ProductsPage;
