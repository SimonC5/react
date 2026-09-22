"""Catálogo de demostración de SimonC: gafas de realidad virtual y servicios.

Es lo que la API siembra la primera vez que arranca. Los nombres son propios de
la tienda, no de marcas reales, y los precios están en pesos colombianos.
"""

PRODUCTOS = (
    ('SimonC Vision One', 'Gafas de realidad virtual autónomas con pantallas LCD de 2064x2208 por ojo y seguimiento de manos sin mandos.', 2950000),
    ('SimonC Vision Pro', 'Visor tope de gama con paneles micro-OLED 4K por ojo, seguimiento ocular y audio espacial.', 6800000),
    ('Nebula Quest 8', 'Visor autónomo de 128 GB: se usa sin cables y sin computador, listo en dos minutos.', 1890000),
    ('Nebula Quest 8 Plus', 'La versión de 512 GB del Quest 8, con correa de batería que duplica la autonomía.', 2450000),
    ('Orion Lite VR', 'Visor de 380 gramos pensado para jornadas largas de trabajo sin cansar el cuello.', 1350000),
    ('Orion Air Glasses', 'Gafas de 78 gramos que proyectan una pantalla virtual de 120 pulgadas delante de ti.', 1690000),
    ('Vertex Pro 120 Hz', 'Visor para PC con refresco de 120 Hz y lentes pancake: imagen nítida de borde a borde.', 3200000),
    ('Vertex Studio 5K', 'Visor de 5K para diseño e ingeniería, con estaciones de seguimiento externas.', 7400000),
    ('Helix Play VR', 'Visor de juego con mandos hápticos y gatillos adaptativos.', 2100000),
    ('Helix Kids Safe', 'Visor infantil con control parental, límite de tiempo y correa ajustable.', 890000),
    ('Aurora Mix AR', 'Realidad mixta con paso de cámara a color: ves tu sala y los objetos virtuales a la vez.', 4300000),
    ('Aurora Mix Business', 'Edición empresarial del Aurora Mix, con gestión remota de la flota de equipos.', 5600000),
    ('Titan Trainer VR', 'Visor reforzado con certificación IP54 para formación en planta e industria pesada.', 5100000),
    ('Titan Medic VR', 'Visor para simulación clínica, con superficies desinfectables y modo multiusuario.', 5900000),
    ('Pulse Fit VR', 'Visor deportivo con correa transpirable, funda lavable y sensor de ritmo cardiaco.', 1750000),
    ('Pulse Motion 360', 'Kit completo con visor y dos estaciones base para moverte libremente por la sala.', 3850000),
    ('Lumen Cinema VR', 'Visor para cine y video 360 con audio espacial y pantalla virtual panorámica.', 2250000),
    ('Lumen Travel', 'Visor plegable con estuche rígido: cabe en el maletín y aguanta el viaje.', 1480000),
    ('Quantum Glass 8K', 'Visor de 8K con campo de visión de 130 grados, el más nítido del catálogo.', 9900000),
    ('Quantum Glass Dev Kit', 'Kit de desarrollo con SDK, dos pares de mandos y licencia de soporte.', 8200000),
)

SERVICIOS = (
    ('Instalación y configuración de gafas VR', 'Dejamos el visor listo, calibrado y con tus cuentas configuradas.', 250000),
    ('Mantenimiento y limpieza de visores', 'Revisión, limpieza de lentes y cambio de espumas de contacto.', 180000),
    ('Garantía extendida 12 meses', 'Un año más de cobertura sobre pantallas, mandos y batería.', 320000),
    ('Capacitación básica en realidad virtual', 'Cuatro horas para que tu equipo pierda el miedo al visor y lo use bien.', 450000),
    ('Capacitación avanzada para equipos', 'Programa de veinte horas sobre creación y gestión de contenido inmersivo.', 1200000),
    ('Desarrollo de experiencia VR a medida', 'Diseñamos y programamos la experiencia completa para tu marca.', 6500000),
    ('Tour virtual 360 de inmuebles', 'Recorrido navegable de una propiedad, listo para publicar en tu web.', 2800000),
    ('Showroom virtual de productos', 'Sala de exhibición inmersiva donde el cliente toma y gira cada producto.', 3400000),
    ('Simulador de entrenamiento industrial', 'Simulación de una tarea de planta para entrenar sin detener la producción.', 7900000),
    ('Simulación clínica en realidad virtual', 'Escenarios médicos para practicar procedimientos sin riesgo para el paciente.', 8400000),
    ('Modelado 3D de productos para VR', 'Convertimos tus productos en modelos 3D optimizados para el visor.', 1900000),
    ('Escaneo 3D de espacios reales', 'Escaneamos tu local o tu planta y lo reconstruimos dentro de la experiencia.', 2300000),
    ('Video 360 y edición inmersiva', 'Grabación, montaje y publicación de video envolvente.', 2600000),
    ('Audio espacial para experiencias VR', 'Diseño sonoro tridimensional que ubica cada sonido en el espacio.', 1100000),
    ('Arriendo de gafas VR por evento', 'Diez visores por un día, con contenido cargado y personal de apoyo.', 900000),
    ('Montaje de sala VR para eventos', 'Zona inmersiva completa: equipos, mobiliario, montaje y desmontaje.', 3100000),
    ('Soporte técnico en sitio', 'Un técnico va a tu sede y resuelve el problema el mismo día.', 380000),
    ('Actualización de firmware y software', 'Dejamos toda la flota en la última versión estable y probada.', 220000),
    ('Consultoría en realidad virtual para empresas', 'Diagnóstico y hoja de ruta para llevar la VR a tu operación.', 2000000),
    ('Publicación de la app VR en tiendas', 'Preparamos y publicamos tu aplicación en las tiendas de los visores.', 1400000),
)

# Catálogo genérico del avance anterior. No tiene que ver con la realidad
# virtual, así que se oculta de la tienda en vez de borrarse: las ventas
# antiguas siguen apuntando a esos nombres.
RETIRADOS = (
    ('productos', 'Branding Premium'),
    ('productos', 'E-commerce Avanzado'),
    ('servicios', 'Desarrollo web'),
    ('servicios', 'Marketing UX'),
)

SEED = tuple(('productos', *fila) for fila in PRODUCTOS) + tuple(('servicios', *fila) for fila in SERVICIOS)
