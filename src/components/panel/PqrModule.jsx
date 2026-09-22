import { useCallback, useEffect, useState } from 'react';
import Modal from '../Modal';
import { pqrApi } from '../../services/api';
import { fechaCorta } from '../../utils/formato';

const solicitudVacia = { tipo: 'Petición', asunto: '', descripcion: '' };
const ESTADOS = ['Pendiente', 'En proceso', 'Respondida', 'Cerrada'];
const TIPOS = ['Petición', 'Queja', 'Reclamo', 'Sugerencia'];

/**
 * Módulo de PQR: el cliente radica y consulta; administrador y empleado gestionan.
 * Cubre el requerimiento 16 del quinto avance.
 */
function PqrModule({ puedeGestionar }) {
  const [solicitud, setSolicitud] = useState(solicitudVacia);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [solicitudes, setSolicitudes] = useState([]);
  const [respuestas, setRespuestas] = useState({});
  const [radicacionAbierta, setRadicacionAbierta] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');

  const cargar = useCallback(
    (estado) =>
      pqrApi
        .listar({ estado })
        .then((data) => {
          setSolicitudes(data.pqr || []);
          setError('');
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );

  useEffect(() => {
    cargar('');
  }, [cargar]);

  const radicar = async (event) => {
    event.preventDefault();
    try {
      const data = await pqrApi.crear(solicitud);
      setMensaje(data.message);
      setError('');
      setSolicitud(solicitudVacia);
      setRadicacionAbierta(false);
      await cargar(filtroEstado);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const gestionar = async (registro, cambios) => {
    try {
      await pqrApi.gestionar(registro.id, cambios);
      setMensaje(`Solicitud ${registro.radicado} actualizada.`);
      setError('');
      await cargar(filtroEstado);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <section id="pqr-panel" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <h2 className="text-xl font-bold text-white">PQR</h2>
      <p className="text-sm text-slate-400">Peticiones, quejas y reclamos con seguimiento por estado.</p>

      {mensaje && <p className="rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-200">{mensaje}</p>}
      {error && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      <button
        type="button"
        className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950"
        onClick={() => setRadicacionAbierta(true)}
      >
        Radicar una solicitud
      </button>

      <Modal
        isOpen={radicacionAbierta}
        onClose={() => setRadicacionAbierta(false)}
        title="Radicar una solicitud"
        subtitle="Cuéntanos qué necesitas y le haremos seguimiento por estado."
      >
        <form onSubmit={radicar} className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm text-slate-300">
            Tipo
            <select className="field mt-1" value={solicitud.tipo} onChange={(event) => setSolicitud({ ...solicitud, tipo: event.target.value })}>
              {TIPOS.map((tipo) => (
                <option key={tipo} value={tipo}>
                  {tipo}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300 md:col-span-2">
            Asunto
            <input
              required
              maxLength="120"
              className="field mt-1"
              value={solicitud.asunto}
              onChange={(event) => setSolicitud({ ...solicitud, asunto: event.target.value })}
            />
          </label>
        </div>

        <label className="block text-sm text-slate-300">
          Descripción
          <textarea
            required
            rows="3"
            className="field mt-1 resize-none"
            value={solicitud.descripcion}
            onChange={(event) => setSolicitud({ ...solicitud, descripcion: event.target.value })}
          />
        </label>

        <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200"
            onClick={() => setRadicacionAbierta(false)}
          >
            Cancelar
          </button>
          <button type="submit" className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950">
            Radicar solicitud
          </button>
        </div>
        </form>
      </Modal>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-slate-300">
          Filtrar por estado
          <select
            className="field mt-1"
            value={filtroEstado}
            onChange={(event) => {
              setFiltroEstado(event.target.value);
              cargar(event.target.value);
            }}
          >
            <option value="">Todos</option>
            {ESTADOS.map((estado) => (
              <option key={estado} value={estado}>
                {estado}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {solicitudes.map((registro) => (
          <article key={registro.id} className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{registro.asunto}</p>
                <p className="text-xs text-slate-500">
                  {registro.radicado} · {registro.tipo} · {registro.cliente} · {fechaCorta(registro.creado)}
                </p>
              </div>
              <span className="rounded-full bg-cyan-500/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-cyan-300">
                {registro.estado}
              </span>
            </div>

            <p className="mt-3 text-sm text-slate-300">{registro.descripcion}</p>
            {registro.respuesta && <p className="mt-2 rounded-lg bg-slate-800/60 p-2 text-sm text-emerald-200">{registro.respuesta}</p>}

            {puedeGestionar && (
              <div className="mt-4 space-y-2">
                <textarea
                  rows="2"
                  placeholder="Escribe una respuesta"
                  className="field resize-none"
                  value={respuestas[registro.id] ?? registro.respuesta ?? ''}
                  onChange={(event) => setRespuestas({ ...respuestas, [registro.id]: event.target.value })}
                />
                <div className="flex flex-wrap gap-2">
                  {ESTADOS.map((estado) => (
                    <button
                      key={estado}
                      type="button"
                      className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-200"
                      onClick={() => gestionar(registro, { estado, respuesta: respuestas[registro.id] ?? registro.respuesta })}
                    >
                      {estado}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </article>
        ))}
        {!solicitudes.length && <p className="text-sm text-slate-500">Aún no hay solicitudes registradas.</p>}
      </div>
    </section>
  );
}

export default PqrModule;
