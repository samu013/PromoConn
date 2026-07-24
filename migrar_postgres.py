import os
import sqlite3

import psycopg
from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÕES
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CAMINHO_SQLITE = os.path.join(
    "data",
    "bot_promocoes.db"
)


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL não encontrada no arquivo .env"
    )


if not os.path.exists(CAMINHO_SQLITE):
    raise FileNotFoundError(
        f"Banco SQLite não encontrado: {CAMINHO_SQLITE}"
    )


# ============================================================
# CONEXÕES
# ============================================================

def conectar_sqlite():
    conexao = sqlite3.connect(CAMINHO_SQLITE)

    conexao.row_factory = sqlite3.Row

    return conexao


def conectar_postgres():
    return psycopg.connect(DATABASE_URL)


# ============================================================
# CRIAR TABELAS POSTGRESQL
# ============================================================

def criar_tabelas_postgres(conexao):
    cursor = conexao.cursor()

    # --------------------------------------------------------
    # PRODUTOS
    # --------------------------------------------------------

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
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            enviado_em TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # OPORTUNIDADES
    # --------------------------------------------------------

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
            status TEXT DEFAULT 'aguardando_link',
            descoberto_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            publicado_em TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # TENDÊNCIAS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tendencias (
            id BIGSERIAL PRIMARY KEY,
            palavra TEXT UNIQUE NOT NULL,
            url TEXT,
            posicao INTEGER,
            ativo INTEGER DEFAULT 1,
            descoberto_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

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
            publicado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_historico_ml_id
        ON historico_publicacoes (
            ml_id,
            publicado_em
        )
    """)

    conexao.commit()

    cursor.close()


# ============================================================
# VERIFICAR SE TABELA EXISTE NO SQLITE
# ============================================================

def tabela_existe_sqlite(conexao, tabela):
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (tabela,)
    )

    existe = cursor.fetchone() is not None

    cursor.close()

    return existe


# ============================================================
# DESCOBRIR COLUNAS DO SQLITE
# ============================================================

def obter_colunas_sqlite(conexao, tabela):
    cursor = conexao.cursor()

    cursor.execute(
        f"PRAGMA table_info({tabela})"
    )

    colunas = {
        linha["name"]
        for linha in cursor.fetchall()
    }

    cursor.close()

    return colunas


# ============================================================
# LER VALOR COM SEGURANÇA
# ============================================================

def valor(linha, colunas, nome, padrao=None):
    if nome not in colunas:
        return padrao

    resultado = linha[nome]

    if resultado is None:
        return padrao

    return resultado


# ============================================================
# MIGRAR PRODUTOS
# ============================================================

def migrar_produtos(sqlite, postgres):
    tabela = "produtos"

    if not tabela_existe_sqlite(
        sqlite,
        tabela
    ):
        print("⚠️ Tabela produtos não existe no SQLite.")
        return 0

    colunas = obter_colunas_sqlite(
        sqlite,
        tabela
    )

    cursor_sqlite = sqlite.cursor()
    cursor_postgres = postgres.cursor()

    cursor_sqlite.execute("""
        SELECT *
        FROM produtos
        ORDER BY id
    """)

    linhas = cursor_sqlite.fetchall()

    quantidade = 0

    for linha in linhas:
        cursor_postgres.execute(
            """
            INSERT INTO produtos (
                item_id,
                titulo,
                preco,
                preco_original,
                desconto,
                link_original,
                link_afiliado,
                imagem,
                enviado,
                criado_em,
                enviado_em
            )

            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )

            ON CONFLICT (item_id)
            DO UPDATE SET

                titulo = EXCLUDED.titulo,
                preco = EXCLUDED.preco,
                preco_original =
                    EXCLUDED.preco_original,
                desconto = EXCLUDED.desconto,
                link_original =
                    EXCLUDED.link_original,
                link_afiliado =
                    EXCLUDED.link_afiliado,
                imagem = EXCLUDED.imagem,
                enviado = EXCLUDED.enviado,
                enviado_em =
                    EXCLUDED.enviado_em
            """,
            (
                valor(
                    linha,
                    colunas,
                    "item_id"
                ),

                valor(
                    linha,
                    colunas,
                    "titulo"
                ),

                valor(
                    linha,
                    colunas,
                    "preco"
                ),

                valor(
                    linha,
                    colunas,
                    "preco_original"
                ),

                valor(
                    linha,
                    colunas,
                    "desconto"
                ),

                valor(
                    linha,
                    colunas,
                    "link_original"
                ),

                valor(
                    linha,
                    colunas,
                    "link_afiliado"
                ),

                valor(
                    linha,
                    colunas,
                    "imagem"
                ),

                valor(
                    linha,
                    colunas,
                    "enviado",
                    0
                ),

                valor(
                    linha,
                    colunas,
                    "criado_em"
                ),

                valor(
                    linha,
                    colunas,
                    "enviado_em"
                ),
            )
        )

        quantidade += 1

    cursor_sqlite.close()
    cursor_postgres.close()

    return quantidade


# ============================================================
# MIGRAR OPORTUNIDADES
# ============================================================

def migrar_oportunidades(sqlite, postgres):
    tabela = "oportunidades"

    if not tabela_existe_sqlite(
        sqlite,
        tabela
    ):
        print("⚠️ Tabela oportunidades não existe.")
        return 0

    colunas = obter_colunas_sqlite(
        sqlite,
        tabela
    )

    cursor_sqlite = sqlite.cursor()
    cursor_postgres = postgres.cursor()

    cursor_sqlite.execute("""
        SELECT *
        FROM oportunidades
        ORDER BY id
    """)

    linhas = cursor_sqlite.fetchall()

    quantidade = 0

    for linha in linhas:
        cursor_postgres.execute(
            """
            INSERT INTO oportunidades (
                ml_id,
                tipo,
                nome,
                imagem,
                fonte,
                ranking,
                categoria,
                link_produto,
                preco,
                preco_original,
                desconto,
                link_afiliado,
                status,
                descoberto_em,
                atualizado_em,
                publicado_em
            )

            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )

            ON CONFLICT (ml_id)
            DO UPDATE SET

                tipo = EXCLUDED.tipo,
                nome = EXCLUDED.nome,
                imagem = EXCLUDED.imagem,
                fonte = EXCLUDED.fonte,
                ranking = EXCLUDED.ranking,
                categoria = EXCLUDED.categoria,

                link_produto =
                    EXCLUDED.link_produto,

                preco = EXCLUDED.preco,

                preco_original =
                    EXCLUDED.preco_original,

                desconto =
                    EXCLUDED.desconto,

                link_afiliado =
                    EXCLUDED.link_afiliado,

                status =
                    EXCLUDED.status,

                atualizado_em =
                    EXCLUDED.atualizado_em,

                publicado_em =
                    EXCLUDED.publicado_em
            """,
            (
                valor(
                    linha,
                    colunas,
                    "ml_id"
                ),

                valor(
                    linha,
                    colunas,
                    "tipo"
                ),

                valor(
                    linha,
                    colunas,
                    "nome"
                ),

                valor(
                    linha,
                    colunas,
                    "imagem"
                ),

                valor(
                    linha,
                    colunas,
                    "fonte",
                    "desconhecida"
                ),

                valor(
                    linha,
                    colunas,
                    "ranking"
                ),

                valor(
                    linha,
                    colunas,
                    "categoria"
                ),

                valor(
                    linha,
                    colunas,
                    "link_produto"
                ),

                valor(
                    linha,
                    colunas,
                    "preco"
                ),

                valor(
                    linha,
                    colunas,
                    "preco_original"
                ),

                valor(
                    linha,
                    colunas,
                    "desconto"
                ),

                valor(
                    linha,
                    colunas,
                    "link_afiliado"
                ),

                valor(
                    linha,
                    colunas,
                    "status",
                    "aguardando_link"
                ),

                valor(
                    linha,
                    colunas,
                    "descoberto_em"
                ),

                valor(
                    linha,
                    colunas,
                    "atualizado_em"
                ),

                valor(
                    linha,
                    colunas,
                    "publicado_em"
                ),
            )
        )

        quantidade += 1

    cursor_sqlite.close()
    cursor_postgres.close()

    return quantidade


# ============================================================
# MIGRAR TENDÊNCIAS
# ============================================================

def migrar_tendencias(sqlite, postgres):
    tabela = "tendencias"

    if not tabela_existe_sqlite(
        sqlite,
        tabela
    ):
        print("⚠️ Tabela tendencias não existe.")
        return 0

    colunas = obter_colunas_sqlite(
        sqlite,
        tabela
    )

    cursor_sqlite = sqlite.cursor()
    cursor_postgres = postgres.cursor()

    cursor_sqlite.execute("""
        SELECT *
        FROM tendencias
        ORDER BY id
    """)

    linhas = cursor_sqlite.fetchall()

    quantidade = 0

    for linha in linhas:
        cursor_postgres.execute(
            """
            INSERT INTO tendencias (
                palavra,
                url,
                posicao,
                ativo,
                descoberto_em,
                atualizado_em
            )

            VALUES (
                %s, %s, %s,
                %s, %s, %s
            )

            ON CONFLICT (palavra)
            DO UPDATE SET

                url = EXCLUDED.url,
                posicao = EXCLUDED.posicao,
                ativo = EXCLUDED.ativo,
                atualizado_em =
                    EXCLUDED.atualizado_em
            """,
            (
                valor(
                    linha,
                    colunas,
                    "palavra"
                ),

                valor(
                    linha,
                    colunas,
                    "url"
                ),

                valor(
                    linha,
                    colunas,
                    "posicao"
                ),

                valor(
                    linha,
                    colunas,
                    "ativo",
                    1
                ),

                valor(
                    linha,
                    colunas,
                    "descoberto_em"
                ),

                valor(
                    linha,
                    colunas,
                    "atualizado_em"
                ),
            )
        )

        quantidade += 1

    cursor_sqlite.close()
    cursor_postgres.close()

    return quantidade


# ============================================================
# MIGRAR HISTÓRICO
# ============================================================

def migrar_historico(sqlite, postgres):
    tabela = "historico_publicacoes"

    if not tabela_existe_sqlite(
        sqlite,
        tabela
    ):
        print(
            "⚠️ Tabela historico_publicacoes "
            "não existe no SQLite."
        )

        return 0

    colunas = obter_colunas_sqlite(
        sqlite,
        tabela
    )

    cursor_sqlite = sqlite.cursor()
    cursor_postgres = postgres.cursor()

    cursor_sqlite.execute("""
        SELECT *
        FROM historico_publicacoes
        ORDER BY id
    """)

    linhas = cursor_sqlite.fetchall()

    quantidade = 0

    for linha in linhas:
        # O histórico não tem UNIQUE em ml_id,
        # pois um produto poderá ser republicado
        # depois do período configurado.

        cursor_postgres.execute(
            """
            INSERT INTO historico_publicacoes (
                ml_id,
                tipo,
                nome,
                imagem,
                categoria,
                ranking,
                link_produto,
                link_afiliado,
                preco,
                preco_original,
                desconto,
                telegram_message_id,
                publicado_em
            )

            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s
            )
            """,
            (
                valor(
                    linha,
                    colunas,
                    "ml_id"
                ),

                valor(
                    linha,
                    colunas,
                    "tipo"
                ),

                valor(
                    linha,
                    colunas,
                    "nome"
                ),

                valor(
                    linha,
                    colunas,
                    "imagem"
                ),

                valor(
                    linha,
                    colunas,
                    "categoria"
                ),

                valor(
                    linha,
                    colunas,
                    "ranking"
                ),

                valor(
                    linha,
                    colunas,
                    "link_produto"
                ),

                valor(
                    linha,
                    colunas,
                    "link_afiliado"
                ),

                valor(
                    linha,
                    colunas,
                    "preco"
                ),

                valor(
                    linha,
                    colunas,
                    "preco_original"
                ),

                valor(
                    linha,
                    colunas,
                    "desconto"
                ),

                valor(
                    linha,
                    colunas,
                    "telegram_message_id"
                ),

                valor(
                    linha,
                    colunas,
                    "publicado_em"
                ),
            )
        )

        quantidade += 1

    cursor_sqlite.close()
    cursor_postgres.close()

    return quantidade


# ============================================================
# CONTAR REGISTROS
# ============================================================

def contar_sqlite(
    conexao,
    tabela
):
    if not tabela_existe_sqlite(
        conexao,
        tabela
    ):
        return 0

    cursor = conexao.cursor()

    cursor.execute(
        f"SELECT COUNT(*) FROM {tabela}"
    )

    total = cursor.fetchone()[0]

    cursor.close()

    return total


def contar_postgres(
    conexao,
    tabela
):
    cursor = conexao.cursor()

    cursor.execute(
        f"SELECT COUNT(*) FROM {tabela}"
    )

    total = cursor.fetchone()[0]

    cursor.close()

    return total


# ============================================================
# EXECUTAR MIGRAÇÃO
# ============================================================

def migrar():
    print()
    print("=" * 65)
    print("MIGRAÇÃO SQLITE → POSTGRESQL")
    print("=" * 65)

    sqlite = conectar_sqlite()
    postgres = conectar_postgres()

    try:
        print()
        print("1. Criando tabelas no PostgreSQL...")

        criar_tabelas_postgres(
            postgres
        )

        print("✅ Estrutura criada.")

        print()
        print("2. Migrando produtos...")

        produtos = migrar_produtos(
            sqlite,
            postgres
        )

        print(
            f"✅ {produtos} registro(s) processado(s)."
        )

        print()
        print("3. Migrando oportunidades...")

        oportunidades = (
            migrar_oportunidades(
                sqlite,
                postgres
            )
        )

        print(
            f"✅ {oportunidades} registro(s) processado(s)."
        )

        print()
        print("4. Migrando tendências...")

        tendencias = migrar_tendencias(
            sqlite,
            postgres
        )

        print(
            f"✅ {tendencias} registro(s) processado(s)."
        )

        print()
        print("5. Migrando histórico...")

        historico = migrar_historico(
            sqlite,
            postgres
        )

        print(
            f"✅ {historico} registro(s) processado(s)."
        )

        postgres.commit()

        # ====================================================
        # CONFERÊNCIA
        # ====================================================

        print()
        print("=" * 65)
        print("CONFERÊNCIA")
        print("=" * 65)

        tabelas = [
            "produtos",
            "oportunidades",
            "tendencias",
            "historico_publicacoes",
        ]

        for tabela in tabelas:
            total_sqlite = contar_sqlite(
                sqlite,
                tabela
            )

            total_postgres = contar_postgres(
                postgres,
                tabela
            )

            status = (
                "✅"
                if total_sqlite
                == total_postgres
                else "⚠️"
            )

            print()
            print(tabela)
            print(
                f"  SQLite:     {total_sqlite}"
            )
            print(
                f"  PostgreSQL: {total_postgres}"
            )
            print(
                f"  Status:     {status}"
            )

        print()
        print("=" * 65)
        print("✅ MIGRAÇÃO FINALIZADA")
        print("=" * 65)

    except Exception as erro:
        postgres.rollback()

        print()
        print("❌ ERRO DURANTE A MIGRAÇÃO")
        print()
        print(erro)

        raise

    finally:
        sqlite.close()
        postgres.close()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    migrar()