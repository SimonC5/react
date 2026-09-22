import { useEffect, useState } from 'react';
import { catalogoApi } from '../services/api';
import { useCart } from '../context/CartContext';
import VrHeadset from '../components/VrHeadset';
import { formatoMoneda } from '../utils/formato';

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
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Gafas de realidad virtual</h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Visores para jugar, entrenar y trabajar: desde el modelo autónomo que se usa sin computador hasta los de 8K para
          diseño e ingeniería. Agrégalos al carrito y confirma tu pedido en un paso.
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-500/10 p-4 text-sm text-red-300">{error}</p>}
      {agregado && (
        <p className="rounded-xl bg-emerald-500/10 p-4 text-sm text-emerald-200">
          "{agregado}" se agregó al carrito. Ábrelo arriba para confirmar el pedido.
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {productos.map((producto, posicion) => (
          <article
            key={producto.id}
            className="flex flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-900/80 shadow-xl shadow-slate-950/20"
          >
            <VrHeadset variante={posicion} className="h-52 w-full object-cover" />
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
