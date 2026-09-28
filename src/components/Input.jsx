import { useState } from 'react';
import PasswordToggle from './PasswordToggle';

function Input({ label, id, error, hint, className = '', ...props }) {
  const [verClave, setVerClave] = useState(false);
  // Todo campo de contraseña trae su botón del ojo, sin que cada formulario
  // tenga que acordarse de ponerlo.
  const esClave = props.type === 'password';
  const type = esClave && verClave ? 'text' : props.type;

  return (
    <div className="space-y-2">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={id}
          {...props}
          type={type}
          className={`w-full rounded-xl border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100 ${
            error ? 'border-red-300 bg-red-50 focus:border-red-400 focus:ring-red-100' : 'border-slate-200'
          } ${esClave ? 'pr-12' : ''} ${className}`}
        />
        {esClave && <PasswordToggle visible={verClave} onToggle={() => setVerClave((actual) => !actual)} />}
      </div>
      {props.maxLength && <p className="text-xs text-slate-500">Máximo {props.maxLength} caracteres.</p>}
      {hint && <p className="text-xs text-slate-600">{hint}</p>}
      {error && <p className="text-sm font-medium text-red-600">{error}</p>}
    </div>
  );
}

export default Input;
