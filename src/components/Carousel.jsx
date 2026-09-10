import { useMemo, useState } from 'react';

const slides = [
  {
    src: 'https://images.unsplash.com/photo-1622979135225-d2ba269cf1ac?auto=format&fit=crop&w=1200&q=80',
    title: 'Realidad virtual inmersiva',
    description: 'Experiencias 3D ultra envolventes para entrenar, vender y conectar con clientes.',
  },
  {
    src: 'https://images.unsplash.com/photo-1593508512255-86ab42a8e620?auto=format&fit=crop&w=1200&q=80',
    title: 'Entornos digitales futuristas',
    description: 'Diseñamos mundos interactivos con sensación realista y profundidad visual.',
  },
  {
    src: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80',
    title: 'Simulación espacial',
    description: 'Visualiza productos y escenarios de forma realista antes de lanzarlos al mercado.',
  },
  {
    src: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80',
    title: 'Tecnología aplicada',
    description: 'Integración de inteligencia visual y sensaciones inmersivas para cada proyecto.',
  },
  {
    src: 'https://images.unsplash.com/photo-1535223289827-42f1e9919769?auto=format&fit=crop&w=1200&q=80',
    title: 'Realidad aumentada',
    description: 'Capta atención con experiencias que mezclan lo digital y lo físico en una sola interfaz.',
  },
  {
    src: 'https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=1200&q=80',
    title: 'Innovación visual',
    description: 'Generamos propuestas con estética avanzada y narrativa de marca muy potente.',
  },
  {
    src: 'https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=1200&q=80',
    title: 'Interfaces de alto impacto',
    description: 'Cada pantalla se diseña para ser memorable, clara y completamente envolvente.',
  },
  {
    src: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80',
    title: 'Experiencia de usuario 360°',
    description: 'Explora la diferencia entre un producto estándar y una experiencia realmente inmersiva.',
  },
  {
    src: 'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80',
    title: 'Visualización premium',
    description: 'Presenta ideas complejas con claridad, movimiento y estilo de alto nivel.',
  },
  {
    src: 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80',
    title: 'Digitalización inteligente',
    description: 'Transformamos ideas en soluciones visuales orientadas a resultados y diferenciación.',
  },
];

function Carousel() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const currentSlide = useMemo(() => slides[currentIndex], [currentIndex]);

  const handlePrevious = () => setCurrentIndex((prev) => (prev - 1 + slides.length) % slides.length);
  const handleNext = () => setCurrentIndex((prev) => (prev + 1) % slides.length);

  return (
    <section className="neon-panel rounded-[2rem] p-4 shadow-[0_25px_70px_rgba(34,211,238,0.12)] sm:p-6 lg:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <span className="inline-flex items-center rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-cyan-300">
          Carrusel VR
        </span>
        <div className="flex items-center gap-2">
          <button type="button" onClick={handlePrevious} aria-label="Anterior" className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/30 bg-slate-900/70 text-xl text-cyan-200 transition hover:border-cyan-300 hover:bg-cyan-500/10 hover:text-cyan-100">
            ←
          </button>
          <button type="button" onClick={handleNext} aria-label="Siguiente" className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/30 bg-slate-900/70 text-xl text-cyan-200 transition hover:border-cyan-300 hover:bg-cyan-500/10 hover:text-cyan-100">
            →
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
        <div className="overflow-hidden rounded-[1.7rem] border border-cyan-400/25 bg-slate-900">
          <img src={currentSlide.src} alt={currentSlide.title} className="h-[260px] w-full object-cover sm:h-[340px] lg:h-[420px]" />
        </div>

        <div className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-300">Presentación</p>
          <h2 className="neon-text text-3xl font-black text-transparent bg-gradient-to-r from-cyan-300 via-sky-400 to-violet-400 bg-clip-text sm:text-4xl">{currentSlide.title}</h2>
          <p className="text-base leading-7 text-slate-300">{currentSlide.description}</p>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-3" role="tablist" aria-label="Slides">
        {slides.map((slide, index) => (
          <button
            key={slide.title}
            type="button"
            className={`h-3 w-3 rounded-full transition ${index === currentIndex ? 'bg-gradient-to-r from-cyan-400 to-violet-500 shadow-[0_0_0_4px_rgba(34,211,238,0.2)]' : 'bg-slate-600 hover:bg-slate-400'}`}
            onClick={() => setCurrentIndex(index)}
            aria-label={`Ir a ${slide.title}`}
            aria-selected={index === currentIndex}
          />
        ))}
      </div>
    </section>
  );
}

export default Carousel;
