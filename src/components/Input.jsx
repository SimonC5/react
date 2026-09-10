function Input({ label, id, error, className = '', ...props }) {
  return (
    <div className="space-y-2">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700">
          {label}
        </label>
      )}
      <input
        id={id}
        className={`w-full rounded-xl border bg-slate-50 px-3.5 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-100 ${
          error ? 'border-red-300 bg-red-50 focus:border-red-400 focus:ring-red-100' : 'border-slate-200'
        } ${className}`}
        {...props}
      />
      {props.maxLength && <p className="text-xs text-slate-500">Máximo {props.maxLength} caracteres.</p>}
      {error && <p className="text-sm font-medium text-red-600">{error}</p>}
    </div>
  );
}

export default Input;
