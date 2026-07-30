CREATE TABLE IF NOT EXISTS oportunidades (
    id BIGSERIAL PRIMARY KEY,
    ml_id VARCHAR(100) NOT NULL,
    origem VARCHAR(50) NOT NULL DEFAULT 'mercadolivre',
    tipo VARCHAR(50),
    nome TEXT NOT NULL,
    imagem TEXT,
    fonte VARCHAR(100),
    ranking INTEGER,
    categoria VARCHAR(100),
    link_afiliado TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'aguardando_link',
    descoberto_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_oportunidades_origem_ml_id
ON oportunidades (origem, ml_id);

CREATE INDEX IF NOT EXISTS ix_oportunidades_status
ON oportunidades (status);

CREATE INDEX IF NOT EXISTS ix_oportunidades_categoria
ON oportunidades (categoria);

CREATE TABLE IF NOT EXISTS historico_publicacoes (
    id BIGSERIAL PRIMARY KEY,
    ml_id VARCHAR(100) NOT NULL,
    origem VARCHAR(50) NOT NULL DEFAULT 'mercadolivre',
    nome TEXT,
    imagem TEXT,
    link_afiliado TEXT,
    categoria VARCHAR(100),
    chat_id VARCHAR(100),
    mensagem_id VARCHAR(100),
    publicado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_historico_origem_ml_id
ON historico_publicacoes (origem, ml_id);

CREATE INDEX IF NOT EXISTS ix_historico_publicado_em
ON historico_publicacoes (publicado_em);

CREATE TABLE IF NOT EXISTS produtos (
    id BIGSERIAL PRIMARY KEY,
    item_id VARCHAR(100) NOT NULL,
    origem VARCHAR(50) NOT NULL DEFAULT 'mercadolivre',
    titulo TEXT,
    preco NUMERIC(14, 2),
    preco_original NUMERIC(14, 2),
    desconto NUMERIC(8, 2),
    link_original TEXT,
    link_afiliado TEXT,
    imagem TEXT,
    categoria VARCHAR(100),
    enviado BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enviado_em TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_origem_item_id
ON produtos (origem, item_id);

CREATE INDEX IF NOT EXISTS ix_produtos_enviado
ON produtos (enviado);

CREATE TABLE IF NOT EXISTS tendencias (
    id BIGSERIAL PRIMARY KEY,
    palavra VARCHAR(255) NOT NULL,
    url TEXT,
    posicao INTEGER,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    descoberta_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tendencias_palavra
ON tendencias (palavra);
