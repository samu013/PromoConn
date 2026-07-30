import os

import psycopg2
from psycopg2.extras import RealDictCursor


def obter_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "A variável de ambiente DATABASE_URL não foi configurada."
        )

    # Alguns provedores ainda fornecem postgres://.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    return database_url


def conectar():
    return psycopg2.connect(
        obter_database_url(),
        cursor_factory=RealDictCursor,
        connect_timeout=15,
    )


def criar_tabelas():
    """
    Mantém compatibilidade com o restante do projeto.

    A aplicação pode continuar chamando criar_tabelas(), mas agora essa
    função também aplica as migrações necessárias.
    """

    from database.migrator import aplicar_migracoes

    aplicar_migracoes()
