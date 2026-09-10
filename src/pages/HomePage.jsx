import Carousel from '../components/Carousel';

const productCards = [
  {
    title: 'Branding Premium',
    description: 'Identidad visual sólida para marcas que quieren destacar con un posicionamiento claro y memorable.',
    image: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=900&q=80',
  },
  {
    title: 'E-commerce Shop',
    description: 'Tiendas digitales optimizadas para vender mejor, mejorar la experiencia y aumentar conversiones.',
    image: 'https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80',
  },
  {
    title: 'App Web Corporativa',
    description: 'Soluciones web modernas para negocios que necesitan escalar procesos y mejorar la atención al cliente.',
    image: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80',
  },
];

const serviceCards = [
  'Diseño de interfaces y experiencia de usuario',
  'Desarrollo de sitios web y aplicaciones',
  'Optimización de SEO y estrategia digital',
  'Soporte técnico y mantenimiento continuo',
];

function HomePage() {
  return (
    <section className="space-y-12 py-6">
      <div className="neon-panel rounded-[2rem] bg-gradient-to-br from-cyan-500/10 via-slate-900 to-violet-500/10 p-8 text-white shadow-[0_25px_80px_rgba(34,211,238,0.12)] sm:p-10 lg:p-12">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-300">Página principal</p>
        <h1 className="neon-text max-w-2xl text-4xl font-black tracking-tight text-transparent bg-gradient-to-r from-cyan-300 via-sky-300 to-violet-400 bg-clip-text sm:text-5xl">
          Bienvenido a SimonC
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
          Descubre experiencias digitales futuristas con branding potente, diseño inmersivo y tecnología pensada para conectar con tu audiencia.
        </p>
      </div>

      <div id="productos" className="space-y-4 scroll-mt-24">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-300">Productos</p>
            <h2 className="mt-2 text-3xl font-bold text-white">Soluciones que impulsan tu negocio</h2>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {productCards.map(({ title, description, image }) => (
            <article key={title} className="overflow-hidden rounded-3xl border border-slate-700 bg-slate-900/80 shadow-xl shadow-slate-950/30">
              <img src={image} alt={title} className="h-56 w-full object-cover" />
              <div className="space-y-3 p-5">
                <h3 className="text-xl font-semibold text-white">{title}</h3>
                <p className="text-sm leading-6 text-slate-300">{description}</p>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div id="servicios" className="rounded-[2rem] border border-slate-700 bg-slate-900/80 p-8 shadow-xl shadow-slate-950/20 scroll-mt-24">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-violet-300">Servicios</p>
        <h2 className="mt-2 text-3xl font-bold text-white">Todo lo que necesitas para crecer</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {serviceCards.map((service) => (
            <div key={service} className="rounded-2xl border border-slate-700 bg-slate-950/60 p-4 text-slate-200">
              {service}
            </div>
          ))}
        </div>
      </div>

      <Carousel />
    </section>
  );
}

export default HomePage;
