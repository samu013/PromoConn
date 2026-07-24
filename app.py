import math

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
)

from database.database import (
    conectar,
    criar_tabelas,
)

from services.pontuacao import (
    calcular_oportunidades,
)

from services.publicador import (
    publicar_produto_por_id,
)


app = Flask(__name__)

criar_tabelas()

ITENS_POR_PAGINA = 20


# =========================================================
# AUXILIARES
# =========================================================

def converter_preco(texto):
    if not texto:
        return None

    texto = (
        texto
        .replace("R$", "")
        .strip()
    )

    # Formato brasileiro:
    # 1.299,90 -> 1299.90

    if "," in texto:
        texto = (
            texto
            .replace(".", "")
            .replace(",", ".")
        )

    return float(texto)


def filtrar_produtos(
    produtos,
    busca,
    categoria,
    ordem
):
    resultado = list(
        produtos
    )

    # =====================================================
    # PESQUISA
    # =====================================================

    if busca:
        termo = busca.lower()

        resultado = [
            produto
            for produto in resultado
            if termo
            in produto["nome"].lower()
        ]

    # =====================================================
    # CATEGORIA
    # =====================================================

    if categoria:
        resultado = [
            produto
            for produto in resultado
            if produto["categoria"]
            == categoria
        ]

    # =====================================================
    # ORDENAÇÃO
    # =====================================================

    if ordem == "ranking":
        resultado.sort(
            key=lambda produto: (
                produto["ranking"]
                if produto["ranking"]
                is not None
                else 999
            )
        )

    elif ordem == "nome":
        resultado.sort(
            key=lambda produto:
                produto["nome"].lower()
        )

    else:
        resultado.sort(
            key=lambda produto:
                produto["pontuacao"],
            reverse=True
        )

    return resultado


# =========================================================
# PAINEL
# =========================================================

@app.route("/")
def painel():
    todos_produtos = (
        calcular_oportunidades(
            limite=None
        )
    )

    fila_publicacao = [
        produto
        for produto in todos_produtos
        if produto["status"]
        == "pronto_publicar"
    ]

    oportunidades_ativas = [
        produto
        for produto in todos_produtos
        if produto["status"]
        == "aguardando_link"
    ]

    fila_publicacao.sort(
        key=lambda produto:
            produto["pontuacao"],
        reverse=True
    )

    busca = request.args.get(
        "busca",
        ""
    ).strip()

    categoria = request.args.get(
        "categoria",
        ""
    ).strip()

    ordem = request.args.get(
        "ordem",
        "score"
    ).strip()

    try:
        pagina = int(
            request.args.get(
                "pagina",
                1
            )
        )

    except ValueError:
        pagina = 1

    pagina = max(
        pagina,
        1
    )

    # =====================================================
    # MÉTRICAS
    # =====================================================

    total_oportunidades = len(
        oportunidades_ativas
    )

    total_aguardando = len(
        oportunidades_ativas
    )

    total_prontos = len(
        fila_publicacao
    )

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM historico_publicacoes
        """)

        resultado = cursor.fetchone()

        total_publicados = (
            resultado["total"]
        )

    finally:
        cursor.close()
        conexao.close()

    # =====================================================
    # CATEGORIAS
    # =====================================================

    categorias = sorted(
        {
            produto["categoria"]
            for produto
            in oportunidades_ativas
            if produto["categoria"]
        }
    )

    # =====================================================
    # FILTROS
    # =====================================================

    produtos_filtrados = (
        filtrar_produtos(
            oportunidades_ativas,
            busca,
            categoria,
            ordem,
        )
    )

    total_filtrado = len(
        produtos_filtrados
    )

    # =====================================================
    # PAGINAÇÃO
    # =====================================================

    total_paginas = max(
        1,
        math.ceil(
            total_filtrado
            / ITENS_POR_PAGINA
        )
    )

    if pagina > total_paginas:
        pagina = total_paginas

    inicio = (
        (pagina - 1)
        * ITENS_POR_PAGINA
    )

    fim = (
        inicio
        + ITENS_POR_PAGINA
    )

    produtos = (
        produtos_filtrados[
            inicio:fim
        ]
    )

    return render_template(
        "painel.html",

        produtos=produtos,

        fila_publicacao=
            fila_publicacao,

        categorias=categorias,

        busca=busca,

        categoria_selecionada=
            categoria,

        ordem_selecionada=
            ordem,

        pagina=pagina,

        total_paginas=
            total_paginas,

        total_filtrado=
            total_filtrado,

        total_oportunidades=
            total_oportunidades,

        total_aguardando=
            total_aguardando,

        total_prontos=
            total_prontos,

        total_publicados=
            total_publicados,
    )


# =========================================================
# SALVAR OFERTA
# =========================================================

@app.route(
    "/oportunidade/"
    "<int:oportunidade_id>/oferta",
    methods=["POST"]
)
def salvar_oferta(
    oportunidade_id
):
    link_produto = (
        request.form.get(
            "link_produto",
            ""
        ).strip()
    )

    link_afiliado = (
        request.form.get(
            "link_afiliado",
            ""
        ).strip()
    )

    preco_texto = (
        request.form.get(
            "preco",
            ""
        ).strip()
    )

    preco_original_texto = (
        request.form.get(
            "preco_original",
            ""
        ).strip()
    )

    # =====================================================
    # LINK DO PRODUTO
    # =====================================================

    if not link_produto.startswith(
        (
            "https://www.mercadolivre.com.br/",
            "https://produto.mercadolivre.com.br/",
        )
    ):
        return (
            "Link do produto inválido.",
            400
        )

    # =====================================================
    # LINK AFILIADO
    # =====================================================

    if not link_afiliado.startswith(
        (
            "https://meli.la/",
            "https://www.mercadolivre.com.br/social/",
        )
    ):
        return (
            "Link de afiliado inválido.",
            400
        )

    # =====================================================
    # PREÇO
    # =====================================================

    try:
        preco = converter_preco(
            preco_texto
        )

    except ValueError:
        return (
            "Preço atual inválido.",
            400
        )

    if (
        preco is None
        or preco <= 0
    ):
        return (
            "Preço atual inválido.",
            400
        )

    # =====================================================
    # PREÇO ORIGINAL
    # =====================================================

    preco_original = None

    if preco_original_texto:
        try:
            preco_original = (
                converter_preco(
                    preco_original_texto
                )
            )

        except ValueError:
            return (
                "Preço anterior inválido.",
                400
            )

        if preco_original <= 0:
            return (
                "Preço anterior inválido.",
                400
            )

    # =====================================================
    # DESCONTO
    # =====================================================

    desconto = None

    if (
        preco_original is not None
        and preco_original > preco
    ):
        desconto = round(
            (
                (
                    preco_original
                    - preco
                )
                / preco_original
            )
            * 100,
            2
        )

    # =====================================================
    # BANCO
    # =====================================================

    conexao = conectar()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE oportunidades

            SET
                link_produto = %s,
                preco = %s,
                preco_original = %s,
                desconto = %s,
                link_afiliado = %s,
                status = 'pronto_publicar',
                atualizado_em =
                    CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                link_produto,
                preco,
                preco_original,
                desconto,
                link_afiliado,
                oportunidade_id,
            )
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()

    return redirect(
        url_for("painel")
    )


# =========================================================
# PUBLICAÇÃO MANUAL
# =========================================================

@app.route(
    "/oportunidade/"
    "<int:oportunidade_id>/telegram",
    methods=["POST"]
)
def publicar_telegram(
    oportunidade_id
):
    resultado = (
        publicar_produto_por_id(
            oportunidade_id
        )
    )

    if not resultado.get(
        "sucesso"
    ):
        return (
            resultado.get(
                "erro",
                "Não foi possível publicar."
            ),
            400
        )

    return redirect(
        url_for("painel")
    )


# =========================================================
# INICIALIZAÇÃO
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )