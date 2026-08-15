import io
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageOps,
)


FUSO_BRASIL = ZoneInfo(
    "America/Sao_Paulo"
)

LARGURA = 1080
ALTURA = 1350

AZUL = "#06143D"
AZUL_CLARO = "#128BDD"
VERDE = "#73C82D"
VERDE_CLARO = "#91E64F"
AMARELO = "#FFC52B"
BRANCO = "#FFFFFF"
PRETO = "#111111"
CINZA = "#667085"

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

STATIC_ROOT = (
    PROJECT_ROOT
    / "static"
)

IMG_ROOT = (
    STATIC_ROOT
    / "img"
)

INSTAGRAM_IMG_ROOT = (
    IMG_ROOT
    / "instagram"
)

GERADAS_ROOT = (
    STATIC_ROOT
    / "instagram"
    / "geradas"
)

LOGO_PATH = (
    IMG_ROOT
    / "logo-promoconn.png"
)

MASCOTE_FEMININA = (
    INSTAGRAM_IMG_ROOT
    / "mascote_feminina.png"
)

MASCOTE_MASCULINO = (
    INSTAGRAM_IMG_ROOT
    / "mascote_masculino.png"
)


def _fonte(
    tamanho,
    bold=False,
):
    candidatos = []

    if bold:
        candidatos.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    else:
        candidatos.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ])

    for caminho in candidatos:
        if Path(caminho).exists():
            return ImageFont.truetype(
                caminho,
                tamanho,
            )

    return ImageFont.load_default()


def _moeda(
    valor
):
    if valor is None:
        return ""

    valor = float(
        valor
    )

    texto = (
        f"{valor:,.2f}"
        .replace(
            ",",
            "X",
        )
        .replace(
            ".",
            ",",
        )
        .replace(
            "X",
            ".",
        )
    )

    return (
        f"R${texto}"
    )


def _normalizar_nome_arquivo(
    texto
):
    texto = str(
        texto
        or "produto"
    )

    texto = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        texto,
    )

    texto = re.sub(
        r"_+",
        "_",
        texto,
    )

    return texto.strip(
        "_"
    )[:60] or "produto"


def _quebrar_texto(
    draw,
    texto,
    font,
    largura_maxima,
    max_linhas=3,
):
    palavras = (
        str(
            texto
            or ""
        )
        .upper()
        .split()
    )

    linhas = []
    atual = ""

    for palavra in palavras:
        teste = (
            f"{atual} {palavra}"
            .strip()
        )

        bbox = draw.textbbox(
            (0, 0),
            teste,
            font=font,
        )

        largura = (
            bbox[2]
            - bbox[0]
        )

        if (
            largura
            <= largura_maxima
        ):
            atual = teste
            continue

        if atual:
            linhas.append(
                atual
            )

        atual = palavra

        if (
            len(linhas)
            >= max_linhas - 1
        ):
            break

    if (
        atual
        and len(linhas)
        < max_linhas
    ):
        linhas.append(
            atual
        )

    return linhas[
        :max_linhas
    ]


def _baixar_imagem_produto(
    url
):
    resposta = requests.get(
        url,
        timeout=25,
        headers={
            "User-Agent":
                "Mozilla/5.0"
        },
    )

    resposta.raise_for_status()

    return Image.open(
        io.BytesIO(
            resposta.content
        )
    ).convert(
        "RGBA"
    )


def _desenhar_fundo():
    imagem = Image.new(
        "RGB",
        (
            LARGURA,
            ALTURA,
        ),
        AZUL,
    )

    draw = ImageDraw.Draw(
        imagem
    )

    # Circuitos decorativos
    circuitos = [
        (
            (70, 255),
            (160, 165),
            (515, 165),
            (660, 55),
        ),
        (
            (170, 1350),
            (170, 1110),
            (245, 1030),
        ),
        (
            (910, 1350),
            (910, 1005),
            (1020, 1005),
        ),
        (
            (940, 0),
            (940, 175),
        ),
    ]

    for pontos in circuitos:
        draw.line(
            pontos,
            fill=AZUL_CLARO,
            width=4,
        )

        x, y = pontos[-1]

        draw.ellipse(
            (
                x - 9,
                y - 9,
                x + 9,
                y + 9,
            ),
            fill=AZUL_CLARO,
        )

    # Cabeçalho
    draw.rounded_rectangle(
        (
            -55,
            -40,
            745,
            225,
        ),
        radius=75,
        fill=BRANCO,
    )

    draw.polygon(
        [
            (675, 0),
            (755, 0),
            (615, 225),
            (535, 225),
        ],
        fill=VERDE,
    )

    # Faixa amarela
    draw.rounded_rectangle(
        (
            -70,
            250,
            770,
            325,
        ),
        radius=55,
        fill=AMARELO,
    )

    # Card principal
    draw.rounded_rectangle(
        (
            -45,
            300,
            850,
            1085,
        ),
        radius=58,
        fill=BRANCO,
        outline=PRETO,
        width=8,
    )

    # Rodapé
    draw.polygon(
        [
            (255, 1140),
            (LARGURA, 1140),
            (LARGURA, ALTURA),
            (155, ALTURA),
        ],
        fill=BRANCO,
    )

    draw.line(
        (
            165,
            ALTURA,
            310,
            1140,
        ),
        fill=VERDE,
        width=30,
    )

    return imagem


def _colar_logo(
    imagem
):
    if not LOGO_PATH.exists():
        return

    logo = Image.open(
        LOGO_PATH
    ).convert(
        "RGBA"
    )

    logo.thumbnail(
        (
            560,
            165,
        )
    )

    imagem.paste(
        logo,
        (
            35,
            24,
        ),
        logo,
    )


def _colar_mascotes(
    imagem
):
    if MASCOTE_FEMININA.exists():
        feminina = Image.open(
            MASCOTE_FEMININA
        ).convert(
            "RGBA"
        )

        feminina.thumbnail(
            (
                235,
                305,
            )
        )

        imagem.paste(
            feminina,
            (
                10,
                745,
            ),
            feminina,
        )

    if MASCOTE_MASCULINO.exists():
        masculino = Image.open(
            MASCOTE_MASCULINO
        ).convert(
            "RGBA"
        )

        masculino.thumbnail(
            (
                245,
                300,
            )
        )

        imagem.paste(
            masculino,
            (
                555,
                745,
            ),
            masculino,
        )


def _desenhar_produto(
    imagem,
    url_imagem,
):
    draw = ImageDraw.Draw(
        imagem
    )

    externo = (
        655,
        300,
        1110,
        765,
    )

    interno = (
        682,
        327,
        1083,
        738,
    )

    draw.ellipse(
        externo,
        fill=AMARELO,
    )

    draw.ellipse(
        interno,
        fill=BRANCO,
        outline=PRETO,
        width=7,
    )

    produto = (
        _baixar_imagem_produto(
            url_imagem
        )
    )

    produto = ImageOps.contain(
        produto,
        (
            330,
            330,
        ),
    )

    # Fundo branco para imagens com transparência irregular.
    canvas = Image.new(
        "RGBA",
        produto.size,
        (
            255,
            255,
            255,
            0,
        ),
    )

    canvas.alpha_composite(
        produto
    )

    x = (
        882
        - canvas.width // 2
    )

    y = (
        530
        - canvas.height // 2
    )

    imagem.paste(
        canvas,
        (
            x,
            y,
        ),
        canvas,
    )


def _desenhar_selo_desconto(
    draw,
    desconto
):
    if desconto <= 0:
        return

    draw.ellipse(
        (
            320,
            690,
            505,
            870,
        ),
        fill=VERDE_CLARO,
        outline=VERDE,
        width=5,
    )

    draw.text(
        (
            412,
            780,
        ),
        f"{desconto:.0f}% OFF",
        anchor="mm",
        font=_fonte(
            34,
            bold=True,
        ),
        fill=BRANCO,
    )


def _desenhar_bullets(
    draw,
    produto,
    inicio_y,
):
    categoria = (
        produto.get(
            "categoria"
        )
        or "Geral"
    )

    ranking = (
        produto.get(
            "ranking"
        )
    )

    bullets = [
        "Selecionada entre as melhores do dia",
        f"Categoria: {categoria}",
    ]

    if ranking is not None:
        bullets.append(
            f"Ranking Mercado Livre: #{ranking}"
        )

    else:
        bullets.append(
            "Link disponível no grupo"
        )

    fonte_texto = _fonte(
        28,
        bold=False,
    )

    fonte_check = _fonte(
        32,
        bold=True,
    )

    y = inicio_y

    for texto in bullets:
        draw.text(
            (
                56,
                y,
            ),
            "✓",
            font=fonte_check,
            fill="#08B828",
        )

        linhas = _quebrar_texto(
            draw,
            texto,
            fonte_texto,
            515,
            max_linhas=2,
        )

        texto_y = y

        for linha in linhas:
            draw.text(
                (
                    93,
                    texto_y,
                ),
                linha.title(),
                font=fonte_texto,
                fill=AZUL,
            )

            texto_y += 35

        y = max(
            y + 52,
            texto_y + 8,
        )


def gerar_arte_produto(
    produto,
    destino,
    posicao,
):
    imagem = (
        _desenhar_fundo()
    )

    _colar_logo(
        imagem
    )

    _colar_mascotes(
        imagem
    )

    draw = ImageDraw.Draw(
        imagem
    )

    # TOP #
    draw.rounded_rectangle(
        (
            55,
            323,
            180,
            368,
        ),
        radius=22,
        fill=AZUL_CLARO,
    )

    draw.text(
        (
            117,
            345,
        ),
        f"TOP {posicao}",
        anchor="mm",
        font=_fonte(
            24,
            bold=True,
        ),
        fill=BRANCO,
    )

    # Título
    fonte_titulo = _fonte(
        47,
        bold=True,
    )

    linhas = _quebrar_texto(
        draw,
        produto.get(
            "nome"
        ),
        fonte_titulo,
        575,
        max_linhas=3,
    )

    y = 388

    for linha in linhas:
        draw.text(
            (
                53,
                y,
            ),
            linha,
            font=fonte_titulo,
            fill=AZUL,
        )

        y += 58

    _desenhar_bullets(
        draw,
        produto,
        max(
            550,
            y + 24,
        ),
    )

    _desenhar_produto(
        imagem,
        produto[
            "imagem"
        ],
    )

    desconto = float(
        produto.get(
            "desconto_instagram",
            0,
        )
        or 0
    )

    _desenhar_selo_desconto(
        draw,
        desconto,
    )

    preco = float(
        produto[
            "preco"
        ]
    )

    preco_original = (
        produto.get(
            "preco_original"
        )
    )

    if (
        preco_original is not None
        and float(
            preco_original
        ) > preco
    ):
        texto_antigo = (
            "DE "
            + _moeda(
                preco_original
            )
        )

        fonte_antigo = _fonte(
            31,
            bold=True,
        )

        draw.text(
            (
                260,
                885,
            ),
            texto_antigo,
            font=fonte_antigo,
            fill=AZUL_CLARO,
        )

        bbox = draw.textbbox(
            (
                260,
                885,
            ),
            texto_antigo,
            font=fonte_antigo,
        )

        meio = (
            bbox[1]
            + bbox[3]
        ) // 2

        draw.line(
            (
                bbox[0],
                meio,
                bbox[2],
                meio,
            ),
            fill=AZUL_CLARO,
            width=4,
        )

    draw.text(
        (
            268,
            936,
        ),
        "POR",
        font=_fonte(
            31,
            bold=True,
        ),
        fill="#F5A900",
    )

    draw.text(
        (
            268,
            978,
        ),
        _moeda(
            preco
        ),
        font=_fonte(
            64,
            bold=True,
        ),
        fill="#F5A900",
    )

    # Rodapé
    draw.text(
        (
            665,
            1195,
        ),
        "ENTRE NO GRUPO E RECEBA AS",
        anchor="mm",
        font=_fonte(
            31,
            bold=True,
        ),
        fill=AZUL,
    )

    draw.text(
        (
            665,
            1240,
        ),
        "MELHORES PROMOÇÕES!",
        anchor="mm",
        font=_fonte(
            35,
            bold=True,
        ),
        fill=AZUL,
    )

    draw.rounded_rectangle(
        (
            550,
            1283,
            860,
            1336,
        ),
        radius=28,
        fill=VERDE,
    )

    draw.text(
        (
            705,
            1309,
        ),
        "LINK NA BIO",
        anchor="mm",
        font=_fonte(
            30,
            bold=True,
        ),
        fill=BRANCO,
    )

    destino = Path(
        destino
    )

    destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    imagem.save(
        destino,
        "JPEG",
        quality=94,
        optimize=True,
    )

    return destino


def gerar_artes_top(
    produtos
):
    agora = datetime.now(
        FUSO_BRASIL
    )

    chave_data = agora.strftime(
        "%Y-%m-%d"
    )

    pasta = (
        GERADAS_ROOT
        / chave_data
    )

    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove apenas as artes do mesmo dia para não deixar
    # arquivos antigos quando o Top 5 mudar.
    for antigo in pasta.glob(
        "*.jpg"
    ):
        antigo.unlink(
            missing_ok=True
        )

    artes = []

    for posicao, produto in enumerate(
        produtos,
        start=1,
    ):
        ml_id = _normalizar_nome_arquivo(
            produto.get(
                "ml_id"
            )
        )

        nome_arquivo = (
            f"{posicao:02d}_{ml_id}.jpg"
        )

        caminho = (
            pasta
            / nome_arquivo
        )

        gerar_arte_produto(
            produto=produto,
            destino=caminho,
            posicao=posicao,
        )

        relativo_static = (
            caminho.relative_to(
                STATIC_ROOT
            )
            .as_posix()
        )

        artes.append({
            "posicao":
                posicao,

            "nome":
                produto.get(
                    "nome"
                ),

            "ml_id":
                produto.get(
                    "ml_id"
                ),

            "arquivo":
                relativo_static,
        })

    return {
        "data_chave":
            chave_data,

        "artes":
            artes,
    }


def listar_artes_do_dia():
    chave_data = (
        datetime.now(
            FUSO_BRASIL
        )
        .strftime(
            "%Y-%m-%d"
        )
    )

    pasta = (
        GERADAS_ROOT
        / chave_data
    )

    if not pasta.exists():
        return []

    artes = []

    for caminho in sorted(
        pasta.glob(
            "*.jpg"
        )
    ):
        nome = caminho.stem

        try:
            posicao = int(
                nome.split(
                    "_",
                    1,
                )[0]
            )

        except (
            ValueError,
            IndexError,
        ):
            posicao = 999

        artes.append({
            "posicao":
                posicao,

            "arquivo":
                caminho.relative_to(
                    STATIC_ROOT
                ).as_posix(),
        })

    return artes
