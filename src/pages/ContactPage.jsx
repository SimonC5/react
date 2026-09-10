function ContactPage() {
  return (
    <section className="space-y-8 py-6">
      <div className="neon-panel rounded-[2rem] p-8 shadow-[0_20px_60px_rgba(34,211,238,0.12)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Contacto</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-white sm:text-5xl">Hablemos sobre tu proyecto</h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-300">
          Completa el formulario para recibir una propuesta personalizada y llevar tu presencia digital al siguiente nivel.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="glass-card rounded-[1.75rem] bg-gradient-to-br from-cyan-500/10 to-violet-500/10 p-6 text-slate-100 shadow-xl">
          <h2 className="text-2xl font-bold text-white">Datos de contacto</h2>
          <div className="mt-5 space-y-4 text-slate-200">
            <p><span className="font-semibold text-white">Correo:</span> contacto@simonc.dev</p>
            <p><span className="font-semibold text-white">Teléfono:</span> +52 55 1234 5678</p>
            <p><span className="font-semibold text-white">Ubicación:</span> Ciudad de México, México</p>
          </div>
        </div>

        <form className="glass-card space-y-4 rounded-[1.75rem] p-6 shadow-[0_20px_50px_rgba(15,23,42,0.4)]">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm font-medium text-slate-200">
              Nombre
              <input type="text" name="name" placeholder="Tu nombre" className="w-full rounded-xl border border-cyan-400/20 bg-slate-950/60 px-3.5 py-2.5 text-slate-100 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-500/10" />
            </label>
            <label className="space-y-2 text-sm font-medium text-slate-200">
              Correo electrónico
              <input type="email" name="email" placeholder="tu@email.com" className="w-full rounded-xl border border-cyan-400/20 bg-slate-950/60 px-3.5 py-2.5 text-slate-100 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-500/10" />
            </label>
          </div>
          <label className="space-y-2 text-sm font-medium text-slate-200">
            Mensaje
            <textarea name="message" placeholder="Escribe tu mensaje" rows="5" className="w-full rounded-xl border border-cyan-400/20 bg-slate-950/60 px-3.5 py-2.5 text-slate-100 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-500/10" />
          </label>
          <button type="submit" className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 text-sm font-semibold text-white shadow-[0_0_25px_rgba(45,212,191,0.35)] transition hover:brightness-110">Enviar mensaje</button>
        </form>
      </div>
    </section>
  );
}

export default ContactPage;
