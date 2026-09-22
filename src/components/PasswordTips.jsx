/**
 * Recomendaciones para armar una contraseña segura.
 *
 * Son recomendaciones, no requisitos: cada punto se marca en verde a medida que
 * la contraseña lo cumple, pero ninguno impide registrarse. Lo obligatorio
 * sigue siendo lo que valida el formulario (mínimo 8 caracteres con letras y
 * números), que es lo mismo que exige el backend.
 */
const RECOMENDACIONES = [
  { clave: 'largo', texto: 'Al menos 12 caracteres', cumple: (clave) => clave.length >= 12 },
  { clave: 'mayusculas', texto: 'Alguna letra mayúscula (A-Z)', cumple: (clave) => /[A-ZÁÉÍÓÚÜÑ]/.test(clave) },
  { clave: 'minusculas', texto: 'Alguna letra minúscula (a-z)', cumple: (clave) => /[a-záéíóúüñ]/.test(clave) },
  { clave: 'numeros', texto: 'Algún número (0-9)', cumple: (clave) => /\d/.test(clave) },
  {
    clave: 'simbolos',
    texto: 'Algún símbolo especial ($, @, #, !, etc.)',
    cumple: (clave) => /[^A-Za-z0-9\sÁÉÍÓÚÜÑáéíóúüñ]/.test(clave),
  },
];

function PasswordTips({ password = '' }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
      <p className="text-sm font-semibold text-slate-700">Recomendaciones para una contraseña segura</p>
      <ul className="mt-2 space-y-1.5">
        {RECOMENDACIONES.map(({ clave, texto, cumple }) => {
          const cumplida = cumple(password);
          return (
            <li
              key={clave}
              className={`flex items-start gap-2 text-xs ${cumplida ? 'text-emerald-700' : 'text-slate-600'}`}
            >
              <span aria-hidden="true" className="leading-5">
                {cumplida ? '✓' : '•'}
              </span>
              <span>{texto}</span>
              {/* El lector de pantalla necesita oír el estado, no solo verlo. */}
              <span className="sr-only">{cumplida ? ' (cumplida)' : ' (pendiente)'}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2.5 text-xs text-slate-500">
        No uses tu nombre, tu documento ni fechas de cumpleaños, y no repitas una contraseña que ya uses en otro sitio.
      </p>
    </div>
  );
}

export default PasswordTips;
