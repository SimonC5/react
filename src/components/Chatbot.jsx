import { useEffect, useRef, useState } from 'react';
import { chatbotApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

const BIENVENIDA = {
  rol: 'asistente',
  contenido: '¡Hola! Soy el asistente de SimonC. Pregúntame por productos, servicios, facturas o radica una PQR.',
};

/**
 * Chatbot de atención al cliente integrado al sitio.
 * Las respuestas llegan desde FastAPI, que es quien habla con el servicio de IA.
 * Cubre los requerimientos 17 y 18 del quinto avance.
 */
function Chatbot() {
  const { user } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState([BIENVENIDA]);
  const [texto, setTexto] = useState('');
  const [conversacionId, setConversacionId] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  // Motivo por el que la IA no pudo responder. El cliente igual recibe la
  // respuesta del catálogo, así que a él no se le muestra el detalle técnico:
  // solo lo ve quien administra la tienda, que es quien puede arreglarlo.
  const [aviso, setAviso] = useState('');
  const finRef = useRef(null);

  useEffect(() => {
    if (abierto) finRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [mensajes, abierto]);

  if (!user) return null;

  const enviar = async (event) => {
    event.preventDefault();
    const pregunta = texto.trim();
    if (!pregunta || enviando) return;

    setMensajes((actuales) => [...actuales, { rol: 'usuario', contenido: pregunta }]);
    setTexto('');
    setEnviando(true);
    setError('');
    setAviso('');

    try {
      const data = await chatbotApi.enviar(pregunta, conversacionId);
      setConversacionId(data.conversacionId);
      setMensajes((actuales) => [...actuales, { rol: 'asistente', contenido: data.respuesta }]);
      setAviso(data.aviso || '');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto((valor) => !valor)}
        aria-label={abierto ? 'Cerrar el asistente virtual' : 'Abrir el asistente virtual'}
        className="fixed bottom-24 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-cyan-500 text-2xl text-slate-950 shadow-lg transition hover:bg-cyan-400"
      >
        {abierto ? '×' : '💬'}
      </button>

      {abierto && (
        <div className="fixed bottom-44 right-6 z-40 flex h-96 w-[min(22rem,calc(100vw-3rem))] flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
          <header className="border-b border-slate-800 px-4 py-3">
            <p className="font-semibold text-white">Asistente SimonC</p>
            <p className="text-xs text-slate-400">Atención al cliente con Inteligencia Artificial</p>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {mensajes.map((mensaje, indice) => (
              <p
                key={indice}
                className={`max-w-[85%] whitespace-pre-line rounded-2xl px-3 py-2 text-sm ${
                  mensaje.rol === 'usuario' ? 'ml-auto bg-cyan-500/20 text-cyan-100' : 'bg-slate-800 text-slate-200'
                }`}
              >
                {mensaje.contenido}
              </p>
            ))}
            {enviando && <p className="text-xs text-slate-500">El asistente está escribiendo...</p>}
            {error && <p className="text-xs text-red-300">{error}</p>}
            {aviso && user.role !== 'Cliente' && <p className="text-xs text-amber-300">{aviso}</p>}
            <div ref={finRef} />
          </div>

          <form onSubmit={enviar} className="flex gap-2 border-t border-slate-800 p-3">
            <input
              className="field"
              placeholder="Escribe tu pregunta"
              aria-label="Mensaje para el asistente"
              maxLength="1000"
              value={texto}
              onChange={(event) => setTexto(event.target.value)}
            />
            <button type="submit" disabled={enviando} className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60">
              Enviar
            </button>
          </form>
        </div>
      )}
    </>
  );
}

export default Chatbot;
