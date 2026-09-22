/**
 * Ilustración de unas gafas de realidad virtual.
 *
 * Se dibuja aquí mismo en vez de traer una foto de internet: así el catálogo
 * se ve igual aunque no haya conexión y nunca queda una imagen rota. El color
 * cambia con "variante" (la posición en el catálogo), para que dos tarjetas
 * vecinas nunca se vean iguales.
 */
const paletas = [
  ['#22d3ee', '#818cf8'],
  ['#a78bfa', '#f472b6'],
  ['#34d399', '#22d3ee'],
  ['#f59e0b', '#f472b6'],
  ['#38bdf8', '#2dd4bf'],
  ['#c084fc', '#38bdf8'],
  ['#fb7185', '#f59e0b'],
  ['#4ade80', '#a3e635'],
  ['#60a5fa', '#a78bfa'],
  ['#2dd4bf', '#eab308'],
];

function VrHeadset({ variante = 0, className = '' }) {
  const [inicio, fin] = paletas[variante % paletas.length];
  const id = `vr-${variante}-${inicio.slice(1)}`;

  return (
    <svg viewBox="0 0 400 240" className={className} role="img" aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-fondo`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0b1220" />
          <stop offset="100%" stopColor="#111c33" />
        </linearGradient>
        <linearGradient id={`${id}-acento`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={inicio} />
          <stop offset="100%" stopColor={fin} />
        </linearGradient>
        <radialGradient id={`${id}-brillo`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={inicio} stopOpacity="0.55" />
          <stop offset="100%" stopColor={inicio} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${id}-lente`} cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
          <stop offset="45%" stopColor={inicio} stopOpacity="0.85" />
          <stop offset="100%" stopColor={fin} stopOpacity="0.55" />
        </radialGradient>
      </defs>

      <rect width="400" height="240" fill={`url(#${id}-fondo)`} />
      <ellipse cx="200" cy="125" rx="165" ry="105" fill={`url(#${id}-brillo)`} />

      {/* Correa */}
      <rect x="34" y="104" width="332" height="30" rx="15" fill="#0f172a" stroke="#1e293b" strokeWidth="2" />
      <rect x="34" y="112" width="332" height="6" rx="3" fill={`url(#${id}-acento)`} opacity="0.35" />

      {/* Cuerpo del visor */}
      <rect x="92" y="64" width="216" height="118" rx="50" fill="#0b1220" stroke={`url(#${id}-acento)`} strokeWidth="3" />
      <rect x="110" y="80" width="180" height="86" rx="40" fill={`url(#${id}-acento)`} opacity="0.16" />

      {/* Lentes */}
      <ellipse cx="161" cy="123" rx="28" ry="24" fill={`url(#${id}-lente)`} />
      <ellipse cx="239" cy="123" rx="28" ry="24" fill={`url(#${id}-lente)`} />
      <ellipse cx="161" cy="123" rx="28" ry="24" fill="none" stroke="#0b1220" strokeWidth="3" />
      <ellipse cx="239" cy="123" rx="28" ry="24" fill="none" stroke="#0b1220" strokeWidth="3" />

      {/* Hueco de la nariz y luz de encendido */}
      <path d="M186 178 q14 16 28 0" fill="none" stroke="#0b1220" strokeWidth="6" strokeLinecap="round" />
      <circle cx="200" cy="84" r="4" fill={fin} />
      <path d="M118 74 q82 -22 164 0" fill="none" stroke="#ffffff" strokeWidth="2" opacity="0.18" strokeLinecap="round" />
    </svg>
  );
}

export default VrHeadset;
