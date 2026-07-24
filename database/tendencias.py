from database.database import conectar


def salvar_tendencia(
    palavra,
    url=None,
    posicao=None
):
    """
    Cria ou atualiza uma tendência.

    Se a palavra já existir, atualiza:
    - URL
    - posição
    - ativo
    - atualizado_em
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
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
                %s,
                %s,
                %s,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT (palavra)

            DO UPDATE SET
                url = EXCLUDED.url,
                posicao = EXCLUDED.posicao,
                ativo = 1,
                atualizado_em =
                    CURRENT_TIMESTAMP
            """,
            (
                palavra,
                url,
                posicao,
            )
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def desativar_todas():
    """
    Marca todas as tendências como inativas.

    Normalmente usamos isso antes de uma nova coleta.
    As tendências encontradas novamente serão
    reativadas por salvar_tendencia().
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE tendencias

            SET
                ativo = 0,
                atualizado_em =
                    CURRENT_TIMESTAMP
            """
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def listar_tendencias(
    apenas_ativas=True
):
    conexao = conectar()
    cursor = conexao.cursor()

    if apenas_ativas:
        cursor.execute(
            """
            SELECT
                id,
                palavra,
                url,
                posicao,
                ativo,
                descoberto_em,
                atualizado_em

            FROM tendencias

            WHERE ativo = 1

            ORDER BY posicao ASC
            """
        )

    else:
        cursor.execute(
            """
            SELECT
                id,
                palavra,
                url,
                posicao,
                ativo,
                descoberto_em,
                atualizado_em

            FROM tendencias

            ORDER BY
                ativo DESC,
                posicao ASC
            """
        )

    tendencias = cursor.fetchall()

    cursor.close()
    conexao.close()

    return tendencias


def buscar_tendencia(
    palavra
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            palavra,
            url,
            posicao,
            ativo,
            descoberto_em,
            atualizado_em

        FROM tendencias

        WHERE palavra = %s

        LIMIT 1
        """,
        (palavra,)
    )

    tendencia = cursor.fetchone()

    cursor.close()
    conexao.close()

    return tendencia


def contar_tendencias(
    apenas_ativas=True
):
    conexao = conectar()
    cursor = conexao.cursor()

    if apenas_ativas:
        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM tendencias

            WHERE ativo = 1
            """
        )

    else:
        cursor.execute(
            """
            SELECT COUNT(*) AS total

            FROM tendencias
            """
        )

    resultado = cursor.fetchone()

    cursor.close()
    conexao.close()

    return resultado["total"]