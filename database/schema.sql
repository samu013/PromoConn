-- Este arquivo cria somente as tabelas básicas.
-- As colunas e os índices de compatibilidade são aplicados em migration.sql.

CREATE TABLE IF NOT EXISTS oportunidades (
    id BIGSERIAL PRIMARY KEY,
    ml_id VARCHAR(100) NOT NULL,
    tipo VARCHAR(50),
    nome TEXT NOT NULL,
    imagem TEXT,
    fonte VARCHAR(100),
    ranking INTEGER,
    categoria VARCHAR(100),
    link_afiliado TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'aguardando_link',
    descoberto_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historico_publicacoes (
    id BIGSERIAL PRIMARY KEY,
    ml_id VARCHAR(100) NOT NULL,
    nome TEXT,
    imagem TEXT,
    link_afiliado TEXT,
    publicado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS produtos (
    id BIGSERIAL PRIMARY KEY,
    item_id VARCHAR(100) NOT NULL,
    titulo TEXT,
    preco NUMERIC(14, 2),
    preco_original NUMERIC(14, 2),
    desconto NUMERIC(8, 2),
    link_original TEXT,
    link_afiliado TEXT,
    imagem TEXT,
    enviado BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enviado_em TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tendencias (
    id BIGSERIAL PRIMARY KEY,
    palavra VARCHAR(255) NOT NULL,
    url TEXT,
    posicao INTEGER,
    descoberta_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
