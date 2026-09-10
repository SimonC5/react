import { Link } from 'react-router-dom';
import logo from '../assets/logo.svg';

const services = ['Desarrollo web', 'Branding digital', 'E-commerce', 'Marketing UX'];
const quickLinks = [
  { label: 'Inicio', to: '/' },
  { label: 'Productos', to: '/#productos' },
  { label: 'Servicios', to: '/#servicios' },
  { label: 'Quiénes Somos', to: '/quienes-somos' },
  { label: 'Contacto', to: '/contacto' },
];
const socials = [
  { name: 'Instagram', handle: '@simoncstudio', href: 'https://instagram.com/simoncstudio', icon: 'instagram' },
  { name: 'Facebook', handle: '@simoncstudio', href: 'https://facebook.com/simoncstudio', icon: 'facebook' },
  { name: 'LinkedIn', handle: 'company/simonc-studio', href: 'https://linkedin.com/company/simonc-studio', icon: 'linkedin' },
  { name: 'X', handle: '@simoncstudio', href: 'https://x.com/simoncstudio', icon: 'x' },
];

const contacts = [
  { label: 'Teléfono', value: '+57 300 123 4567' },
  { label: 'Correo', value: 'hola@simoncstudio.com' },
  { label: 'Dirección', value: 'Bogotá, Colombia' },
];

function SocialIcon({ type }) {
  const common = 'h-5 w-5 fill-current';

  if (type === 'instagram') {
    return (
      <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
        <path d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm0 2a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H7Zm5 3.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 0 1 12 7.5Zm0 2A2.5 2.5 0 1 0 14.5 12 2.5 2.5 0 0 0 12 9.5Zm5-3.2a1.1 1.1 0 1 1-1.1-1.1 1.1 1.1 0 0 1 1.1 1.1Z" />
      </svg>
    );
  }

  if (type === 'facebook') {
    return (
      <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
        <path d="M13.5 22v-8h2.7l.4-3.2h-3.1V7.5c0-.9.3-1.5 1.6-1.5H17V3.1c-.3 0-1.3-.1-2.4-.1-2.4 0-4 1.5-4 4.2V10.8H8v3.2h2.6v8h2.9Z" />
      </svg>
    );
  }

  if (type === 'linkedin') {
    return (
      <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
        <path d="M6.94 8.5A1.56 1.56 0 1 1 6.9 5.4a1.56 1.56 0 0 1 .04 3.1ZM5.5 10h2.9v9H5.5v-9Zm5.1 0h2.8v1.2h.1c.4-.7 1.4-1.5 2.9-1.5 3.1 0 3.7 2 3.7 4.7V19h-2.9v-17.6c0-1.2-.1-2.8-1.7-2.8-1.7 0-2 1.3-2 2.7V19h-2.9v-9Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
      <path d="M18.9 2h3.2l-7 8 8.3 12h-6.5l-5.1-7.5L6 22H2.7l7.5-8.6L2.4 2h6.7l4.6 6.8L18.9 2Zm-1.1 18.1h1.8L7.2 3.8H5.3l12.5 16.3Z" />
    </svg>
  );
}

function Footer() {
  return (
    <footer className="border-t border-cyan-500/20 bg-slate-950/90">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-10 text-sm text-slate-300 sm:px-6 lg:grid-cols-[1.3fr_0.9fr_0.8fr_1.1fr_1.1fr] lg:px-8">
        <div>
          <div className="mb-4 flex items-center gap-3">
            <img src={logo} alt="Logo SimonC" className="h-12 w-12 rounded-full ring-2 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.45)]" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-cyan-300">Digital studio</p>
              <p className="text-xl font-black tracking-[0.18em] text-transparent bg-gradient-to-r from-cyan-300 via-sky-400 to-violet-400 bg-clip-text">
                SIMONC
              </p>
            </div>
          </div>
          <p className="max-w-sm leading-7 text-slate-300">
            Creamos experiencias digitales que conectan marcas con personas mediante diseño estratégico, tecnología moderna y soluciones enfocadas en resultados.
          </p>
        </div>

        <div>
          <h3 className="mb-4 text-base font-semibold uppercase tracking-[0.2em] text-white">Servicios</h3>
          <ul className="space-y-3">
            {services.map((service) => (
              <li key={service}>{service}</li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="mb-4 text-base font-semibold uppercase tracking-[0.2em] text-white">Enlaces</h3>
          <ul className="space-y-3">
            {quickLinks.map(({ label, to }) => (
              <li key={label}>
                <Link to={to} className="transition hover:text-cyan-200">
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="mb-4 text-base font-semibold uppercase tracking-[0.2em] text-white">Contacto</h3>
          <ul className="space-y-3">
            {contacts.map(({ label, value }) => (
              <li key={label}>
                <span className="font-medium text-white">{label}: </span>
                {value}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="mb-4 text-base font-semibold uppercase tracking-[0.2em] text-white">Redes sociales</h3>
          <div className="space-y-3">
            {socials.map(({ name, handle, href, icon }) => (
              <a
                key={name}
                href={href}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-3 rounded-xl border border-cyan-400/20 bg-slate-900/80 px-3 py-2 transition hover:border-cyan-300 hover:bg-slate-800"
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-200">
                  <SocialIcon type={icon} />
                </span>
                <span>
                  <span className="block font-medium text-white">{name}</span>
                  <span className="block text-xs text-slate-400">{handle}</span>
                </span>
              </a>
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-slate-700/80">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-4 text-center text-sm text-slate-400 sm:px-6 lg:flex-row lg:px-8">
          <p>© {new Date().getFullYear()} SimonC Studio. Todos los derechos reservados.</p>
          <p>Diseño y desarrollo con React + Vite</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
