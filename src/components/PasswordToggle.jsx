/**
 * Botón del ojo para mostrar u ocultar una contraseña.
 *
 * Se dibuja encima del campo, pegado a la derecha. Lo usan `Input.jsx` y el
 * formulario de usuarios del panel, que no pasa por `Input`.
 */
function PasswordToggle({ visible, onToggle, className = '' }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
      aria-pressed={visible}
      title={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
      className={`absolute inset-y-0 right-0 flex w-11 items-center justify-center text-slate-500 transition hover:text-indigo-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${className}`}
    >
      {visible ? <IconOjoTachado /> : <IconOjo />}
    </button>
  );
}

function IconOjo() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3.2" />
    </svg>
  );
}

function IconOjoTachado() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M9.9 5.7A8.9 8.9 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a16.4 16.4 0 0 1-3 3.8M6.5 7.7A16.2 16.2 0 0 0 2.5 12S6 18.5 12 18.5c1.4 0 2.6-.3 3.7-.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9.9 9.9a3.2 3.2 0 0 0 4.3 4.3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m4 4 16 16" strokeLinecap="round" />
    </svg>
  );
}

export default PasswordToggle;
