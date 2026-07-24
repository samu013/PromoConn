from database.database import conectar


def salvar_canal(
    nome,
    categoria,
    chat_id,
    ativo=True,
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO telegram_canais (
                nome,
                categoria,
                chat_id,
                ativo,
                criado_em,
                atualizado_em
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT (categoria)

            DO UPDATE SET
                nome = EXCLUDED.nome,
                chat_id = EXCLUDED.chat_id,
                ativo = EXCLUDED.ativo,
                atualizado_em = CURRENT_TIMESTAMP
            """,
            (
                nome,
                categoria,
                chat_id,
                ativo,
            )
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def buscar_canal_por_categoria(
    categoria
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            categoria,
            chat_id,
            ativo
        FROM telegram_canais
        WHERE categoria = %s
          AND ativo = TRUE
        LIMIT 1
        """,
        (categoria,)
    )

    canal = cursor.fetchone()

    cursor.close()
    conexao.close()

    return canal


def listar_canais(
    apenas_ativos=False
):
    conexao = conectar()
    cursor = conexao.cursor()

    if apenas_ativos:
        cursor.execute(
            """
            SELECT
                id,
                nome,
                categoria,
                chat_id,
                ativo
            FROM telegram_canais
            WHERE ativo = TRUE
            ORDER BY categoria ASC
            """
        )
    else:
        cursor.execute(
            """
            SELECT
                id,
                nome,
                categoria,
                chat_id,
                ativo
            FROM telegram_canais
            ORDER BY categoria ASC
            """
        )

    canais = cursor.fetchall()

    cursor.close()
    conexao.close()

    return canais


def desativar_canal(
    categoria
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE telegram_canais

            SET
                ativo = FALSE,
                atualizado_em =
                    CURRENT_TIMESTAMP

            WHERE categoria = %s
            """,
            (categoria,)
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()