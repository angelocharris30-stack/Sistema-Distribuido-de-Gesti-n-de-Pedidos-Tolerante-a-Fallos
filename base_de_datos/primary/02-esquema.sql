CREATE TABLE IF NOT EXISTS pedidos (
    id               BIGSERIAL     PRIMARY KEY,   -- identificador interno; el número que ve el usuario se calcula (ver backend/app/repo.py)
    cliente          VARCHAR(120)  NOT NULL,
    producto         VARCHAR(120)  NOT NULL,
    cantidad         INTEGER       NOT NULL CHECK (cantidad > 0),
    precio_unitario  NUMERIC(10,2) NOT NULL CHECK (precio_unitario > 0),
    estado           VARCHAR(20)   NOT NULL DEFAULT 'pendiente'
                     CHECK (estado IN ('pendiente','en_proceso','enviado','entregado')),
    version          INTEGER       NOT NULL DEFAULT 1,
    idempotency_key  VARCHAR(100)  UNIQUE,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos (estado) WHERE deleted_at IS NULL;

INSERT INTO pedidos (cliente, producto, cantidad, precio_unitario, estado) VALUES
 ('Laura Gómez',  'Monitor 24"',        1, 689900.00, 'pendiente'),
 ('Carlos Pérez', 'Teclado mecánico',   2, 189900.00, 'en_proceso'),
 ('Marta Ruiz',   'Mouse inalámbrico',  3,  59900.00, 'enviado');
