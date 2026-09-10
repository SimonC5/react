import { NavLink } from 'react-router-dom';
import logo from '../assets/logo.svg';
import Button from './Button';
import { useAuth } from '../context/AuthContext';

function Header() {
  const { user, logout } = useAuth();
  return (
    <header className="sticky top-0 z-40 border-b border-cyan-500/20 bg-slate-950/75 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <NavLink to="/" className="flex items-center gap-3">
          <img src={logo} alt="Logo SimonC" className="h-12 w-12 rounded-full ring-2 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.45)]" />
          <div className="leading-none">
            <span className="block text-[10px] font-semibold uppercase tracking-[0.38em] text-cyan-300">Digital Studio</span>
            <span className="neon-text block text-xl font-black tracking-[0.18em] text-transparent bg-gradient-to-r from-cyan-300 via-sky-400 to-violet-400 bg-clip-text">
              SIMONC
            </span>
          </div>
        </NavLink>

        <nav className="hidden items-center gap-2 md:flex" aria-label="Menú principal">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30' : 'text-slate-300 hover:bg-slate-800 hover:text-cyan-200'
              }`
            }
          >
            Inicio
          </NavLink>
          <NavLink
            to="/productos"
            className={({ isActive }) =>
              `rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30' : 'text-slate-300 hover:bg-slate-800 hover:text-cyan-200'
              }`
            }
          >
            Productos
          </NavLink>
          <NavLink
            to="/servicios"
            className={({ isActive }) =>
              `rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30' : 'text-slate-300 hover:bg-slate-800 hover:text-cyan-200'
              }`
            }
          >
            Servicios
          </NavLink>
          <NavLink
            to="/quienes-somos"
            className={({ isActive }) =>
              `rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30' : 'text-slate-300 hover:bg-slate-800 hover:text-cyan-200'
              }`
            }
          >
            Quiénes Somos
          </NavLink>
          <NavLink
            to="/contacto"
            className={({ isActive }) =>
              `rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30' : 'text-slate-300 hover:bg-slate-800 hover:text-cyan-200'
              }`
            }
          >
            Contacto
          </NavLink>
        </nav>

        <div className="flex items-center gap-3">
          {user ? <><NavLink to={user.role === 'Administrador' ? '/panel/admin' : user.role === 'Empleado' ? '/panel/empleado' : '/panel/cliente'} className="hidden text-sm text-cyan-300 sm:block">Bienvenido, {user.name}</NavLink><Button variant="secondary" onClick={logout} className="rounded-full px-4 py-2 text-sm">Cerrar sesión</Button></> : <NavLink to="/login">
            <Button variant="primary" className="neon-button rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 px-5 py-2.5 text-sm text-white shadow-[0_0_25px_rgba(45,212,191,0.35)] hover:brightness-110">
              Iniciar sesión
            </Button>
          </NavLink>}
        </div>
      </div>
    </header>
  );
}

export default Header;
