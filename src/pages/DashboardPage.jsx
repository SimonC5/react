import { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import logo from '../assets/logo.svg';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../services/api';
import AnalyticsModule from '../components/panel/AnalyticsModule';
import SalesModule from '../components/panel/SalesModule';
import InvoicesModule from '../components/panel/InvoicesModule';
import ReportsModule from '../components/panel/ReportsModule';
import PqrModule from '../components/panel/PqrModule';

const blankResource = { name: '', description: '', price: '' };

function IconHome() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V20h14V9.5" />
      <path d="M9 20v-7h6v7" />
    </svg>
  );
}

function IconPackage() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M3 8.5 12 4l9 4.5-9 4.5L3 8.5Z" />
      <path d="M12 13v7" />
      <path d="M3 8.5v7L12 20l9-4.5v-7" />
    </svg>
  );
}

function IconService() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M12 3v6" />
      <path d="M9 6h6" />
      <path d="M5 12h14" />
      <path d="M6 18h12" />
      <path d="M12 12v9" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M4 20V10" />
      <path d="M10 20V4" />
      <path d="M16 20v-7" />
      <path d="M3 20h18" />
    </svg>
  );
}

function IconSale() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M4 7h16l-1.5 12H5.5L4 7Z" />
      <path d="M9 7V5a3 3 0 0 1 6 0v2" />
    </svg>
  );
}

function IconInvoice() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z" />
      <path d="M9 8h6" />
      <path d="M9 12h6" />
    </svg>
  );
}

function IconReport() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M7 3h7l5 5v13H7V3Z" />
      <path d="M14 3v5h5" />
      <path d="M10 13h5" />
      <path d="M10 17h5" />
    </svg>
  );
}

function IconSupport() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M21 12a9 9 0 1 0-3.2 6.9L21 20l-1-3.3A8.9 8.9 0 0 0 21 12Z" />
      <path d="M9.5 9.5a2.5 2.5 0 0 1 4.6 1.3c0 1.7-2.1 2-2.1 3.2" />
      <path d="M12 17h.01" />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M16 20v-1.5a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20" />
      <circle cx="9" cy="7" r="3.2" />
      <path d="M22 20v-1.5a4 4 0 0 0-3-3.8" />
      <path d="M16 3.7a4 4 0 0 1 0 6.6" />
    </svg>
  );
}

function IconLogout() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  );
}

function SidebarButton({ icon, label, onClick, activo = false }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={activo ? 'page' : undefined}
      className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition ${
        activo
          ? 'border-cyan-400/40 bg-cyan-500/10 text-white'
          : 'border-transparent text-slate-200 hover:border-slate-700 hover:bg-slate-800/70'
      }`}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-300">{icon}</span>
      <span className="font-medium">{label}</span>
    </button>
  );
}

function ResourceManager({ resource, title, puedeEditar = true }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(blankResource);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadItems = useCallback(
    () => apiRequest(`/${resource}`).then((data) => setItems(data[resource] || [])),
    [resource],
  );

  useEffect(() => {
    loadItems().catch((requestError) => setError(requestError.message));
  }, [loadItems]);

  const openCreateModal = () => {
    setEditingId(null);
    setForm(blankResource);
    setIsModalOpen(true);
  };

  const openEditModal = (item) => {
    setEditingId(item.id);
    setForm({
      name: item.name || '',
      description: item.description || '',
      price: String(item.price ?? ''),
    });
    setIsModalOpen(true);
  };

  const submitResource = async (event) => {
    event.preventDefault();
    try {
      const payload = { ...form, price: Number(form.price || 0) };

      await apiRequest(editingId ? `/${resource}/${editingId}` : `/${resource}`, {
        method: editingId ? 'PUT' : 'POST',
        body: JSON.stringify(payload),
      });

      setForm(blankResource);
      setEditingId(null);
      setIsModalOpen(false);
      await loadItems();
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const toggleStatus = async (id, active) => {
    try {
      await apiRequest(`/${resource}/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ active: !active }),
      });
      setItems((currentItems) =>
        currentItems.map((item) => (item.id === id ? { ...item, active: !active } : item)),
      );
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const deleteItem = async (id) => {
    try {
      await apiRequest(`/${resource}/${id}`, { method: 'DELETE' });
      setItems((currentItems) => currentItems.filter((item) => item.id !== id));
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return (
    <div className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-white">{title}</h2>
        {puedeEditar && (
          <button
            type="button"
            onClick={openCreateModal}
            className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            Agregar {title.slice(0, -1).toLowerCase()}
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-300">{error}</p>}

      <div className="grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{item.name}</p>
                <p className="mt-1 text-sm text-slate-400">{item.description || 'Sin descripción'}</p>
                <p className="mt-2 text-sm font-medium text-cyan-300">${Number(item.price).toLocaleString('es-CO')}</p>
              </div>
              <span
                className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
                  item.active === 0 || item.active === false
                    ? 'bg-red-500/15 text-red-300'
                    : 'bg-emerald-500/15 text-emerald-300'
                }`}
              >
                {item.active === 0 || item.active === false ? 'Inactivo' : 'Activo'}
              </span>
            </div>

            {puedeEditar && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="text-sm text-cyan-300" onClick={() => openEditModal(item)}>
                  Editar
                </button>
                <button type="button" className="text-sm text-amber-300" onClick={() => toggleStatus(item.id, item.active)}>
                  Estado
                </button>
                <button type="button" className="text-sm text-red-300" onClick={() => deleteItem(item.id)}>
                  Eliminar
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {puedeEditar && isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4">
          <div className="w-full max-w-xl rounded-3xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h3 className="text-xl font-bold text-white">
                {editingId ? `Editar ${title.slice(0, -1).toLowerCase()}` : `Agregar ${title.slice(0, -1).toLowerCase()}`}
              </h3>
              <button type="button" className="text-xl text-slate-400" onClick={() => setIsModalOpen(false)} aria-label="Cerrar modal">
                ×
              </button>
            </div>

            <form onSubmit={submitResource} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-300">Nombre</label>
                <input
                  required
                  maxLength="100"
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  className="field"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm text-slate-300">Descripción</label>
                <textarea
                  maxLength="255"
                  rows="4"
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  className="field resize-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm text-slate-300">Precio</label>
                <input
                  required
                  min="0"
                  step="0.01"
                  type="number"
                  value={form.price}
                  onChange={(event) => setForm({ ...form, price: event.target.value })}
                  className="field"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setIsModalOpen(false)} className="rounded-lg border border-slate-600 px-4 py-2 text-slate-200">
                  Cancelar
                </button>
                <button type="submit" className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950">
                  {editingId ? 'Guardar cambios' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function DashboardPage({ role }) {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [message, setMessage] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: '',
    lastName: '',
    documentNumber: '',
    address: '',
    phone: '',
    email: '',
    password: '',
    role: 'Cliente',
  });

  const esAdministrador = role === 'Administrador';
  const esCliente = role === 'Cliente';
  // Administrador y empleado operan; el cliente solo consulta lo suyo.
  const gestionaComercial = esAdministrador || role === 'Empleado';

  // Cada entrada del menú muestra su sección y esconde las demás. El dashboard
  // es solo del administrador, y el cliente no lleva el catálogo dentro del
  // panel: para ver qué se vende está la tienda pública.
  const secciones = useMemo(
    () => [
      ...(esAdministrador ? [{ clave: 'dashboard', label: 'Dashboard', icon: <IconChart /> }] : []),
      { clave: 'ventas', label: esCliente ? 'Mis compras' : 'Ventas', icon: <IconSale /> },
      { clave: 'facturas', label: esCliente ? 'Mis facturas' : 'Facturación', icon: <IconInvoice /> },
      ...(gestionaComercial ? [{ clave: 'reportes', label: 'Reportes', icon: <IconReport /> }] : []),
      { clave: 'pqr', label: 'PQR', icon: <IconSupport /> },
      ...(esAdministrador ? [{ clave: 'usuarios', label: 'Usuarios', icon: <IconUsers /> }] : []),
      ...(esCliente
        ? []
        : [
            { clave: 'productos', label: 'Productos', icon: <IconPackage /> },
            { clave: 'servicios', label: 'Servicios', icon: <IconService /> },
          ]),
    ],
    [esAdministrador, esCliente, gestionaComercial],
  );

  const [seccion, setSeccion] = useState(secciones[0].clave);

  useEffect(() => {
    // Si cambia el rol, la sección activa puede dejar de existir.
    if (!secciones.some((item) => item.clave === seccion)) setSeccion(secciones[0].clave);
  }, [secciones, seccion]);

  const loadUsers = () => apiRequest('/users').then((data) => setUsers(data.users || []));

  useEffect(() => {
    if (user?.role === 'Administrador') {
      loadUsers().catch((requestError) => setMessage(requestError.message));
    }
  }, [user]);

  if (loading) {
    return <div className="py-20 text-center text-slate-400">Cargando sesión...</div>;
  }

  if (!user || user.role !== role) {
    return <Navigate to="/login" replace />;
  }

  const saveUser = async (event) => {
    event.preventDefault();
    try {
      await apiRequest(editingId ? `/users/${editingId}` : '/users', {
        method: editingId ? 'PUT' : 'POST',
        body: JSON.stringify(form),
      });
      setForm({
        name: '',
        lastName: '',
        documentNumber: '',
        address: '',
        phone: '',
        email: '',
        password: '',
        role: 'Cliente',
      });
      setEditingId(null);
      setMessage('Usuario guardado correctamente.');
      await loadUsers();
    } catch (requestError) {
      setMessage(requestError.message);
    }
  };

  const toggleUserStatus = async (id, active) => {
    try {
      await apiRequest(`/users/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ active: !active }),
      });
      setUsers((currentUsers) => currentUsers.map((item) => (item.id === id ? { ...item, active: !active } : item)));
    } catch (requestError) {
      setMessage(requestError.message);
    }
  };

  const deleteUser = async (id) => {
    try {
      await apiRequest(`/users/${id}`, { method: 'DELETE' });
      setUsers((currentUsers) => currentUsers.filter((item) => item.id !== id));
    } catch (requestError) {
      setMessage(requestError.message);
    }
  };

  return (
    <section className="space-y-6 py-8">
      <div className="mb-6 flex flex-col gap-6 lg:flex-row">
        <aside className="w-full rounded-3xl border border-slate-700 bg-slate-900/80 p-5 lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:w-[260px] lg:shrink-0 lg:self-start lg:overflow-y-auto">
          <div className="mb-6 flex items-center gap-3">
            <img src={logo} alt="Logo SimonC" className="h-12 w-12 rounded-full ring-2 ring-cyan-400/50" />
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-300">SimonC</p>
              <p className="text-sm text-slate-300">Panel</p>
            </div>
          </div>

          <nav className="space-y-2">
            <SidebarButton icon={<IconHome />} label="Mi página" onClick={() => navigate('/')} />
            {secciones.map(({ clave, label, icon }) => (
              <SidebarButton
                key={clave}
                icon={icon}
                label={label}
                activo={seccion === clave}
                onClick={() => setSeccion(clave)}
              />
            ))}
            <SidebarButton
              icon={<IconLogout />}
              label="Cerrar sesión"
              onClick={() => {
                logout();
                navigate('/login');
              }}
            />
          </nav>
        </aside>

        <div className="flex-1 space-y-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">Área privada</p>
            <h1 className="mt-2 text-4xl font-black text-white">Panel de {role}</h1>
            <p className="mt-2 text-slate-400">Bienvenido, {user.name}. Sesión protegida con JWT.</p>
          </div>

          {message && <p className="rounded-lg bg-cyan-500/10 p-3 text-cyan-200">{message}</p>}

          {esAdministrador && seccion === 'usuarios' && (
            <div id="usuarios-panel" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
              <h2 className="text-xl font-bold text-white">Administrar usuarios</h2>

              <form onSubmit={saveUser} className="grid gap-3 md:grid-cols-4">
                <input required maxLength="80" placeholder="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="field" />
                <input required maxLength="80" placeholder="Apellido" value={form.lastName} onChange={(event) => setForm({ ...form, lastName: event.target.value })} className="field" />
                <input required placeholder="Documento" inputMode="numeric" maxLength="12" value={form.documentNumber} disabled={Boolean(editingId)} onChange={(event) => setForm({ ...form, documentNumber: event.target.value.replace(/\D/g, '') })} className="field" />
                <input required type="email" placeholder="Correo" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="field" />
                <input required={!editingId} type="password" minLength="8" placeholder="Contraseña" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} className="field" />
                <input required placeholder="Dirección" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} className="field" />
                <input required placeholder="Teléfono" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} className="field" />
                <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} className="field">
                  <option>Cliente</option>
                  <option>Empleado</option>
                  <option>Administrador</option>
                </select>
                <button type="submit" className="rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-slate-950 md:col-span-4">
                  {editingId ? 'Actualizar usuario' : 'Guardar usuario'}
                </button>
              </form>

              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-700 text-slate-400">
                      <th className="py-2 pr-4">Nombre</th>
                      <th className="py-2 pr-4">Correo</th>
                      <th className="py-2 pr-4">Rol</th>
                      <th className="py-2 pr-4">Estado</th>
                      <th className="py-2">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((item) => (
                      <tr key={item.id} className="border-b border-slate-800">
                        <td className="py-3 pr-4 text-white">{item.name} {item.lastName}</td>
                        <td className="py-3 pr-4">{item.email}</td>
                        <td className="py-3 pr-4">{item.role}</td>
                        <td className="py-3 pr-4">
                          <button type="button" className={`rounded-full px-2 py-1 text-xs font-semibold ${item.active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`} onClick={() => toggleUserStatus(item.id, item.active)}>
                            {item.active ? 'Activo' : 'Inactivo'}
                          </button>
                        </td>
                        <td className="py-3">
                          <div className="flex flex-wrap gap-2">
                            <button type="button" className="text-cyan-300" onClick={() => { setEditingId(item.id); setForm({ name: item.name, lastName: item.lastName, documentNumber: item.documentNumber, address: item.address, phone: item.phone, email: item.email, password: '', role: item.role }); }}>
                              Editar
                            </button>
                            <button type="button" className="text-red-300" onClick={() => deleteUser(item.id)}>
                              Eliminar
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {seccion === 'dashboard' && esAdministrador && <AnalyticsModule rol={role} />}

          {seccion === 'ventas' && (
            <SalesModule puedeRegistrar={gestionaComercial} titulo={esCliente ? 'Mis compras' : 'Ventas'} />
          )}

          {seccion === 'facturas' && (
            <InvoicesModule
              titulo={esCliente ? 'Mis facturas' : 'Facturación'}
              puedeGenerar={gestionaComercial}
            />
          )}

          {seccion === 'reportes' && gestionaComercial && <ReportsModule />}

          {seccion === 'pqr' && <PqrModule puedeGestionar={gestionaComercial} />}

          {seccion === 'productos' && !esCliente && (
            <div id="productos-panel">
              <ResourceManager resource="products" title="Productos" puedeEditar={esAdministrador} />
            </div>
          )}

          {seccion === 'servicios' && !esCliente && (
            <div id="servicios-panel">
              <ResourceManager resource="services" title="Servicios" puedeEditar={gestionaComercial} />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default DashboardPage;
