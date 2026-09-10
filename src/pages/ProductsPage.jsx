const products = [
  {
    title: 'Branding Premium',
    description: 'Soluciones estratégicas para fortalecer la identidad visual y la percepción de marca en el mercado.',
    image: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=80',
  },
  {
    title: 'E-commerce Avanzado',
    description: 'Plataformas de venta online diseñadas para ofrecer una experiencia fluida, rápida y con enfoque en conversión.',
    image: 'https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80',
  },
  {
    title: 'Landing Pages',
    description: 'Páginas optimizadas para captar leads, comunicar valor y convertir tráfico en oportunidades reales.',
    image: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
  },
  {
    title: 'Dashboard Empresarial',
    description: 'Herramientas analíticas y de gestión para visualizar información clave y tomar decisiones con rapidez.',
    image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80',
  },
];

function ProductsPage() {
  return (
    <section className="space-y-8 py-6">
      <div className="rounded-[2rem] bg-gradient-to-r from-cyan-500/10 via-slate-900 to-violet-500/10 p-8 text-white shadow-[0_25px_80px_rgba(34,211,238,0.12)]">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">Productos</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Nuestra oferta digital</h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Soluciones pensadas para empresas que desean crecer con presencia digital, branding sólido y tecnología que mejore cada interacción.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {products.map(({ title, description, image }) => (
          <article key={title} className="overflow-hidden rounded-3xl border border-slate-700 bg-slate-900/80 shadow-xl shadow-slate-950/20">
            <img src={image} alt={title} className="h-52 w-full object-cover" />
            <div className="space-y-3 p-5">
              <h2 className="text-xl font-semibold text-white">{title}</h2>
              <p className="text-sm leading-6 text-slate-300">{description}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default ProductsPage;
