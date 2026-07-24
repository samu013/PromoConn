from database.database import (
    conectar,
)

from services.pontuacao import (
    calcular_oportunidades,
)

from services.roteador_telegram import (
    descobrir_categoria_destino,
    buscar_destino_produto,
)

from telegram_bot.bot import (
    enviar_produto,
)


# =========================================================
# BUSCAR PRODUTO
# =========================================================

def buscar_produto(
    oportunidade_id
):
    produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    for produto in produtos:

        if (
            produto["id"]
            == oportunidade_id
        ):
            return produto

    return None


# =========================================================
# MESSAGE ID
# =========================================================

def extrair_message_id(
    resposta
):
    if not isinstance(
        resposta,
        dict
    ):
        return None

    resultado = resposta.get(
        "result",
        {}
    )

    message_id = resultado.get(
        "message_id"
    )

    if message_id is None:
        return None

    return str(
        message_id
    )


# =========================================================
# HISTÓRICO
# =========================================================

def mover_para_historico(
    produto,
    telegram_message_id=None,
    telegram_canal=None,
    telegram_chat_id=None,
):
    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute(
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
                telegram_canal,
                telegram_chat_id,
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
                produto["ml_id"],
                produto["tipo"],
                produto["nome"],
                produto["imagem"],
                produto["categoria"],
                produto["ranking"],
                produto["link_produto"],
                produto["link_afiliado"],
                produto["preco"],
                produto["preco_original"],
                produto["desconto"],
                telegram_message_id,
                telegram_canal,
                telegram_chat_id,
            )
        )

        # =================================================
        # REMOVE DA FILA ATIVA
        # =================================================

        cursor.execute(
            """
            DELETE FROM oportunidades

            WHERE id = %s
            """,
            (
                produto["id"],
            )
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


# =========================================================
# PUBLICAR PRODUTO
# =========================================================

def publicar_produto_por_id(
    oportunidade_id
):
    produto = buscar_produto(
        oportunidade_id
    )

    if produto is None:
        return {
            "sucesso": False,
            "erro":
                "Produto não encontrado.",
        }

    # =====================================================
    # VALIDA STATUS
    # =====================================================

    if (
        produto.get("status")
        != "pronto_publicar"
    ):
        return {
            "sucesso": False,
            "erro": (
                "Produto ainda não está "
                "pronto para publicar."
            ),
        }

    # =====================================================
    # VALIDA LINK
    # =====================================================

    if not produto.get(
        "link_afiliado"
    ):
        return {
            "sucesso": False,
            "erro": (
                "Produto sem link "
                "de afiliado."
            ),
        }

    # =====================================================
    # VALIDA PREÇO
    # =====================================================

    if produto.get(
        "preco"
    ) is None:
        return {
            "sucesso": False,
            "erro":
                "Produto sem preço.",
        }

    # =====================================================
    # DESCOBRE CATEGORIA PROMOCONN
    # =====================================================

    categoria_destino = (
        descobrir_categoria_destino(
            produto
        )
    )

    # =====================================================
    # BUSCA CANAL
    # =====================================================

    canal = (
        buscar_destino_produto(
            produto
        )
    )

    if canal is None:
        return {
            "sucesso": False,
            "erro": (
                "Nenhum canal do Telegram "
                "foi encontrado para "
                f"{categoria_destino}, "
                "e o grupo Geral também "
                "não está configurado."
            ),
        }

    chat_id = canal[
        "chat_id"
    ]

    nome_canal = canal[
        "nome"
    ]

    # =====================================================
    # LOG
    # =====================================================

    print()
    print("=" * 60)
    print("📤 PUBLICAÇÃO PROMOCONN")
    print("=" * 60)

    print(
        "Produto:",
        produto["nome"]
    )

    print(
        "Categoria original:",
        produto.get(
            "categoria"
        )
    )

    print(
        "Categoria destino:",
        categoria_destino
    )

    print(
        "Grupo:",
        nome_canal
    )

    # =====================================================
    # TELEGRAM
    # =====================================================

    try:

        resposta = enviar_produto(
            produto,
            chat_id=chat_id,
        )

    except Exception as erro:

        return {
            "sucesso": False,
            "erro": (
                "Erro ao enviar para "
                f"{nome_canal}: {erro}"
            ),
        }

    telegram_message_id = (
        extrair_message_id(
            resposta
        )
    )

    # =====================================================
    # HISTÓRICO
    # =====================================================

    try:

        mover_para_historico(
            produto=produto,

            telegram_message_id=
                telegram_message_id,

            telegram_canal=
                nome_canal,

            telegram_chat_id=
                str(chat_id),
        )

    except Exception as erro:

        return {
            "sucesso": False,

            "erro": (
                "A mensagem foi enviada "
                "ao Telegram, mas houve "
                "erro ao salvar no banco: "
                f"{erro}"
            ),
        }

    print(
        "✅ Publicado em:",
        nome_canal
    )

    return {
        "sucesso": True,

        "produto_id":
            produto["id"],

        "ml_id":
            produto["ml_id"],

        "nome":
            produto["nome"],

        "categoria_destino":
            categoria_destino,

        "telegram_canal":
            nome_canal,

        "telegram_chat_id":
            str(chat_id),

        "telegram_message_id":
            telegram_message_id,
    }


# =========================================================
# PRÓXIMO DA FILA
# =========================================================

def publicar_proxima_promocao():
    """
    Publica somente UMA promoção por ciclo.

    A prioridade continua sendo:
    maior pontuação primeiro.
    """

    produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    fila = [
        produto

        for produto in produtos

        if (
            produto.get("status")
            == "pronto_publicar"

            and produto.get(
                "link_afiliado"
            )

            and produto.get(
                "preco"
            ) is not None
        )
    ]

    if not fila:

        print(
            "📭 Nenhuma promoção "
            "pronta na fila."
        )

        return {
            "sucesso": False,

            "fila_vazia": True,

            "erro": (
                "Nenhuma promoção pronta "
                "para publicação."
            ),
        }

    # =====================================================
    # MAIOR SCORE PRIMEIRO
    # =====================================================

    fila.sort(
        key=lambda produto:
            produto.get(
                "pontuacao",
                0
            ),

        reverse=True,
    )

    produto = fila[0]

    print()
    print(
        "🚀 Próxima promoção:"
    )

    print(
        f"   {produto['nome']}"
    )

    print(
        "   Score:",
        produto["pontuacao"]
    )

    resultado = (
        publicar_produto_por_id(
            produto["id"]
        )
    )

    if resultado.get(
        "sucesso"
    ):

        print(
            "✅ Publicada com sucesso."
        )

    else:

        print(
            "❌ Falha:",
            resultado.get(
                "erro"
            ),
        )

    return resultado