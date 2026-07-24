import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL não encontrada no arquivo .env"
    )


def conectar():
    """
    Cria conexão com PostgreSQL.

    dict_row faz cada resultado funcionar como dicionário:

    linha["nome"]
    linha["preco"]
    """

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()

    # =====================================================
    # PRODUTOS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id BIGSERIAL PRIMARY KEY,

            item_id TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,

            preco DOUBLE PRECISION,
            preco_original DOUBLE PRECISION,
            desconto DOUBLE PRECISION,

            link_original TEXT,
            link_afiliado TEXT,

            imagem TEXT,

            enviado INTEGER DEFAULT 0,

            criado_em TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            enviado_em TIMESTAMP
        )
    """)

    # =====================================================
    # OPORTUNIDADES
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oportunidades (
            id BIGSERIAL PRIMARY KEY,

            ml_id TEXT UNIQUE NOT NULL,

            tipo TEXT NOT NULL,

            nome TEXT NOT NULL,

            imagem TEXT,

            fonte TEXT NOT NULL,

            ranking INTEGER,

            categoria TEXT,

            link_produto TEXT,

            preco DOUBLE PRECISION,

            preco_original DOUBLE PRECISION,

            desconto DOUBLE PRECISION,

            link_afiliado TEXT,

            status TEXT
                DEFAULT 'aguardando_link',

            descoberto_em TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            atualizado_em TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            publicado_em TIMESTAMP
        )
    """)

    # =====================================================
    # TENDÊNCIAS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tendencias (
            id BIGSERIAL PRIMARY KEY,

            palavra TEXT UNIQUE NOT NULL,

            url TEXT,

            posicao INTEGER,

            ativo INTEGER DEFAULT 1,

            descoberto_em TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            atualizado_em TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # HISTÓRICO
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_publicacoes (
            id BIGSERIAL PRIMARY KEY,

            ml_id TEXT NOT NULL,

            tipo TEXT,

            nome TEXT NOT NULL,

            imagem TEXT,

            categoria TEXT,

            ranking INTEGER,

            link_produto TEXT,

            link_afiliado TEXT,

            preco DOUBLE PRECISION,

            preco_original DOUBLE PRECISION,

            desconto DOUBLE PRECISION,

            telegram_message_id TEXT,

            publicado_em TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # ÍNDICES
    # =====================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_oportunidades_categoria
        ON oportunidades (categoria)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_oportunidades_status
        ON oportunidades (status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_oportunidades_ranking
        ON oportunidades (ranking)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_tendencias_posicao
        ON tendencias (posicao)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_historico_ml_id
        ON historico_publicacoes (
            ml_id,
            publicado_em
        )
    """)

    conexao.commit()

    cursor.close()
    conexao.close()

    print(
        "✅ PostgreSQL: tabelas verificadas "
        "com sucesso."
    )


if __name__ == "__main__":
    criar_tabelas()