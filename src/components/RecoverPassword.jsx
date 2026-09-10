import { useMemo, useState } from 'react';
import logo from '../assets/logo.svg';
import Button from './Button';
import Input from './Input';
import { authApi } from '../services/api';

function RecoverPassword({ onBack }) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const emailRegex = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/, []);

  const validateEmail = (value) => {
    if (!value.trim()) return 'El correo electrónico es obligatorio.';
    if (!emailRegex.test(value)) return 'El formato del correo es inválido.';
    return '';
  };

  const handleChange = (event) => {
    const nextValue = event.target.value;
    setEmail(nextValue);
    setError(validateEmail(nextValue));
    setSuccess('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextError = validateEmail(email);
    setError(nextError);

    if (!nextError) {
      setSubmitting(true);
      try { const result = await authApi.recover(email); setSuccess(result.message); setEmail(''); }
      catch (requestError) { setError(requestError.message); }
      finally { setSubmitting(false); }
    }
  };

  return (
    <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-xl ring-1 ring-slate-200 sm:p-8">
      <div className="mb-6 text-center">
        <img src={logo} alt="Logo SimonC" className="mx-auto h-16 w-16 rounded-full ring-2 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.45)]" />
        <p className="mt-4 text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500">Seguridad</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-900">Recuperar contraseña</h2>
      </div>

      <p className="mb-4 text-sm text-slate-600">
        Se le enviará un correo electrónico para recuperar la cuenta perdida.
      </p>

      <form className="space-y-5" onSubmit={handleSubmit} noValidate>
        <Input
          id="recover-email"
          label="Correo electrónico"
          type="email"
          value={email}
          onChange={handleChange}
          error={error}
          placeholder="nombre@correo.com"
          autoComplete="email"
        />

        {success && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
            {success}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button type="submit" className="flex-1" disabled={submitting}>{submitting ? 'Enviando...' : 'Recuperar contraseña'}</Button>
          <Button type="button" variant="secondary" className="flex-1" onClick={onBack}>
            Volver
          </Button>
        </div>
      </form>
    </div>
  );
}

export default RecoverPassword;
