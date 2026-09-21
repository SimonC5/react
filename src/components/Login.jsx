import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logo from '../assets/logo.svg';
import Button from './Button';
import Input from './Input';
import RecoverPassword from './RecoverPassword';
import RegisterModal from './RegisterModal';
import { useAuth } from '../context/AuthContext';
import { rutaDelPanel } from '../utils/rutas';

const PASO_CORREO = 'correo';
const PASO_CLAVE = 'clave';

/**
 * Inicio de sesión en dos pasos, al estilo de Gmail: primero el correo y
 * después la contraseña.
 */
function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [paso, setPaso] = useState(PASO_CORREO);
  const [form, setForm] = useState({ email: '', password: '', remember: true });
  const [errors, setErrors] = useState({});
  const [showRecover, setShowRecover] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [serverError, setServerError] = useState('');
  const [aviso, setAviso] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const emailRegex = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/, []);

  const validarCorreo = (email) => {
    if (!email.trim()) return 'El correo electrónico es obligatorio.';
    if (!emailRegex.test(email)) return 'Correo electrónico inválido.';
    return '';
  };

  const validarClave = (password) => {
    if (!password) return 'La contraseña es obligatoria.';
    if (password.length < 8) return 'Debe tener al menos 8 caracteres.';
    return '';
  };

  const handleChange = (event) => {
    const { name, type, checked, value } = event.target;
    const nextValue = type === 'checkbox' ? checked : value;
    setForm((actual) => ({ ...actual, [name]: nextValue }));
    setServerError('');
    if (name === 'email') setErrors((actuales) => ({ ...actuales, email: validarCorreo(value) || undefined }));
    if (name === 'password') setErrors((actuales) => ({ ...actuales, password: validarClave(value) || undefined }));
  };

  const irAlPasoDeClave = (event) => {
    event.preventDefault();
    const error = validarCorreo(form.email);
    setErrors({ email: error || undefined });
    if (error) return;
    setPaso(PASO_CLAVE);
  };

  const volverAlCorreo = () => {
    setPaso(PASO_CORREO);
    setForm((actual) => ({ ...actual, password: '' }));
    setErrors({});
    setServerError('');
  };

  const iniciarSesion = async (event) => {
    event.preventDefault();
    const error = validarClave(form.password);
    setErrors({ password: error || undefined });
    if (error) return;

    setIsSubmitting(true);
    setServerError('');
    try {
      const user = await login({ email: form.email, password: form.password });
      navigate(rutaDelPanel(user.role));
    } catch (requestError) {
      setServerError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  /** Tras crear la cuenta el usuario cae en el inicio de sesión con su correo puesto. */
  const alRegistrarse = (email) => {
    setIsRegisterOpen(false);
    setForm({ email, password: '', remember: true });
    setErrors({});
    setServerError('');
    setAviso('Cuenta creada con éxito. Escribe tu contraseña para iniciar sesión.');
    setPaso(PASO_CLAVE);
  };

  if (showRecover) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center bg-slate-100 px-4 py-10">
        <RecoverPassword onBack={() => setShowRecover(false)} />
      </div>
    );
  }

  return (
    <>
      <div className="flex min-h-[70vh] items-center justify-center bg-slate-100 px-4 py-10">
        <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-xl ring-1 ring-slate-200 sm:p-8">
          <div className="mb-6 text-center">
            <img src={logo} alt="Logo SimonC" className="mx-auto h-16 w-16 rounded-full ring-2 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.45)]" />
            <p className="mt-4 text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500">SimonC</p>
            <h1 className="mt-2 text-3xl font-bold text-slate-900">
              {paso === PASO_CORREO ? 'Iniciar sesión' : 'Te damos la bienvenida'}
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {paso === PASO_CORREO ? 'Usa tu cuenta de SimonC' : 'Escribe tu contraseña para continuar'}
            </p>
          </div>

          {aviso && <p className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{aviso}</p>}

          {paso === PASO_CORREO ? (
            <form className="space-y-5" onSubmit={irAlPasoDeClave} noValidate>
              <Input
                id="login-email"
                label="Correo electrónico"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                error={errors.email}
                placeholder="nombre@correo.com"
                autoComplete="email"
              />

              <div className="flex items-center justify-between gap-3">
                <button
                  type="button"
                  className="text-sm font-semibold text-indigo-600 transition hover:text-indigo-500"
                  onClick={() => setIsRegisterOpen(true)}
                >
                  Crear una cuenta
                </button>
                <Button type="submit" className="min-w-32">
                  Siguiente
                </Button>
              </div>
            </form>
          ) : (
            <form className="space-y-5" onSubmit={iniciarSesion} noValidate>
              <button
                type="button"
                onClick={volverAlCorreo}
                className="flex w-full items-center gap-2 rounded-full border border-slate-300 px-3 py-2 text-left text-sm text-slate-700 transition hover:bg-slate-50"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
                  {form.email.slice(0, 1).toUpperCase() || 'U'}
                </span>
                <span className="flex-1 truncate">{form.email}</span>
                <span className="text-xs font-semibold text-indigo-600">Cambiar</span>
              </button>

              <Input
                id="login-password"
                autoFocus
                label="Contraseña"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                error={errors.password}
                placeholder="••••••••"
                autoComplete="current-password"
              />

              <div className="flex items-center justify-between gap-3 text-sm">
                <label className="flex items-center gap-2 text-slate-600">
                  <input
                    type="checkbox"
                    name="remember"
                    checked={form.remember}
                    onChange={handleChange}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Recordarme
                </label>

                <button
                  type="button"
                  className="font-medium text-indigo-600 transition hover:text-indigo-500"
                  onClick={() => setShowRecover(true)}
                >
                  ¿Olvidaste tu contraseña?
                </button>
              </div>

              {serverError && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{serverError}</p>}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? 'Validando...' : 'Iniciar sesión'}
              </Button>
            </form>
          )}
        </div>
      </div>

      <RegisterModal isOpen={isRegisterOpen} onClose={() => setIsRegisterOpen(false)} onRegistered={alRegistrarse} />
    </>
  );
}

export default Login;
