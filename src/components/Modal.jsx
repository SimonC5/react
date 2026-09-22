import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import logo from '../assets/logo.svg';

/**
 * Ventana emergente común a todo el sitio.
 *
 * Lleva siempre el logo de SimonC en la cabecera y se cierra con Escape o
 * pulsando fuera, para que todas se comporten igual. La cabecera queda fija y
 * solo se desplaza el contenido, así el título nunca se sale de la pantalla.
 *
 * Se dibuja al final del <body>: si se quedara dentro del header, que lleva
 * "backdrop-blur", el navegador la recortaría contra esa franja.
 */
function Modal({ isOpen, onClose, title, subtitle, children, footer, size = 'md' }) {
  useEffect(() => {
    if (!isOpen) return undefined;

    const alPulsarEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };

    // Mientras la ventana está abierta la página de atrás no se desplaza.
    const desbordeAnterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', alPulsarEscape);
    return () => {
      document.body.style.overflow = desbordeAnterior;
      document.removeEventListener('keydown', alPulsarEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const anchos = { sm: 'max-w-md', md: 'max-w-2xl', lg: 'max-w-4xl' };

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`flex max-h-[92vh] w-full flex-col ${anchos[size] || anchos.md} rounded-3xl border border-slate-700 bg-slate-900 shadow-2xl`}
      >
        <div className="flex items-start justify-between gap-3 p-5 pb-4 sm:p-7 sm:pb-5">
          <div className="flex items-center gap-4">
            <img
              src={logo}
              alt="Logo SimonC"
              className="h-12 w-12 rounded-full ring-2 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.45)]"
            />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">SimonC</p>
              <h2 className="mt-1 text-xl font-bold text-white">{title}</h2>
              {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar ventana"
            className="rounded-full bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-slate-700"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4 overflow-y-auto px-5 pb-5 sm:px-7 sm:pb-7">{children}</div>

        {footer && (
          <div className="flex flex-col-reverse gap-3 border-t border-slate-800 p-5 sm:flex-row sm:justify-end sm:px-7">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

export default Modal;
