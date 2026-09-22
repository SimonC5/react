import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { rutaDelPanel } from '../utils/rutas';

/**
 * Nombre del usuario en el header. Al hacer clic despliega el acceso al panel.
 * La sesión se cierra desde el propio panel, no desde aquí.
 */
function UserMenu() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const contenedorRef = useRef(null);

  useEffect(() => {
    if (!abierto) return undefined;

    const alHacerClicFuera = (evento) => {
      if (!contenedorRef.current?.contains(evento.target)) setAbierto(false);
    };
    const alPresionarEscape = (evento) => {
      if (evento.key === 'Escape') setAbierto(false);
    };

    document.addEventListener('mousedown', alHacerClicFuera);
    document.addEventListener('keydown', alPresionarEscape);
    return () => {
      document.removeEventListener('mousedown', alHacerClicFuera);
      document.removeEventListener('keydown', alPresionarEscape);
    };
  }, [abierto]);

  if (!user) return null;

  const iniciales = `${user.name?.[0] ?? ''}${user.lastName?.[0] ?? ''}`.toUpperCase() || 'U';

  const irAlPanel = () => {
    setAbierto(false);
    navigate(rutaDelPanel(user.role));
  };

  return (
    <div ref={contenedorRef} className="relative">
      <button
        type="button"
        onClick={() => setAbierto((valor) => !valor)}
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-label={`Menú de ${user.name}`}
        className="flex items-center gap-2 rounded-full border border-cyan-400/30 bg-slate-900/60 py-1.5 pl-1.5 pr-4 text-sm text-cyan-200 transition hover:border-cyan-300/60 hover:bg-slate-800"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-violet-500 text-xs font-bold text-slate-950">
          {iniciales}
        </span>
        <span className="font-medium">{user.name}</span>
      </button>

      {abierto && (
        <div className="absolute right-0 z-50 mt-2 w-60 rounded-2xl border border-slate-700 bg-slate-900 p-2 shadow-2xl">
          <div className="border-b border-slate-800 px-3 py-2">
            <p className="truncate font-semibold text-white">
              {user.name} {user.lastName}
            </p>
            <p className="truncate text-xs text-slate-400">{user.email}</p>
            <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300">{user.role}</p>
          </div>

          <button
            type="button"
            onClick={irAlPanel}
            className="mt-2 w-full rounded-xl bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            Entrar al panel
          </button>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
