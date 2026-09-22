import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const CLAVE = 'simonsc_carrito';

const CartContext = createContext(null);

function leerGuardado() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE) || '[]');
    return Array.isArray(guardado) ? guardado : [];
  } catch {
    return [];
  }
}

/** Carrito de compras. Se guarda en el navegador para que sobreviva a una recarga. */
export function CartProvider({ children }) {
  const [items, setItems] = useState(leerGuardado);

  useEffect(() => {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(items));
    } catch {
      // Si el navegador no deja guardar, el carrito sigue funcionando en memoria.
    }
  }, [items]);

  const agregar = useCallback((articulo, cantidad = 1) => {
    setItems((actuales) => {
      const existente = actuales.find((item) => item.tipo === articulo.tipo && item.id === articulo.id);
      if (existente) {
        return actuales.map((item) =>
          item === existente ? { ...item, cantidad: item.cantidad + cantidad } : item,
        );
      }
      return [...actuales, { ...articulo, cantidad }];
    });
  }, []);

  const cambiarCantidad = useCallback((tipo, id, cantidad) => {
    setItems((actuales) =>
      actuales
        .map((item) => (item.tipo === tipo && item.id === id ? { ...item, cantidad } : item))
        .filter((item) => item.cantidad > 0),
    );
  }, []);

  const quitar = useCallback((tipo, id) => {
    setItems((actuales) => actuales.filter((item) => !(item.tipo === tipo && item.id === id)));
  }, []);

  const vaciar = useCallback(() => setItems([]), []);

  const valor = useMemo(() => {
    const unidades = items.reduce((suma, item) => suma + item.cantidad, 0);
    const total = items.reduce((suma, item) => suma + item.precio * item.cantidad, 0);
    return { items, unidades, total, agregar, cambiarCantidad, quitar, vaciar };
  }, [items, agregar, cambiarCantidad, quitar, vaciar]);

  return <CartContext.Provider value={valor}>{children}</CartContext.Provider>;
}

export function useCart() {
  const contexto = useContext(CartContext);
  if (!contexto) throw new Error('useCart debe usarse dentro de CartProvider');
  return contexto;
}
