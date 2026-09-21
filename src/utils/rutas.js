/** Ruta del panel privado que corresponde a cada rol. */
export function rutaDelPanel(role) {
  if (role === 'Administrador') return '/panel/admin';
  if (role === 'Empleado') return '/panel/empleado';
  return '/panel/cliente';
}

/** Indica si una ruta pertenece al panel privado. */
export function esRutaDePanel(pathname) {
  return pathname.startsWith('/panel');
}
