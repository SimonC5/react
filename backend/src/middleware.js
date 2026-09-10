const jwt = require('jsonwebtoken');

const secret = process.env.JWT_SECRET || 'simonsc-development-secret-change-me';
function authenticate(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ message: 'Token requerido.' });
  try {
    req.user = jwt.verify(token, secret);
    next();
  } catch {
    return res.status(401).json({ message: 'Token inválido o expirado.' });
  }
}
function authorize(...roles) {
  return (req, res, next) => roles.includes(req.user.role) ? next() : res.status(403).json({ message: 'No tienes permisos para esta acción.' });
}
module.exports = { authenticate, authorize, secret };
