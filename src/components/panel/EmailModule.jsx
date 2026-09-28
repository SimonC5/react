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
              Los correos salen desde <span className="font-mono">{estado.remitente}</span> por{' '}
              <span className="font-mono">{estado.servidor}</span>.
            </p>
          ) : (
            <p className="mt-1">{estado.motivo}</p>
          )}
        </div>
      )}

      {!configurado && estado && (
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-300">
          <li>Activa la verificación en dos pasos en la cuenta de Google que va a enviar los correos.</li>
          <li>
            Crea una contraseña de aplicación en{' '}
            <span className="font-mono">myaccount.google.com/apppasswords</span> y copia las 16 letras.
          </li>
          <li>
            Escribe <span className="font-mono">SMTP_USER</span> (el correo) y <span className="font-mono">SMTP_PASSWORD</span>{' '}
            (esas 16 letras) en las variables del servidor. El resto se deduce solo.
          </li>
          <li>Reinicia el backend y vuelve a esta pantalla.</li>
        </ol>
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
