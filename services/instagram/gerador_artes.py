from pathlib import Path
from urllib.parse import quote
import base64
import html

from jinja2 import Template

from .renderer import renderizar_html


# ============================================================
# CONFIGURAÇÃO
# ============================================================

LARGURA = 1080
ALTURA = 1350

BASE_DIR = Path(__file__).resolve().parents[2]

PASTA_IMAGENS = (
    BASE_DIR
    / "static"
    / "img"
)

PASTA_INSTAGRAM = (
    PASTA_IMAGENS
    / "instagram"
)

PASTA_SAIDA = (
    PASTA_INSTAGRAM
    / "geradas"
)

PASTA_TEMPLATES = (
    Path(__file__).resolve().parent
    / "templates"
)

TEMPLATE_PATH = (
    PASTA_TEMPLATES
    / "oferta.html"
)

LOGO_PATH = (
    PASTA_INSTAGRAM
    / "logo.png"
)


# ============================================================
# UTILITÁRIOS
# ============================================================

def escapar(valor):
    """
    Escapa texto para utilização segura no HTML.
    """

    if valor is None:
        return ""

    return html.escape(
        str(valor),
        quote=True,
    )


def formatar_preco(valor):
    """
    Normaliza preços para o formato brasileiro.
    """

    if valor is None:
        return "0,00"

    texto = str(valor).strip()

    if not texto:
        return "0,00"

    texto = (
        texto
        .replace("R$", "")
        .replace(" ", "")
    )

    # Já está no formato brasileiro.
    if "," in texto:
        try:
            numero = float(
                texto.replace(".", "").replace(",", ".")
            )

            return f"{numero:,.2f}".replace(
                ",",
                "X",
            ).replace(
                ".",
                ",",
            ).replace(
                "X",
                ".",
            )

        except ValueError:
            return texto

    try:
        numero = float(texto)

        return f"{numero:,.2f}".replace(
            ",",
            "X",
        ).replace(
            ".",
            ",",
        ).replace(
            "X",
            ".",
        )

    except ValueError:
        return texto


def formatar_desconto(valor):
    """
    Formata o desconto evitando casas decimais
    desnecessárias.
    """

    if valor is None:
        return "0"

    try:
        numero = float(valor)

        if numero.is_integer():
            return str(int(numero))

        return f"{numero:.1f}".replace(
            ".",
            ",",
        )

    except (ValueError, TypeError):
        return str(valor)


# ============================================================
# IMAGENS
# ============================================================

def imagem_para_data_uri(caminho):
    """
    Converte uma imagem local para Data URI.

    Isso permite que o Chromium carregue imagens
    locais durante a geração da arte.
    """

    caminho = Path(caminho)

    if not caminho.exists():
        return None

    extensao = caminho.suffix.lower()

    tipos = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    mime = tipos.get(
        extensao,
        "application/octet-stream",
    )

    dados = caminho.read_bytes()

    encoded = base64.b64encode(
        dados
    ).decode("ascii")

    return (
        f"data:{mime};base64,{encoded}"
    )


def preparar_imagem(imagem):
    """
    Aceita:

    - URL HTTP/HTTPS
    - caminho local
    - Path
    """

    if not imagem:
        return None

    texto = str(imagem).strip()

    if not texto:
        return None

    # URL remota.
    if texto.startswith("http://"):
        return texto

    if texto.startswith("https://"):
        return texto

    # Arquivo local.
    caminho = Path(texto)

    if caminho.exists():
        return imagem_para_data_uri(
            caminho
        )

    # Caminho relativo ao projeto.
    caminho_projeto = (
        BASE_DIR
        / texto.lstrip("/")
        .replace("/", "\\")
    )

    if caminho_projeto.exists():
        return imagem_para_data_uri(
            caminho_projeto
        )

    return None


def preparar_logo():
    """
    Prepara a logo do PromoConn.
    """

    if not LOGO_PATH.exists():
        return None

    return imagem_para_data_uri(
        LOGO_PATH
    )


# ============================================================
# TEMPLATE
# ============================================================

def carregar_template():
    """
    Carrega o template HTML.
    """

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template não encontrado: "
            f"{TEMPLATE_PATH}"
        )

    return Template(
        TEMPLATE_PATH.read_text(
            encoding="utf-8"
        )
    )


# ============================================================
# GERAÇÃO
# ============================================================

def gerar_arte(
    produto,
    caminho_saida=None,
):
    """
    Gera uma arte individual 1080x1350.

    Espera um dicionário contendo,
    preferencialmente:

        titulo
        categoria
        ranking
        preco_antigo
        preco_atual
        desconto
        imagem
    """

    if not produto:
        raise ValueError(
            "Produto não informado."
        )

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    ranking = produto.get(
        "ranking",
        1,
    )

    titulo = (
        produto.get("titulo")
        or produto.get("nome")
        or "Oferta especial"
    )

    categoria = (
        produto.get("categoria")
        or "Oferta"
    )

    preco_antigo = (
        produto.get("preco_antigo")
        or produto.get("preco_original")
        or produto.get("preco")
        or 0
    )

    preco_atual = (
        produto.get("preco_atual")
        or produto.get("preco")
        or 0
    )

    desconto = (
        produto.get("desconto")
        or 0
    )

    imagem = (
        produto.get("imagem")
        or produto.get("imagem_url")
        or produto.get("thumbnail")
    )

    imagem = preparar_imagem(
        imagem
    )

    logo = preparar_logo()

    dados = {
        "ranking": escapar(ranking),
        "titulo": escapar(titulo),
        "categoria": escapar(categoria),
        "preco_antigo": formatar_preco(
            preco_antigo
        ),
        "preco_atual": formatar_preco(
            preco_atual
        ),
        "desconto": formatar_desconto(
            desconto
        ),
        "imagem": imagem,
        "logo": logo,
    }

    template = carregar_template()

    html_renderizado = template.render(
        **dados
    )

    if caminho_saida is None:

        caminho_saida = (
            PASTA_SAIDA
            / f"arte_{ranking}.png"
        )

    caminho_saida = Path(
        caminho_saida
    )

    return renderizar_html(
        html_renderizado,
        caminho_saida,
    )


# ============================================================
# TOP 5
# ============================================================

def gerar_artes_top(produtos):
    """
    Gera até 5 artes.

    Retorna uma lista com os caminhos
    das imagens geradas.
    """

    if not produtos:
        print(
            "⚠️ Nenhum produto recebido "
            "para geração das artes."
        )

        return []

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    artes = []

    print()
    print("=" * 60)
    print("📸 GERANDO ARTES DO INSTAGRAM")
    print("=" * 60)

    for posicao, produto in enumerate(
        produtos[:5],
        start=1,
    ):

        try:

            produto = dict(produto)

            produto["ranking"] = (
                produto.get("ranking")
                or posicao
            )

            caminho = gerar_arte(
                produto
            )

            artes.append(
                caminho
            )

            print(
                f"✅ Arte "
                f"{posicao}/5 criada: "
                f"{caminho}"
            )

        except Exception as erro:

            print(
                f"❌ Erro ao gerar "
                f"arte {posicao}/5: "
                f"{erro}"
            )

    print(
        f"📸 Total de artes geradas: "
        f"{len(artes)}"
    )

    return artes


# ============================================================
# LISTAGEM
# ============================================================

def listar_artes_do_dia():
    """
    Lista as artes disponíveis para
    a página /instagram.
    """

    if not PASTA_SAIDA.exists():
        return []

    arquivos = sorted(
        PASTA_SAIDA.glob("*.png"),
        key=lambda arquivo:
            arquivo.stat().st_mtime,
        reverse=True,
    )

    artes = []

    for posicao, arquivo in enumerate(
        arquivos[:5],
        start=1,
    ):

        try:

            caminho_relativo = (
                arquivo.relative_to(
                    BASE_DIR
                    / "static"
                )
            )

            artes.append(
                {
                    "arquivo":
                        caminho_relativo.as_posix(),

                    "posicao":
                        posicao,
                }
            )

        except ValueError:

            print(
                "⚠️ Não foi possível "
                "montar o caminho da arte: "
                f"{arquivo}"
            )

    return artes