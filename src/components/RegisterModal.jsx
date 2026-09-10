import { useEffect, useMemo, useState } from 'react';
import logo from '../assets/logo.svg';
import Button from './Button';
import Input from './Input';
import Select from './Select';
import { authApi } from '../services/api';

const initialForm = {
  name: '',
  lastName: '',
  documentType: 'CC',
  documentNumber: '',
  address: '',
  phone: '',
  email: '',
  password: '',
  confirmPassword: '',
};

function RegisterModal({ isOpen, onClose }) {
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');
  const [serverError, setServerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const documentTypes = useMemo(
    () => [
      { value: 'CC', label: 'Cédula de ciudadanía' },
      { value: 'TI', label: 'Tarjeta de identidad' },
      { value: 'CE', label: 'Cédula de extranjería' },
      { value: 'PASAPORTE', label: 'Pasaporte' },
    ],
    [],
  );

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event) => {
      if (event.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) {
      setForm(initialForm);
      setErrors({});
      setSuccessMessage('');
      setServerError('');
    }
  }, [isOpen]);

  const validateForm = (currentForm) => {
    const nextErrors = {};

    if (!currentForm.name.trim()) nextErrors.name = 'Nombre es obligatorio.';
    else if (currentForm.name.trim().length < 2) nextErrors.name = 'El nombre debe tener al menos 2 caracteres.';
    else if (/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/.test(currentForm.name)) nextErrors.name = 'Nombre contiene caracteres no permitidos.';

    if (!currentForm.lastName.trim()) nextErrors.lastName = 'Apellido es obligatorio.';
    else if (currentForm.lastName.trim().length < 2) nextErrors.lastName = 'El apellido debe tener al menos 2 caracteres.';
    else if (/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/.test(currentForm.lastName)) nextErrors.lastName = 'Apellido contiene caracteres no permitidos.';

    if (!currentForm.documentNumber.trim()) nextErrors.documentNumber = 'Número de documento obligatorio.';
    else if (!/^\d{6,12}$/.test(currentForm.documentNumber)) nextErrors.documentNumber = 'El documento debe contener entre 6 y 12 dígitos numéricos.';

    if (!currentForm.address.trim()) nextErrors.address = 'La dirección es obligatoria.';
    else if (currentForm.address.trim().length < 8) nextErrors.address = 'La dirección debe contener al menos 8 caracteres.';

    if (!currentForm.phone.trim()) nextErrors.phone = 'El teléfono es obligatorio.';
    else if (!/^\+?[0-9\s-]{7,15}$/.test(currentForm.phone)) nextErrors.phone = 'El teléfono debe tener formato válido.';

    if (!currentForm.email.trim()) nextErrors.email = 'El correo electrónico es obligatorio.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(currentForm.email)) nextErrors.email = 'Correo electrónico inválido.';

    if (!currentForm.password) nextErrors.password = 'La contraseña es obligatoria.';
    else if (currentForm.password.length < 8) nextErrors.password = 'La contraseña debe tener al menos 8 caracteres.';
    else if (!/^(?=.*[A-Za-z])(?=.*\d).+$/.test(currentForm.password)) nextErrors.password = 'La contraseña debe incluir letras y números.';

    if (!currentForm.confirmPassword) nextErrors.confirmPassword = 'Debes confirmar la contraseña.';
    else if (currentForm.confirmPassword !== currentForm.password) nextErrors.confirmPassword = 'Las contraseñas no coinciden.';

    return nextErrors;
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    const nextForm = { ...form, [name]: value };
    setForm(nextForm);
    setErrors(validateForm(nextForm));
    setSuccessMessage('');
    setServerError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = validateForm(form);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length === 0) {
      setIsSubmitting(true);
      try {
        await authApi.register(form);
        setSuccessMessage('Registro completado con éxito. Ya puedes iniciar sesión.');
        setForm(initialForm);
        setErrors({});
      } catch (error) { setServerError(error.message); }
      finally { setIsSubmitting(false); }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-white p-5 shadow-2xl sm:p-7">
        <div className="mb-5 flex items-start justify-between gap-3">
          <div className="flex items-center gap-4">
            <img src={logo} alt="Logo SimonC" className="h-14 w-14 rounded-full ring-2 ring-cyan-400/50 shadow-[0_0_20px_rgba(34,211,238,0.45)]" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-500">Nuevo cliente</p>
              <h2 className="mt-2 text-2xl font-bold text-slate-900">Crear cuenta</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-200"
            aria-label="Cerrar modal"
          >
            ✕
          </button>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
          <div className="grid gap-4 md:grid-cols-2">
            <Input id="register-name" name="name" label="Nombre" value={form.name} onChange={handleChange} error={errors.name} placeholder="Tu nombre" maxLength={80} />
            <Input id="register-lastName" name="lastName" label="Apellido" value={form.lastName} onChange={handleChange} error={errors.lastName} placeholder="Tu apellido" maxLength={80} />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Select id="register-documentType" name="documentType" label="Tipo de documento" value={form.documentType} onChange={handleChange} options={documentTypes} error={errors.documentType} />
            <Input id="register-documentNumber" name="documentNumber" label="Número de documento" value={form.documentNumber} onChange={handleChange} error={errors.documentNumber} placeholder="12345678" maxLength={12} inputMode="numeric" />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Input id="register-address" name="address" label="Dirección" value={form.address} onChange={handleChange} error={errors.address} placeholder="Calle 123 #45-67" maxLength={150} />
            <Input id="register-phone" name="phone" label="Teléfono" value={form.phone} onChange={handleChange} error={errors.phone} placeholder="+57 300 123 4567" maxLength={15} inputMode="tel" />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Input id="register-email" name="email" label="Correo electrónico" type="email" value={form.email} onChange={handleChange} error={errors.email} placeholder="nombre@correo.com" maxLength={120} />
            <Input id="register-password" name="password" label="Contraseña" type="password" value={form.password} onChange={handleChange} error={errors.password} placeholder="Mínimo 8 caracteres" maxLength={100} />
          </div>

          <Input id="register-confirmPassword" name="confirmPassword" label="Confirmación de contraseña" type="password" value={form.confirmPassword} onChange={handleChange} error={errors.confirmPassword} placeholder="Repite tu contraseña" maxLength={100} />

          {successMessage && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
              {successMessage}
            </div>
          )}
          {serverError && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{serverError}</div>}

          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="secondary" onClick={onClose} className="sm:min-w-32">
              Cancelar
            </Button>
            <Button type="submit" className="sm:min-w-40" disabled={isSubmitting}>{isSubmitting ? 'Guardando...' : 'Registrarse'}</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RegisterModal;
