-- Posiciones de las tablas para el Diseñador de phpMyAdmin.
--
-- Cómo usarlo: en phpMyAdmin, pestaña SQL (la de arriba, sin entrar a ninguna
-- base), pega este archivo entero y dale Continuar. Después entra a la base
-- simonsc y abre la pestaña Diseñador: las tablas aparecen ya colocadas, de
-- izquierda a derecha siguiendo las dependencias.
--
-- Las posiciones no viven en la base simonsc sino en la base de configuración
-- de phpMyAdmin, que en XAMPP se llama phpmyadmin. Si en tu instalación tiene
-- otro nombre, cámbialo en las líneas de abajo.
--
-- Se puede volver a ejecutar cuantas veces se quiera: primero borra la
-- distribución anterior y luego la vuelve a crear.

DELETE FROM phpmyadmin.pma__table_coords
  WHERE pdf_page_number IN (
    SELECT page_nr FROM phpmyadmin.pma__pdf_pages
    WHERE db_name = 'simonsc' AND page_descr = 'simonsc'
  );

DELETE FROM phpmyadmin.pma__pdf_pages
  WHERE db_name = 'simonsc' AND page_descr = 'simonsc';

INSERT INTO phpmyadmin.pma__pdf_pages (db_name, page_descr) VALUES ('simonsc', 'simonsc');

SET @pagina = LAST_INSERT_ID();

INSERT INTO phpmyadmin.pma__table_coords (db_name, table_name, pdf_page_number, x, y) VALUES
  -- Columna 1: seguridad.
  ('simonsc', 'roles',            @pagina,   40,   40),
  ('simonsc', 'permisos',         @pagina,   40,  230),
  ('simonsc', 'role_permisos',    @pagina,   40,  420),
  -- Columna 2: usuarios y el catálogo, que no depende de nadie.
  ('simonsc', 'usuarios',         @pagina,  340,   40),
  ('simonsc', 'productos',        @pagina,  340,  560),
  ('simonsc', 'servicios',        @pagina,  340,  760),
  -- Columna 3: todo lo que apunta a usuarios.
  ('simonsc', 'ventas',           @pagina,  700,   40),
  ('simonsc', 'pqr',              @pagina,  700,  520),
  ('simonsc', 'conversaciones',   @pagina,  700,  880),
  ('simonsc', 'recuperaciones',   @pagina,  700, 1120),
  -- Columna 4: lo que cuelga de la columna anterior.
  ('simonsc', 'detalle_ventas',   @pagina, 1060,   40),
  ('simonsc', 'facturas',         @pagina, 1060,  420),
  ('simonsc', 'mensajes',         @pagina, 1060,  880),
  -- Columna 5: el detalle de la factura.
  ('simonsc', 'detalle_facturas', @pagina, 1420,  420);
