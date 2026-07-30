from pathlib import Path

from database.database import conectar


PASTA_ATUAL = Path(__file__).resolve().parent


def _executar_sql_arquivo(nome_arquivo):
    caminho = PASTA_ATUAL / nome_arquivo

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo SQL não encontrado: {caminho}")

    sql = caminho.read_text(encoding="utf-8")
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(sql)
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()
        conexao.close()


def aplicar_schema():
    _executar_sql_arquivo("schema.sql")


def aplicar_migracoes():
    # Ordem obrigatória:
    # 1. cria tabelas ausentes sem depender das colunas novas;
    # 2. adiciona colunas;
    # 3. somente depois cria os índices que usam essas colunas.
    aplicar_schema()
    _executar_sql_arquivo("migration.sql")
    print("✅ PostgreSQL: schema e migrações aplicados com sucesso.")
