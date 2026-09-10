import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logo from '../assets/logo.svg';
import Button from './Button';
import Input from './Input';
import RecoverPassword from './RecoverPassword';
import RegisterModal from './RegisterModal';
import { useAuth } from '../context/AuthContext';

const initialForm = {
  email: '',
  password: '',
  remember: true,
};

function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [showRecover, setShowRecover] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [serverError, setServerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const emailRegex = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/, []);

  const validateForm = (currentForm) => {
    const nextErrors = {};

    if (!currentForm.email.trim()) {
      nextErrors.email = 'El correo electrónico es obligatorio.';
    } else if (!emailRegex.test(currentForm.email)) {
      nextErrors.email = 'Correo electrónico inválido.';
    }

    if (!currentForm.password) {
      nextErrors.password = 'La contraseña es obligatoria.';
    } else if (currentForm.password.length < 8) {
      nextErrors.password = 'Debe tener al menos 8 caracteres.';
    }

    return nextErrors;
  };

  const handleChange = (event) => {
    const { name, type, checked, value } = event.target;
    const nextValue = type === 'checkbox' ? checked : value;
    const nextForm = { ...form, [name]: nextValue };
    setForm(nextForm);
    setErrors(validateForm(nextForm));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = validateForm(form);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length === 0) {
      setIsSubmitting(true);
      setServerError('');
      try {
        const user = await login({ email: form.email, password: form.password });
        navigate(user.role === 'Administrador' ? '/panel/admin' : user.role === 'Empleado' ? '/panel/empleado' : '/panel/cliente');
      } catch (error) { setServerError(error.message); }
      finally { setIsSubmitting(false); }
    }
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
            <h1 className="mt-2 text-3xl font-bold text-slate-900">Iniciar sesión</h1>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit} noValidate>
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

            <Input
              id="login-password"
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
            <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting ? 'Validando...' : 'Iniciar sesión'}</Button>

            <div className="text-center text-sm text-slate-600">
              ¿No tienes cuenta?{' '}
              <button
                type="button"
                className="font-semibold text-indigo-600 transition hover:text-indigo-500"
                onClick={() => setIsRegisterOpen(true)}
              >
                Crear una cuenta
              </button>
            </div>
          </form>
        </div>
      </div>

      <RegisterModal isOpen={isRegisterOpen} onClose={() => setIsRegisterOpen(false)} />
    </>
  );
}

export default Login;
