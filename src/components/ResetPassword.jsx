import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import logo from '../assets/logo.svg';
import Button from './Button';
import Input from './Input';
import PasswordTips from './PasswordTips';
import { authApi } from '../services/api';

function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (!token) {
      setError('El enlace de recuperación no es válido.');
      return;
    }
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError('La contraseña debe tener al menos 8 caracteres, letras y números.');
      return;
    }
    if (password !== confirmation) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setSubmitting(true);
    try {
      const result = await authApi.resetPassword({ token, password });
      setSuccess(result.message);
      setPassword('');
      setConfirmation('');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[70vh] items-center justify-center bg-slate-100 px-4 py-10">
      <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-xl ring-1 ring-slate-200 sm:p-8">
        <div className="mb-6 text-center">
          <img src={logo} alt="Logo SimonC" className="mx-auto h-16 w-16 rounded-full ring-2 ring-cyan-400/50" />
          <p className="mt-4 text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500">Seguridad</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Nueva contraseña</h1>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <Input
            id="reset-password"
            maxLength={20}
            label="Nueva contraseña"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
            autoComplete="new-password"
            hint="Obligatorio: mínimo 8 caracteres, con letras y números."
          />
          <Input
            id="reset-confirmation"
            maxLength={20}
            label="Repetir contraseña"
            type="password"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            placeholder="••••••••"
            autoComplete="new-password"
            hint="Escribe exactamente la misma contraseña de arriba."
          />

          <PasswordTips password={password} />

          {error && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          {success && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{success}</p>}

          <Button type="submit" className="w-full" disabled={submitting || Boolean(success)}>
            {submitting ? 'Guardando...' : 'Cambiar contraseña'}
          </Button>
          <p className="text-center text-sm text-slate-600">
            <Link to="/login" className="font-semibold text-indigo-600 hover:text-indigo-500">Volver a iniciar sesión</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

export default ResetPassword;
