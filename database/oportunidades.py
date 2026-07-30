from datetime import datetime, timedelta

from database.database import conectar


DIAS_PARA_REPUBLICAR = 7


def foi_publicado_recentemente(
    ml_id,
    dias=DIAS_PARA_REPUBLICAR
):
    conexao = conectar()
    cursor = conexao.cursor()

    data_limite = (
        datetime.now()
        - timedelta(days=dias)
    )

    cursor.execute(
        """
        SELECT id
        FROM historico_publicacoes

        WHERE ml_id = %s
          AND publicado_em >= %s

        LIMIT 1
        """,
        (
            str(ml_id),
            data_limite,
        )
    )

    encontrado = (
        cursor.fetchone()
        is not None
    )

    cursor.close()
    conexao.close()

    return encontrado


def salvar_oportunidade(
    produto,
    fonte="highlights",
    categoria=None
):
    """
    Salva ou atualiza uma oportunidade.

    Retorna:
        True  -> oportunidade nova
        False -> já existia ou foi publicada recentemente

    Importante:
        a categoria de uma oportunidade existente não é
        sobrescrita por outra categoria de Highlights.
        Isso evita que um mesmo produto mude de grupo
        dependendo da ordem das consultas.
    """

    produto_id = str(
        produto["id"]
    )

    if foi_publicado_recentemente(
        produto_id
    ):
        return False

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                categoria

            FROM oportunidades

            WHERE ml_id = %s
            """,
            (produto_id,)
        )

        existente = cursor.fetchone()

        if existente:
            cursor.execute(
                """
                UPDATE oportunidades

                SET
                    tipo = %s,
                    nome = %s,
                    imagem = %s,
                    fonte = %s,
                    ranking = %s,

                    categoria = CASE
                        WHEN categoria IS NULL
                          OR TRIM(categoria) = ''
                        THEN %s
                        ELSE categoria
                    END,

                    atualizado_em =
                        CURRENT_TIMESTAMP

                WHERE ml_id = %s
                """,
                (
                    produto["tipo"],
                    produto["nome"],
                    produto.get("imagem"),
                    fonte,
                    produto.get("ranking"),
                    categoria,
                    produto_id,
                )
            )

            novo = False

        else:
            cursor.execute(
                """
                INSERT INTO oportunidades (
                    ml_id,
                    tipo,
                    nome,
                    imagem,
                    fonte,
                    ranking,
                    categoria,
                    status,
                    descoberto_em,
                    atualizado_em
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'aguardando_link',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    produto_id,
                    produto["tipo"],
                    produto["nome"],
                    produto.get("imagem"),
                    fonte,
                    produto.get("ranking"),
                    categoria,
                )
            )

            novo = True

        conexao.commit()

        return novo

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def buscar_oportunidade_por_id(
    oportunidade_id
):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT *
        FROM oportunidades

        WHERE id = %s
        """,
        (oportunidade_id,)
    )

    oportunidade = cursor.fetchone()

    cursor.close()
    conexao.close()

    return oportunidade


def excluir_oportunidade(
    oportunidade_id
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM oportunidades
            WHERE id = %s
            """,
            (oportunidade_id,)
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def contar_oportunidades():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM oportunidades
        """
    )

    resultado = cursor.fetchone()

    cursor.close()
    conexao.close()

    return resultado["total"]
