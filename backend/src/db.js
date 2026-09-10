const fs = require('node:fs');
const path = require('node:path');
const mysql = require('mysql2/promise');
const bcrypt = require('bcryptjs');

const config = { host: process.env.DB_HOST || '127.0.0.1', port: Number(process.env.DB_PORT || 3306), user: process.env.DB_USER || 'root', password: process.env.DB_PASSWORD || '', waitForConnections: true, connectionLimit: 10, charset: 'utf8mb4' };
let pool;
const query = (sql, params = []) => pool.execute(sql, params);
async function initializeDatabase() {
  const bootstrap = await mysql.createConnection(config);
  const database = process.env.DB_NAME || 'simonsc';
  await bootstrap.query(`CREATE DATABASE IF NOT EXISTS \`${database}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`);
  await bootstrap.end();
  pool = mysql.createPool({ ...config, database });
  const connection = await pool.getConnection();
  try {
    const statements = fs.readFileSync(path.join(__dirname, '..', 'schema.sql'), 'utf8').split(';').map((statement) => statement.trim()).filter(Boolean);
    for (const statement of statements) await connection.query(statement);
    for (const name of ['Administrador', 'Empleado', 'Cliente']) await connection.query('INSERT IGNORE INTO roles (name) VALUES (?)', [name]);
    for (const name of ['users:read', 'users:write', 'products:read', 'products:write', 'services:read', 'services:write']) await connection.query('INSERT IGNORE INTO permisos (name) VALUES (?)', [name]);
    const [roles] = await connection.query('SELECT id, name FROM roles'); const [permissions] = await connection.query('SELECT id, name FROM permisos');
    const roleMap = Object.fromEntries(roles.map((role) => [role.name, role.id])); const permissionMap = Object.fromEntries(permissions.map((permission) => [permission.name, permission.id]));
    const grants = { Administrador: Object.keys(permissionMap), Empleado: ['services:read', 'services:write'], Cliente: ['products:read', 'services:read'] };
    for (const [role, granted] of Object.entries(grants)) for (const permission of granted) await connection.query('INSERT IGNORE INTO role_permisos (role_id, permiso_id) VALUES (?, ?)', [roleMap[role], permissionMap[permission]]);
    await connection.query('INSERT IGNORE INTO usuarios (name,last_name,document_type,document_number,address,phone,email,password_hash,role_id) VALUES (?,?,?,?,?,?,?,?,?)', ['Admin', 'SimonC', 'CC', '1000000001', 'Oficina principal', '3000000000', 'admin@simonsc.com', bcrypt.hashSync('Admin1234', 10), roleMap.Administrador]);
    await connection.query('INSERT IGNORE INTO usuarios (name,last_name,document_type,document_number,address,phone,email,password_hash,role_id) VALUES (?,?,?,?,?,?,?,?,?)', ['Empleado', 'SimonC', 'CC', '1000000002', 'Oficina principal', '3000000001', 'empleado@simonsc.com', bcrypt.hashSync('Empleado1234', 10), roleMap.Empleado]);
    await connection.query("INSERT IGNORE INTO productos (name,description,price) VALUES ('Branding Premium','Identidad visual estratégica para marcas.',850000),('E-commerce Avanzado','Tienda online orientada a conversión.',1500000)");
    await connection.query("INSERT IGNORE INTO servicios (name,description,price) VALUES ('Desarrollo web','Aplicaciones modernas y rápidas.',1200000),('Marketing UX','Optimización de experiencia de usuario.',650000)");
  } finally { connection.release(); }
}
module.exports = { pool, query, initializeDatabase };
