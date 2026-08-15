from datetime import (
    datetime,
    timedelta,
    timezone,
)

from database.database import conectar


PROVEDOR = "mercadolivre"


def buscar_tokens():
    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                provedor,
                access_token,
                refresh_token,
                expires_in,
                expira_em,
                atualizado_em

            FROM mercadolivre_tokens

            WHERE provedor = %s

            LIMIT 1
            """,
            (
                PROVEDOR,
            ),
        )

        return cursor.fetchone()

    finally:
        cursor.close()
        conexao.close()


def salvar_tokens(
    access_token,
    refresh_token,
    expires_in=None,
):
    access_token = str(
        access_token
        or ""
    ).strip()

    refresh_token = str(
        refresh_token
        or ""
    ).strip()

    if not access_token:
        raise ValueError(
            "access_token vazio."
        )

    if not refresh_token:
        raise ValueError(
            "refresh_token vazio."
        )

    expira_em = None

    if expires_in is not None:
        try:
            expires_in = int(
                expires_in
            )

            # Margem de 60 segundos para não usar
            # um token que esteja prestes a expirar.
            segundos_validos = max(
                0,
                expires_in - 60,
            )

            expira_em = (
                datetime.now(
                    timezone.utc
                )
                + timedelta(
                    seconds=
                        segundos_validos
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            expires_in = None
            expira_em = None

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO mercadolivre_tokens (
                provedor,
                access_token,
                refresh_token,
                expires_in,
                expira_em,
                criado_em,
                atualizado_em
            )

            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )

            ON CONFLICT (provedor)

            DO UPDATE SET
                access_token =
                    EXCLUDED.access_token,

                refresh_token =
                    EXCLUDED.refresh_token,

                expires_in =
                    EXCLUDED.expires_in,

                expira_em =
                    EXCLUDED.expira_em,

                atualizado_em =
                    CURRENT_TIMESTAMP
            """,
            (
                PROVEDOR,
                access_token,
                refresh_token,
                expires_in,
                expira_em,
            ),
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


def inicializar_tokens(
    access_token,
    refresh_token,
):
    """
    Usa as credenciais iniciais apenas quando a tabela
    ainda não possui tokens.

    Depois da primeira renovação, o Neon passa a ser
    a fonte principal dos tokens.
    """

    existente = buscar_tokens()

    if existente:
        return existente

    access_token = str(
        access_token
        or ""
    ).strip()

    refresh_token = str(
        refresh_token
        or ""
    ).strip()

    if (
        not access_token
        or not refresh_token
    ):
        return None

    salvar_tokens(
        access_token=
            access_token,

        refresh_token=
            refresh_token,

        expires_in=None,
    )

    return buscar_tokens()


def token_expirado(
    dados_tokens,
):
    if not dados_tokens:
        return True

    expira_em = (
        dados_tokens.get(
            "expira_em"
        )
    )

    if expira_em is None:
        return False

    if expira_em.tzinfo is None:
        expira_em = (
            expira_em.replace(
                tzinfo=timezone.utc
            )
        )

    return (
        datetime.now(
            timezone.utc
        )
        >= expira_em
    )
