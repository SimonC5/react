const services = [
  {
    title: 'Desarrollo web',
    description: 'Sitios y aplicaciones web modernas, rápidas y preparadas para ofrecer una excelente experiencia al usuario.',
  },
  {
    title: 'Branding digital',
    description: 'Estrategias visuales y de posicionamiento digital para construir una marca clara, confiable y memorable.',
  },
  {
    title: 'E-commerce',
    description: 'Tiendas online con experiencia optimizada, pagos seguros y diseño orientado a la conversión.',
  },
  {
    title: 'Marketing UX',
    description: 'Diseño centrado en la experiencia del usuario para mejorar la interacción, la retención y el rendimiento.',
  },
];

function ServicesPage() {
  return (
    <section className="space-y-8 py-6">
      <div className="rounded-[2rem] bg-gradient-to-r from-violet-500/10 via-slate-900 to-cyan-500/10 p-8 text-white shadow-[0_25px_80px_rgba(168,85,247,0.12)]">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-300">Servicios</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Potenciamos tus ideas</h1>
        <p className="mt-4 max-w-2xl text-slate-300">
          Ofrecemos acompañamiento estratégico y técnico para llevar tus proyectos digitales desde la idea hasta una solución lista para crecer.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {services.map(({ title, description }) => (
          <div key={title} className="rounded-3xl border border-slate-700 bg-slate-900/80 p-6 shadow-xl shadow-slate-950/20">
            <div className="mb-4 inline-flex rounded-full border border-violet-400/40 bg-violet-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-violet-200">
              {title}
            </div>
            <p className="text-base leading-7 text-slate-300">{description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ServicesPage;
