require('dotenv').config();
const express = require('express');
const cors = require('cors');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { query, initializeDatabase } = require('./db');
const { authenticate, authorize, secret } = require('./middleware');
const app = express();
const port = Number(process.env.PORT || 3001);
const allowedOrigins = [process.env.FRONTEND_URL, 'http://localhost:5173', 'http://127.0.0.1:5173'].filter(Boolean);
app.use(cors({ origin: (origin, callback) => !origin || allowedOrigins.includes(origin) ? callback(null, true) : callback(new Error('Origen no permitido por CORS')) })); app.use(express.json());
const publicUser = (user) => ({ id: user.id, name: user.name, lastName: user.last_name, email: user.email, role: user.role, active: Boolean(user.active) });
const getUser = async (email) => { const [rows] = await query('SELECT u.*, r.name AS role FROM usuarios u JOIN roles r ON r.id=u.role_id WHERE u.email=?', [email]); return rows[0]; };
app.get('/api/health', (_req, res) => res.json({ status: 'ok', database: 'mysql' }));
app.post('/api/auth/register', async (req, res) => { const { name, lastName, documentType, documentNumber, address, phone, email, password } = req.body; if (!name || !lastName || !documentType || !/^\d{6,12}$/.test(String(documentNumber || '')) || !address || !/^\+?[0-9\s-]{7,15}$/.test(String(phone || '')) || !/^\S+@\S+\.\S+$/.test(String(email || '')) || !password || password.length < 8 || !/(?=.*[A-Za-z])(?=.*\d)/.test(password)) return res.status(400).json({ message: 'Revisa los datos y la contraseña (mínimo 8 caracteres, letras y números).' }); try { const [roles] = await query('SELECT id FROM roles WHERE name=?', ['Cliente']); const [result] = await query('INSERT INTO usuarios (name,last_name,document_type,document_number,address,phone,email,password_hash,role_id) VALUES (?,?,?,?,?,?,?,?,?)', [name.trim(), lastName.trim(), documentType, documentNumber, address.trim(), phone.trim(), email.trim().toLowerCase(), bcrypt.hashSync(password, 12), roles[0].id]); res.status(201).json({ message: 'Registro completado con éxito.', user: { id: result.insertId, name, lastName, email: email.toLowerCase(), role: 'Cliente', active: true } }); } catch (error) { res.status(error.code === 'ER_DUP_ENTRY' ? 409 : 500).json({ message: error.code === 'ER_DUP_ENTRY' ? 'El correo o documento ya está registrado.' : 'No fue posible registrar el usuario.' }); } });
app.post('/api/auth/login', async (req, res) => { const user = await getUser(String(req.body.email || '').trim().toLowerCase()); if (!user || !user.active || !bcrypt.compareSync(req.body.password || '', user.password_hash)) return res.status(401).json({ message: 'Credenciales inválidas o usuario inactivo.' }); const token = jwt.sign({ id: user.id, name: user.name, email: user.email, role: user.role }, secret, { expiresIn: process.env.JWT_EXPIRES_IN || '2h' }); res.json({ token, user: publicUser(user) }); });
app.post('/api/auth/recover', (req, res) => /^\S+@\S+\.\S+$/.test(String(req.body.email || '').trim()) ? res.json({ message: 'Si el correo existe, recibirás instrucciones para recuperar tu cuenta.' }) : res.status(400).json({ message: 'Correo electrónico inválido.' }));
app.get('/api/auth/me', authenticate, async (req, res) => res.json({ user: publicUser(await getUser(req.user.email)) }));
app.get('/api/users', authenticate, authorize('Administrador'), async (_req, res) => { const [users] = await query('SELECT u.id,u.name,u.last_name AS lastName,u.document_type AS documentType,u.document_number AS documentNumber,u.address,u.phone,u.email,u.active,r.name AS role FROM usuarios u JOIN roles r ON r.id=u.role_id ORDER BY u.id DESC'); res.json({ users }); });
app.post('/api/users', authenticate, authorize('Administrador'), async (req, res) => { const { name, lastName, documentType = 'CC', documentNumber, address, phone, email, password, role = 'Cliente' } = req.body; if (!name || !lastName || !documentNumber || !address || !password || password.length < 8) return res.status(400).json({ message: 'Datos de usuario incompletos o inválidos.' }); try { const [roles] = await query('SELECT id FROM roles WHERE name=?', [role]); if (!roles[0]) return res.status(400).json({ message: 'Rol inválido.' }); const [result] = await query('INSERT INTO usuarios (name,last_name,document_type,document_number,address,phone,email,password_hash,role_id) VALUES (?,?,?,?,?,?,?,?,?)', [name, lastName, documentType, documentNumber, address, phone, email.toLowerCase(), bcrypt.hashSync(password, 12), roles[0].id]); res.status(201).json({ id: result.insertId }); } catch (error) { res.status(error.code === 'ER_DUP_ENTRY' ? 409 : 500).json({ message: 'No fue posible crear el usuario.' }); } });
app.put('/api/users/:id', authenticate, authorize('Administrador'), async (req, res) => { const { name, lastName, address, phone, email, role = 'Cliente' } = req.body; const [roles] = await query('SELECT id FROM roles WHERE name=?', [role]); if (!name || !lastName || !email || !roles[0]) return res.status(400).json({ message: 'Datos de usuario inválidos.' }); const [result] = await query('UPDATE usuarios SET name=?,last_name=?,address=?,phone=?,email=?,role_id=? WHERE id=?', [name, lastName, address, phone, email.toLowerCase(), roles[0].id, req.params.id]); result.affectedRows ? res.json({ message: 'Usuario actualizado.' }) : res.status(404).json({ message: 'Usuario no encontrado.' }); });
app.patch('/api/users/:id/status', authenticate, authorize('Administrador'), async (req, res) => { const [result] = await query('UPDATE usuarios SET active=? WHERE id=?', [req.body.active ? 1 : 0, req.params.id]); result.affectedRows ? res.json({ message: 'Estado actualizado.' }) : res.status(404).json({ message: 'Usuario no encontrado.' }); });
app.delete('/api/users/:id', authenticate, authorize('Administrador'), async (req, res) => { const [result] = await query('DELETE FROM usuarios WHERE id=?', [req.params.id]); result.affectedRows ? res.json({ message: 'Usuario eliminado.' }) : res.status(404).json({ message: 'Usuario no encontrado.' }); });
function crud(resource, table, roles) {
  app.get(`/api/${resource}`, authenticate, async (_req, res) => {
    const [rows] = await query(`SELECT * FROM ${table} ORDER BY id DESC`);
    res.json({ [resource]: rows });
  });
  app.post(`/api/${resource}`, authenticate, authorize(...roles), async (req, res) => {
    const { name, description = '', price = 0 } = req.body;
    if (!name || Number(price) < 0) return res.status(400).json({ message: 'Nombre y precio válido son obligatorios.' });
    const [result] = await query(`INSERT INTO ${table} (name,description,price,active) VALUES (?,?,?,?)`, [name.trim(), description, Number(price), 1]);
    res.status(201).json({ id: result.insertId });
  });
  app.put(`/api/${resource}/:id`, authenticate, authorize(...roles), async (req, res) => {
    const { name, description = '', price = 0 } = req.body;
    const [result] = await query(`UPDATE ${table} SET name=?,description=?,price=? WHERE id=?`, [name.trim(), description, Number(price), req.params.id]);
    result.affectedRows ? res.json({ message: 'Registro actualizado.' }) : res.status(404).json({ message: 'Registro no encontrado.' });
  });
  app.patch(`/api/${resource}/:id/status`, authenticate, authorize(...roles), async (req, res) => {
    const active = Boolean(req.body.active);
    const [result] = await query(`UPDATE ${table} SET active=? WHERE id=?`, [active ? 1 : 0, req.params.id]);
    result.affectedRows ? res.json({ message: 'Estado actualizado.' }) : res.status(404).json({ message: 'Registro no encontrado.' });
  });
  app.delete(`/api/${resource}/:id`, authenticate, authorize(...roles), async (req, res) => {
    const [result] = await query(`DELETE FROM ${table} WHERE id=?`, [req.params.id]);
    result.affectedRows ? res.json({ message: 'Registro eliminado.' }) : res.status(404).json({ message: 'Registro no encontrado.' });
  });
}
crud('products', 'productos', ['Administrador']);
crud('services', 'servicios', ['Administrador', 'Empleado']);
initializeDatabase().then(() => app.listen(port, () => console.log(`SimonC API MySQL en http://localhost:${port}`))).catch((error) => { console.error('No se pudo conectar a MySQL:', error.message); process.exit(1); });
