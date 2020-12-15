SELECT id, nombre, documento, telefono FROM clientes
WHERE (tipo = 'N' OR tipo = 'G')
AND activo = True
AND fecha_inicio < current_date
AND (fecha_fin IS NULL OR fecha_fin > current_date)
