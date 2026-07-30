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

-- HISTÓRICO
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
ADD COLUMN IF NOT EXISTS atualizada_em TIMESTAMP;

UPDATE tendencias
SET atualizada_em = COALESCE(descoberta_em, CURRENT_TIMESTAMP)
WHERE atualizada_em IS NULL;

ALTER TABLE tendencias
ALTER COLUMN atualizada_em SET DEFAULT CURRENT_TIMESTAMP;

-- Remove índices únicos antigos incompatíveis, quando existirem.
DROP INDEX IF EXISTS ux_oportunidades_origem_ml_id;
DROP INDEX IF EXISTS ux_produtos_origem_item_id;

-- Remove duplicados antes de criar índices únicos compostos.
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
