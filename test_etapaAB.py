-- =====================================================================
-- Sistema de Gestión para Taller Mecánico
-- Etapa 1: Clientes y Autos
-- PostgreSQL (Neon)
-- =====================================================================

-- ---------------------------------------------------------------------
-- CLIENTES
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL,
    telefono        VARCHAR(30),          -- para el botón de WhatsApp (solo dígitos, con código de país)
    email           VARCHAR(150),
    direccion       VARCHAR(200),
    notas           TEXT,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes (nombre);
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes (telefono);

-- ---------------------------------------------------------------------
-- AUTOS (cada auto pertenece a un cliente)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS autos (
    id              SERIAL PRIMARY KEY,
    cliente_id      INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    marca           VARCHAR(60),
    modelo          VARCHAR(60),
    anio            SMALLINT,
    patente         VARCHAR(15),
    color           VARCHAR(30),
    kilometraje     INTEGER,
    vin             VARCHAR(40),          -- número de chasis (opcional)
    notas           TEXT,
    -- token único que va a servir para el QR del historial del vehículo (Etapa QR)
    qr_token        UUID NOT NULL DEFAULT gen_random_uuid(),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autos_cliente ON autos (cliente_id);
CREATE INDEX IF NOT EXISTS idx_autos_patente ON autos (patente);
CREATE UNIQUE INDEX IF NOT EXISTS idx_autos_qr_token ON autos (qr_token);

-- ---------------------------------------------------------------------
-- Trigger para mantener actualizado_en al día
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_actualizado_en()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_clientes_upd ON clientes;
CREATE TRIGGER trg_clientes_upd BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION set_actualizado_en();

DROP TRIGGER IF EXISTS trg_autos_upd ON autos;
CREATE TRIGGER trg_autos_upd BEFORE UPDATE ON autos
    FOR EACH ROW EXECUTE FUNCTION set_actualizado_en();
