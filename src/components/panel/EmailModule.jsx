import { useCallback, useEffect, useState } from 'react';
import { authApi } from '../../services/api';

/**
 * Estado del servidor de correo y envío de una prueba.
 *
 * Existe porque el correo es lo único del sistema que no se puede comprobar
 * desde el código: depende de unas credenciales que viven fuera del repositorio.
 * Sin esta tarjeta, la única forma de saber si «olvidé mi contraseña» envía el
 * correo era pedir un enlace y esperar a ver si llegaba.
 */
function EmailModule() {
  const [estado, setEstado] = useState(null);
  const [destino, setDestino] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  const cargar = useCallback(
    () =>
      authApi
        .correoEstado()
        .then((datos) => {
          setEstado(datos);
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );

  useEffect(() => {
    cargar();
  }, [cargar]);

  const probar = async (event) => {
    event.preventDefault();
    const correo = destino.trim();
    if (!correo) {
      setError('Escribe el correo al que quieres mandar la prueba.');
      return;
    }

    setEnviando(true);
    setMensaje('');
    setError('');
    try {
      const datos = await authApi.probarCorreo(correo);
      if (datos.enviado) setMensaje(datos.message);
      else setError(datos.message);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setEnviando(false);
    }
  };

  const configurado = estado?.configurado === true;

  return (
    <section id="correo-panel" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <div>
        <h2 className="text-xl font-bold text-white">Servidor de correo</h2>
        <p className="mt-1 text-sm text-slate-400">
          Es el que envía el enlace de «Olvidé mi contraseña» y la respuesta de las PQR.
        </p>
      </div>

      {estado && (
        <div
          className={`rounded-xl border p-3 text-sm ${
            configurado ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-amber-500/40 bg-amber-500/10 text-amber-200'
          }`}
        >
          <p className="font-semibold">{configurado ? 'Configurado' : 'Sin configurar'}</p>
          {configurado ? (
            <p className="mt-1">
              Los correos salen desde <span className="font-mono">{estado.remitente}</span> por {estado.porDonde}.
            </p>
          ) : (
            <p className="mt-1">{estado.motivo}</p>
          )}
        </div>
      )}

      {/* El plan gratuito de Render bloquea SMTP, así que aquí se avisa aunque
          la configuración esté completa: si no, el correo se pierde en silencio. */}
      {estado?.advertencia && (
        <p className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
          {estado.advertencia}
        </p>
      )}

      {estado && (!configurado || estado.advertencia) && (
        <div className="space-y-2 text-sm text-slate-300">
          <p className="font-semibold text-slate-200">Para que los correos salgan en cualquier parte:</p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>
              Crea una cuenta gratuita en <span className="font-mono">brevo.com</span> con el correo que quieras
              usar como remitente.
            </li>
            <li>En esa cuenta, entra a SMTP &amp; API, pestaña API Keys, y genera una clave.</li>
            <li>
              Escribe <span className="font-mono">EMAIL_API_KEY</span> (la clave) y{' '}
              <span className="font-mono">EMAIL_FROM</span> (ese mismo correo) en las variables del servidor.
            </li>
            <li>Reinicia el backend, o vuelve a publicar el servicio, y regresa a esta pantalla.</li>
          </ol>
          <p className="text-slate-400">
            En tu propio computador también sirve un Gmail por SMTP:{' '}
            <span className="font-mono">SMTP_USER</span> y <span className="font-mono">SMTP_PASSWORD</span> con una
            contraseña de aplicación de <span className="font-mono">myaccount.google.com/apppasswords</span>. En el
            sitio publicado no, porque el plan gratuito de Render bloquea SMTP.
          </p>
        </div>
      )}

      {mensaje && <p className="rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-200">{mensaje}</p>}
      {/* Cuando el fallo es el mismo que ya explica el recuadro de arriba no se
          repite la frase: basta con decir que no se envió nada. */}
      {error && (
        <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">
          {error === estado?.motivo ? 'No se envió nada: falta lo que dice el recuadro de arriba.' : error}
        </p>
      )}

      <form className="flex flex-wrap items-end gap-3" onSubmit={probar}>
        <label className="text-sm text-slate-300">
          Enviar una prueba a
          <input
            type="email"
            className="field mt-1"
            value={destino}
            onChange={(event) => setDestino(event.target.value)}
            placeholder="tucorreo@gmail.com"
          />
        </label>
        <button
          type="submit"
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60"
          disabled={enviando}
        >
          {enviando ? 'Enviando...' : 'Enviar correo de prueba'}
        </button>
      </form>
    </section>
  );
}

export default EmailModule;
