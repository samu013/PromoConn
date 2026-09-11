from pathlib import Path
import base64
import mimetypes
import os
import re

import cloudinary
import cloudinary.api
import cloudinary.uploader
import requests
from dotenv import load_dotenv
from jinja2 import Template


# =========================================================
# DIRETÓRIOS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PASTA_SAIDA = (
    BASE_DIR
    / "static"
    / "img"
    / "instagram"
    / "geradas"
)

TEMPLATE_PATH = (
    BASE_DIR
    / "services"
    / "instagram"
    / "templates"
    / "oferta.html"
)

LOGO_PATH = (
    BASE_DIR
    / "static"
    / "img"
    / "instagram"
    / "logo.png"
)


# =========================================================
# AMBIENTE
# =========================================================

load_dotenv()

CLOUDINARY_URL = os.getenv(
    "CLOUDINARY_URL"
)

if CLOUDINARY_URL:
    cloudinary.config(
        cloudinary_url=CLOUDINARY_URL
    )


# =========================================================
# CONFIGURAÇÃO CLOUDINARY
# =========================================================

PASTA_CLOUDINARY = (
    "promoconn/instagram"
)


def verificar_cloudinary():

    config = cloudinary.config()

    if not config.cloud_name:
        raise RuntimeError(
            "Cloudinary não está configurado. "
            "Verifique a variável CLOUDINARY_URL."
        )

    print(
        f"☁️ Cloudinary configurado: "
        f"{config.cloud_name}"
    )

    return True


# =========================================================
# CONVERSÃO DE NÚMEROS
# =========================================================

def converter_numero(
    valor,
    padrao=0,
):
    """
    Converte valores para float.

    Exemplos:

        1234.56
        "1234.56"
        "1.234,56"
        "R$ 1.234,56"
    """

    if valor is None:
        return padrao

    if isinstance(
        valor,
        (int, float),
    ):
        return float(valor)

    texto = str(valor).strip()

    if not texto:
        return padrao

    texto = re.sub(
        r"[^\d,.\-]",
        "",
        texto,
    )

    if not texto:
        return padrao

    if (
        "," in texto
        and "." in texto
    ):
        texto = texto.replace(
            ".",
            "",
        )

        texto = texto.replace(
            ",",
            ".",
        )

    elif "," in texto:

        texto = texto.replace(
            ",",
            ".",
        )

    try:
        return float(texto)

    except (
        ValueError,
        TypeError,
    ):
        return padrao


# =========================================================
# PREPARAR IMAGEM
# =========================================================

def preparar_imagem(
    origem,
):
    """
    Aceita:

    - URL HTTP/HTTPS
    - caminho local
    - data URI
    """

    if not origem:
        return None

    origem = str(
        origem
    ).strip()

    # -----------------------------------------------------
    # DATA URI
    # -----------------------------------------------------

    if origem.startswith(
        "data:image/"
    ):
        return origem

    # -----------------------------------------------------
    # URL
    # -----------------------------------------------------

    if (
        origem.startswith(
            "http://"
        )
        or origem.startswith(
            "https://"
        )
    ):

        resposta = requests.get(
            origem,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        )

        resposta.raise_for_status()

        conteudo = resposta.content

        content_type = (
            resposta.headers.get(
                "Content-Type",
                "image/jpeg",
            )
            .split(";")[0]
        )

        if not content_type.startswith(
            "image/"
        ):
            content_type = "image/jpeg"

        base64_data = (
            base64.b64encode(
                conteudo
            ).decode("utf-8")
        )

        return (
            f"data:{content_type};base64,"
            f"{base64_data}"
        )

    # -----------------------------------------------------
    # ARQUIVO LOCAL
    # -----------------------------------------------------

    caminho = Path(
        origem
    )

    if not caminho.is_absolute():

        caminho = (
            BASE_DIR
            / caminho
        )

    if not caminho.exists():

        raise FileNotFoundError(
            "Imagem não encontrada: "
            f"{caminho}"
        )

    mime_type, _ = (
        mimetypes.guess_type(
            caminho.name
        )
    )

    if not mime_type:
        mime_type = "image/png"

    conteudo = (
        caminho.read_bytes()
    )

    base64_data = (
        base64.b64encode(
            conteudo
        ).decode("utf-8")
    )

    return (
        f"data:{mime_type};base64,"
        f"{base64_data}"
    )


# =========================================================
# LOGO
# =========================================================

def preparar_logo():

    if not LOGO_PATH.exists():

        print(
            "⚠️ Logo não encontrado: "
            f"{LOGO_PATH}"
        )

        return None

    return preparar_imagem(
        LOGO_PATH
    )


# =========================================================
# TEMPLATE
# =========================================================

def carregar_template():

    if not TEMPLATE_PATH.exists():

        raise FileNotFoundError(
            "Template do Instagram não encontrado: "
            f"{TEMPLATE_PATH}"
        )

    return Template(
        TEMPLATE_PATH.read_text(
            encoding="utf-8"
        )
    )


# =========================================================
# LIMPAR ARTES LOCAIS
# =========================================================

def limpar_artes_anteriores():

    if not PASTA_SAIDA.exists():
        return

    for arquivo in (
        PASTA_SAIDA.glob("*.png")
    ):

        try:

            arquivo.unlink()

            print(
                f"🗑️ Arte local removida: "
                f"{arquivo.name}"
            )

        except OSError as erro:

            print(
                f"⚠️ Não foi possível remover "
                f"{arquivo.name}: {erro}"
            )


# =========================================================
# CLOUDINARY - UPLOAD
# =========================================================

def enviar_para_cloudinary(
    caminho_arquivo,
    posicao,
):
    """
    Envia a arte para o Cloudinary.

    Os nomes serão sempre:

        promoconn/instagram/top_1
        promoconn/instagram/top_2
        ...
        promoconn/instagram/top_5
    """

    verificar_cloudinary()

    caminho_arquivo = Path(
        caminho_arquivo
    )

    if not caminho_arquivo.exists():

        raise FileNotFoundError(
            "Arquivo não encontrado para "
            f"upload: {caminho_arquivo}"
        )

    public_id = (
        f"{PASTA_CLOUDINARY}/"
        f"top_{posicao}"
    )

    print(
        f"☁️ Enviando "
        f"{caminho_arquivo.name} "
        "para Cloudinary..."
    )

    resultado = (
        cloudinary.uploader.upload(
            str(caminho_arquivo),

            public_id=public_id,

            resource_type="image",

            overwrite=True,

            invalidate=True,
        )
    )

    url = (
        resultado.get(
            "secure_url"
        )
    )

    if not url:

        raise RuntimeError(
            "Cloudinary não retornou "
            "secure_url."
        )

    print(
        f"✅ Upload concluído:"
    )

    print(
        f"   {url}"
    )

    return {
        "url": url,

        "public_id": public_id,

        "asset_id": resultado.get(
            "asset_id"
        ),

        "version": resultado.get(
            "version"
        ),
    }


# =========================================================
# CLOUDINARY - LISTAR ARTES
# =========================================================

def listar_artes_cloudinary():

    verificar_cloudinary()

    try:

        resultado = (
            cloudinary.api.resources(
                type="upload",
                resource_type="image",
                prefix=PASTA_CLOUDINARY,
                max_results=20,
            )
        )

    except Exception as erro:

        print(
            "⚠️ Não foi possível listar "
            "as artes no Cloudinary:"
        )

        print(erro)

        return []

    recursos = (
        resultado.get(
            "resources",
            [],
        )
    )

    artes = []

    for recurso in recursos:

        public_id = (
            recurso.get(
                "public_id",
                "",
            )
        )

        nome = (
            public_id.split(
                "/"
            )[-1]
        )

        match = re.match(
            r"top_(\d+)$",
            nome,
        )

        if not match:
            continue

        posicao = int(
            match.group(1)
        )

        url = (
            recurso.get(
                "secure_url"
            )
        )

        if not url:
            continue

        artes.append(
            {
                "arquivo": (
                    f"img/instagram/"
                    f"geradas/"
                    f"top_{posicao}.png"
                ),

                "arquivo_local": (
                    str(
                        PASTA_SAIDA
                        / f"top_{posicao}.png"
                    )
                ),

                "posicao": posicao,

                "url": url,

                "public_id": public_id,

                "cloudinary": True,
            }
        )

    artes.sort(
        key=lambda arte:
            arte["posicao"]
    )

    return artes[:5]


# =========================================================
# GERAR ARTE INDIVIDUAL
# =========================================================

def gerar_arte(
    produto,
    caminho_saida,
):
    """
    Gera a arte localmente e envia para Cloudinary.

    Retorna informações da arte.
    """

    # Mantém o renderizador que já existe
    # no projeto PromoConn.
    from services.instagram.renderizador import (
        renderizar_html,
    )

    template = (
        carregar_template()
    )

    # -----------------------------------------------------
    # PREÇO ATUAL
    # -----------------------------------------------------

    preco_atual = (
        converter_numero(
            produto.get(
                "preco_atual"
            )
            or produto.get(
                "preco"
            ),
            0,
        )
    )

    # -----------------------------------------------------
    # PREÇO ANTIGO
    # -----------------------------------------------------

    preco_antigo = (
        converter_numero(
            produto.get(
                "preco_antigo"
            )
            or produto.get(
                "preco_original"
            ),
            0,
        )
    )

    # -----------------------------------------------------
    # DESCONTO
    # -----------------------------------------------------

    desconto = (
        converter_numero(
            produto.get(
                "desconto"
            )
            or produto.get(
                "desconto_instagram"
            ),
            0,
        )
    )

    # Calcula automaticamente
    # somente quando existe um
    # preço antigo REALMENTE maior.

    if (
        desconto <= 0
        and preco_antigo > preco_atual
        and preco_atual > 0
    ):

        desconto = (
            (
                preco_antigo
                - preco_atual
            )
            / preco_antigo
        ) * 100

    # -----------------------------------------------------
    # DESCONTO REAL
    # -----------------------------------------------------

    tem_desconto = (
        preco_atual > 0
        and preco_antigo > preco_atual
        and desconto > 0
    )

    if not tem_desconto:

        preco_antigo = 0

        desconto = 0

    # -----------------------------------------------------
    # IMAGEM
    # -----------------------------------------------------

    imagem = preparar_imagem(
        produto.get(
            "imagem"
        )
        or produto.get(
            "imagem_url"
        )
        or produto.get(
            "thumbnail"
        )
    )

    if not imagem:

        raise ValueError(
            "Produto não possui "
            "imagem válida."
        )

    # -----------------------------------------------------
    # LOGO
    # -----------------------------------------------------

    logo = (
        preparar_logo()
    )

    # -----------------------------------------------------
    # CONTEXTO
    # -----------------------------------------------------

    contexto = {

        "produto": produto,

        "nome": (
            produto.get(
                "nome"
            )
            or produto.get(
                "titulo"
            )
            or "Produto"
        ),

        "categoria": (
            produto.get(
                "categoria"
            )
            or "Oferta"
        ),

        "imagem": imagem,

        "logo": logo,

        "preco_atual": preco_atual,

        "preco_antigo": preco_antigo,

        "desconto": desconto,

        "tem_desconto":
            tem_desconto,

        "ranking": produto.get(
            "ranking",
            1,
        ),

        "link_produto": (
            produto.get(
                "link_produto"
            )
            or produto.get(
                "link"
            )
            or ""
        ),

        "link_afiliado": (
            produto.get(
                "link_afiliado"
            )
            or produto.get(
                "link"
            )
            or ""
        ),
    }

    # -----------------------------------------------------
    # RENDERIZA HTML
    # -----------------------------------------------------

    html = (
        template.render(
            **contexto
        )
    )

    # -----------------------------------------------------
    # CRIA DIRETÓRIO
    # -----------------------------------------------------

    caminho_saida = Path(
        caminho_saida
    )

    caminho_saida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"🎨 Gerando arte "
        f"{caminho_saida.name}..."
    )

    # -----------------------------------------------------
    # HTML → PNG
    # -----------------------------------------------------

    renderizar_html(
        html,
        caminho_saida,
    )

    if not caminho_saida.exists():

        raise RuntimeError(
            "O renderizador não criou "
            f"a imagem: {caminho_saida}"
        )

    print(
        f"✅ PNG criado: "
        f"{caminho_saida}"
    )

    # -----------------------------------------------------
    # CLOUDINARY
    # -----------------------------------------------------

    resultado_cloudinary = (
        enviar_para_cloudinary(
            caminho_saida,
            posicao=produto.get(
                "ranking",
                1,
            ),
        )
    )

    # -----------------------------------------------------
    # RETORNO
    # -----------------------------------------------------

    return {

        "arquivo_local":
            caminho_saida,

        "url":
            resultado_cloudinary[
                "url"
            ],

        "public_id":
            resultado_cloudinary[
                "public_id"
            ],

        "asset_id":
            resultado_cloudinary[
                "asset_id"
            ],

        "version":
            resultado_cloudinary[
                "version"
            ],
    }


# =========================================================
# GERAR TOP 5
# =========================================================

def gerar_artes_top(
    produtos,
):

    if not produtos:

        print(
            "⚠️ Nenhum produto recebido."
        )

        return []

    verificar_cloudinary()

    # -----------------------------------------------------
    # ARTES LOCAIS
    # -----------------------------------------------------

    limpar_artes_anteriores()

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    artes = []

    # -----------------------------------------------------
    # TOP 5
    # -----------------------------------------------------

    for posicao, produto in enumerate(
        produtos[:5],
        start=1,
    ):

        produto_arte = dict(
            produto
        )

        produto_arte[
            "ranking"
        ] = posicao

        caminho_saida = (
            PASTA_SAIDA
            / f"top_{posicao}.png"
        )

        print()

        print(
            "========================================"
        )

        print(
            f"📸 GERANDO ARTE "
            f"{posicao}/5"
        )

        print(
            "========================================"
        )

        try:

            resultado = (
                gerar_arte(
                    produto_arte,
                    caminho_saida,
                )
            )

            arte = {

                "posicao":
                    posicao,

                "arquivo": (
                    "img/instagram/"
                    "geradas/"
                    f"top_{posicao}.png"
                ),

                "arquivo_local":
                    str(
                        resultado[
                            "arquivo_local"
                        ]
                    ),

                "url":
                    resultado[
                        "url"
                    ],

                "public_id":
                    resultado[
                        "public_id"
                    ],

                "cloudinary":
                    True,

                "produto":
                    produto_arte,
            }

            artes.append(
                arte
            )

            print(
                f"✅ Arte {posicao} "
                "pronta!"
            )

        except Exception as erro:

            print(
                f"❌ Erro ao gerar "
                f"arte {posicao}:"
            )

            print(erro)

    print()

    print(
        "========================================"
    )

    print(
        f"📸 Total de artes geradas: "
        f"{len(artes)}"
    )

    print(
        "========================================"
    )

    return artes


# =========================================================
# LISTAR ARTES DO DIA
# =========================================================

def listar_artes_do_dia():

    # -----------------------------------------------------
    # PRIMEIRO: CLOUDINARY
    # -----------------------------------------------------

    try:

        artes = (
            listar_artes_cloudinary()
        )

        if artes:

            print(
                f"☁️ {len(artes)} arte(s) "
                "encontrada(s) no Cloudinary."
            )

            return artes

    except Exception as erro:

        print(
            "⚠️ Erro ao consultar "
            "Cloudinary:"
        )

        print(erro)

    # -----------------------------------------------------
    # FALLBACK LOCAL
    #
    # Útil durante desenvolvimento.
    # -----------------------------------------------------

    if not PASTA_SAIDA.exists():

        return []

    arquivos = sorted(
        PASTA_SAIDA.glob(
            "*.png"
        ),
        key=lambda arquivo:
            arquivo.stat().st_mtime,
        reverse=True,
    )

    artes = []

    for arquivo in arquivos[:5]:

        nome = arquivo.stem

        try:

            posicao = int(
                nome.split(
                    "_"
                )[-1]
            )

        except (
            ValueError,
            IndexError,
        ):

            posicao = 0

        artes.append(
            {
                "arquivo": (
                    "img/instagram/"
                    "geradas/"
                    + arquivo.name
                ),

                "arquivo_local":
                    str(arquivo),

                "posicao":
                    posicao,

                "url": None,

                "cloudinary":
                    False,
            }
        )

    return artes