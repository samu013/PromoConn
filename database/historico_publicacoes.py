from database.database import conectar
from database.oportunidades import normalizar_origem


def registrar_publicacao(
    ml_id,
    nome=None,
    imagem=None,
    link_afiliado=None,
    categoria=None,
    chat_id=None,
    mensagem_id=None,
    origem="mercadolivre",
):
    origem = normalizar_origem(origem)

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO historico_publicacoes (
                ml_id,
                origem,
                nome,
                imagem,
                link_afiliado,
                categoria,
                chat_id,
                mensagem_id,
                publicado_em
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP
            )
            """,
            (
                str(ml_id),
                origem,
                nome,
                imagem,
                link_afiliado,
                categoria,
                str(chat_id) if chat_id is not None else None,
                str(mensagem_id) if mensagem_id is not None else None,
            ),
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()
