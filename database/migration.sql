BEGIN;

-- OPORTUNIDADES
ALTER TABLE oportunidades
ADD COLUMN IF NOT EXISTS origem VARCHAR(50);

UPDATE oportunidades
SET origem = 'mercadolivre'
WHERE origem IS NULL OR BTRIM(origem) = '';

ALTER TABLE oportunidades
ALTER COLUMN origem SET DEFAULT 'mercadolivre';

ALTER TABLE oportunidades
ALTER COLUMN origem SET NOT NULL;

ALTER TABLE oportunidades
ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP;

UPDATE oportunidades
SET atualizado_em = COALESCE(descoberto_em, CURRENT_TIMESTAMP)
WHERE atualizado_em IS NULL;

ALTER TABLE oportunidades
ALTER COLUMN atualizado_em SET DEFAULT CURRENT_TIMESTAMP;


-- HISTÓRICO DE PUBLICAÇÕES
ALTER TABLE historico_publicacoes
ADD COLUMN IF NOT EXISTS origem VARCHAR(50);

UPDATE historico_publicacoes
SET origem = 'mercadolivre'
WHERE origem IS NULL OR BTRIM(origem) = '';

ALTER TABLE historico_publicacoes
ALTER COLUMN origem SET DEFAULT 'mercadolivre';

ALTER TABLE historico_publicacoes
ALTER COLUMN origem SET NOT NULL;

ALTER TABLE historico_publicacoes
ADD COLUMN IF NOT EXISTS categoria VARCHAR(100);

ALTER TABLE historico_publicacoes
ADD COLUMN IF NOT EXISTS chat_id VARCHAR(100);

ALTER TABLE historico_publicacoes
ADD COLUMN IF NOT EXISTS mensagem_id VARCHAR(100);


-- PRODUTOS
ALTER TABLE produtos
ADD COLUMN IF NOT EXISTS origem VARCHAR(50);

UPDATE produtos
SET origem = 'mercadolivre'
WHERE origem IS NULL OR BTRIM(origem) = '';

ALTER TABLE produtos
ALTER COLUMN origem SET DEFAULT 'mercadolivre';

ALTER TABLE produtos
ALTER COLUMN origem SET NOT NULL;

ALTER TABLE produtos
ADD COLUMN IF NOT EXISTS categoria VARCHAR(100);


-- TENDÊNCIAS
ALTER TABLE tendencias
ADD COLUMN IF NOT EXISTS ativa BOOLEAN;

UPDATE tendencias
SET ativa = TRUE
WHERE ativa IS NULL;

ALTER TABLE tendencias
ALTER COLUMN ativa SET DEFAULT TRUE;

ALTER TABLE tendencias
ALTER COLUMN ativa SET NOT NULL;

ALTER TABLE tendencias
ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP;

-- Compatibilidade com bancos que possuem descoberto_em ou descoberta_em.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'tendencias'
          AND column_name = 'descoberto_em'
    ) THEN
        EXECUTE '
            UPDATE tendencias
            SET atualizado_em = COALESCE(descoberto_em, CURRENT_TIMESTAMP)
            WHERE atualizado_em IS NULL
        ';

    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'tendencias'
          AND column_name = 'descoberta_em'
    ) THEN
        EXECUTE '
            UPDATE tendencias
            SET atualizado_em = COALESCE(descoberta_em, CURRENT_TIMESTAMP)
            WHERE atualizado_em IS NULL
        ';

    ELSE
        UPDATE tendencias
        SET atualizado_em = CURRENT_TIMESTAMP
        WHERE atualizado_em IS NULL;
    END IF;
END
$$;

ALTER TABLE tendencias
ALTER COLUMN atualizado_em SET DEFAULT CURRENT_TIMESTAMP;


-- Remove duplicados antes dos índices únicos.
DELETE FROM oportunidades a
USING oportunidades b
WHERE a.id < b.id
  AND a.origem = b.origem
  AND a.ml_id = b.ml_id;

DELETE FROM produtos a
USING produtos b
WHERE a.id < b.id
  AND a.origem = b.origem
  AND a.item_id = b.item_id;


-- ÍNDICES
CREATE UNIQUE INDEX IF NOT EXISTS ux_oportunidades_origem_ml_id
ON oportunidades (origem, ml_id);

CREATE INDEX IF NOT EXISTS ix_oportunidades_status
ON oportunidades (status);

CREATE INDEX IF NOT EXISTS ix_oportunidades_categoria
ON oportunidades (categoria);

CREATE INDEX IF NOT EXISTS ix_historico_origem_ml_id
ON historico_publicacoes (origem, ml_id);

CREATE INDEX IF NOT EXISTS ix_historico_publicado_em
ON historico_publicacoes (publicado_em);

CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_origem_item_id
ON produtos (origem, item_id);

CREATE INDEX IF NOT EXISTS ix_produtos_enviado
ON produtos (enviado);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tendencias_palavra
ON tendencias (palavra);

COMMIT;
