function AboutPage() {
  return (
    <section className="space-y-8 py-6">
      <div className="neon-panel rounded-[2rem] p-8 shadow-[0_20px_60px_rgba(34,211,238,0.12)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Quiénes Somos</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Conoce a SimonC</h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-300">
          Somos un equipo creativo dedicado a desarrollar experiencias digitales con impacto visual, navegación clara y tecnología inmersiva para transformar la presencia de tu marca.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {[
          {
            title: 'Misión',
            text: 'Transformar ideas en productos digitales que conecten con los usuarios y generen resultados reales.',
          },
          {
            title: 'Visión',
            text: 'Ser la referencia regional en experiencias web inmersivas, modernas y centradas en la usabilidad.',
          },
          {
            title: 'Valores',
            text: 'Creatividad, colaboración, calidad y atención a los detalles en cada proyecto.',
          },
        ].map((item) => (
          <article key={item.title} className="glass-card rounded-[1.75rem] p-6 shadow-[0_18px_40px_rgba(15,23,42,0.4)]">
            <h2 className="text-2xl font-bold text-white">{item.title}</h2>
            <p className="mt-3 text-base leading-7 text-slate-300">{item.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default AboutPage;
