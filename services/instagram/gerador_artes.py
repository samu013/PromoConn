from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LARGURA = 1080
ALTURA = 1350

BASE_DIR = Path(__file__).resolve().parents[2]

PASTA_IMAGENS = BASE_DIR / "static" / "img"
PASTA_INSTAGRAM = PASTA_IMAGENS / "instagram"

LOGO_PATH = PASTA_INSTAGRAM / "logo.png"
ROBO_FEMININO_PATH = PASTA_INSTAGRAM / "robo_feminino.png"
ROBO_MASCULINO_PATH = PASTA_INSTAGRAM / "robo_masculino.png"

PASTA_SAIDA = PASTA_INSTAGRAM / "geradas"


# ============================================================
# CORES
# ============================================================

AZUL_ESCURO = "#07163F"
AZUL = "#168FD0"
AZUL_CLARO = "#20A4E5"

BRANCO = "#FFFFFF"
VERDE = "#69C92A"
VERDE_ESCURO = "#49A91E"

AMARELO = "#FFBF22"
AMARELO_ESCURO = "#E9A900"

CINZA = "#6B7280"
PRETO = "#101828"

VERMELHO = "#D92D20"


# ============================================================
# FONTES
# ============================================================

FONT_DIR = Path("C:/Windows/Fonts")

FONT_BOLD = FONT_DIR / "arialbd.ttf"
FONT_REGULAR = FONT_DIR / "arial.ttf"
FONT_BLACK = FONT_DIR / "arialbd.ttf"


def fonte(tamanho, negrito=True):
    """
    Carrega uma fonte do Windows.
    """

    caminho = FONT_BOLD if negrito else FONT_REGULAR

    try:
        return ImageFont.truetype(
            str(caminho),
            tamanho,
        )

    except Exception:
        return ImageFont.load_default()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def texto_tamanho(draw, texto, font):
    """
    Retorna largura e altura aproximadas do texto.
    """

    caixa = draw.textbbox(
        (0, 0),
        texto,
        font=font,
    )

    return (
        caixa[2] - caixa[0],
        caixa[3] - caixa[1],
    )


def quebrar_texto(
    draw,
    texto,
    font,
    largura_maxima,
):
    """
    Quebra o título em linhas sem ultrapassar
    a largura disponível.
    """

    palavras = texto.split()

    linhas = []
    linha_atual = ""

    for palavra in palavras:

        tentativa = (
            palavra
            if not linha_atual
            else f"{linha_atual} {palavra}"
        )

        largura, _ = texto_tamanho(
            draw,
            tentativa,
            font,
        )

        if largura <= largura_maxima:
            linha_atual = tentativa

        else:
            if linha_atual:
                linhas.append(linha_atual)

            linha_atual = palavra

    if linha_atual:
        linhas.append(linha_atual)

    return linhas


def desenhar_texto_centralizado(
    draw,
    texto,
    y,
    font,
    cor,
):
    """
    Desenha um texto centralizado horizontalmente.
    """

    largura, altura = texto_tamanho(
        draw,
        texto,
        font,
    )

    x = (LARGURA - largura) // 2

    draw.text(
        (x, y),
        texto,
        font=font,
        fill=cor,
    )

    return altura


def carregar_imagem(caminho):
    """
    Carrega uma imagem se ela existir.
    """

    if not caminho:
        return None

    caminho = Path(caminho)

    if not caminho.exists():
        return None

    try:
        return Image.open(caminho).convert("RGBA")

    except Exception:
        return None


# ============================================================
# FOTO DO PRODUTO
# ============================================================

def preparar_foto_produto(
    caminho,
    tamanho=430,
):
    """
    Coloca o produto dentro de uma área quadrada
    sem distorcer a imagem.

    O produto nunca ultrapassa a área.
    """

    imagem = carregar_imagem(caminho)

    if imagem is None:
        return None

    imagem.thumbnail(
        (
            tamanho - 60,
            tamanho - 60,
        ),
        Image.Resampling.LANCZOS,
    )

    fundo = Image.new(
        "RGBA",
        (
            tamanho,
            tamanho,
        ),
        BRANCO,
    )

    x = (
        tamanho - imagem.width
    ) // 2

    y = (
        tamanho - imagem.height
    ) // 2

    fundo.alpha_composite(
        imagem,
        (
            x,
            y,
        ),
    )

    return fundo


def criar_area_produto(
    imagem_produto,
    tamanho=470,
):
    """
    Cria o círculo onde ficará o produto.

    Importante:
    o fundo é criado do zero.
    Nenhuma imagem de modelo é utilizada.
    """

    area = Image.new(
        "RGBA",
        (
            tamanho,
            tamanho,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    draw = ImageDraw.Draw(area)

    centro = tamanho // 2

    # Círculo externo
    draw.ellipse(
        (
            0,
            0,
            tamanho - 1,
            tamanho - 1,
        ),
        fill=AMARELO,
        outline=BRANCO,
        width=8,
    )

    # Círculo interno
    margem = 18

    draw.ellipse(
        (
            margem,
            margem,
            tamanho - margem,
            tamanho - margem,
        ),
        fill=BRANCO,
        outline=AZUL_ESCURO,
        width=7,
    )

    if imagem_produto is not None:

        produto = preparar_foto_produto(
            imagem_produto,
            tamanho=tamanho - 55,
        )

        if produto:

            # Máscara circular interna
            mascara = Image.new(
                "L",
                produto.size,
                0,
            )

            mascara_draw = ImageDraw.Draw(
                mascara
            )

            mascara_draw.ellipse(
                (
                    0,
                    0,
                    produto.width,
                    produto.height,
                ),
                fill=255,
            )

            produto_circular = Image.new(
                "RGBA",
                produto.size,
                (
                    255,
                    255,
                    255,
                    0,
                ),
            )

            produto_circular.paste(
                produto,
                (
                    0,
                    0,
                ),
                mascara,
            )

            x = (
                tamanho
                - produto.width
            ) // 2

            y = (
                tamanho
                - produto.height
            ) // 2

            area.alpha_composite(
                produto_circular,
                (
                    x,
                    y,
                ),
            )

    return area


# ============================================================
# TÍTULO
# ============================================================

def desenhar_titulo(
    imagem,
    draw,
    titulo,
):
    """
    Desenha o título com tamanho automático.

    Evita que títulos grandes saiam da área.
    """

    largura_maxima = 540

    tamanho = 72

    while tamanho >= 42:

        font = fonte(
            tamanho,
            True,
        )

        linhas = quebrar_texto(
            draw,
            titulo.upper(),
            font,
            largura_maxima,
        )

        if len(linhas) <= 3:
            break

        tamanho -= 4

    font = fonte(
        tamanho,
        True,
    )

    linhas = quebrar_texto(
        draw,
        titulo.upper(),
        font,
        largura_maxima,
    )

    y = 340

    espacamento = 8

    for linha in linhas[:3]:

        largura, altura = texto_tamanho(
            draw,
            linha,
            font,
        )

        x = 55

        draw.text(
            (
                x,
                y,
            ),
            linha,
            font=font,
            fill=BRANCO,
        )

        y += altura + espacamento

    return y


# ============================================================
# INFORMAÇÕES
# ============================================================

def desenhar_informacoes(
    draw,
    y,
    categoria,
    ranking,
):
    font = fonte(
        31,
        False,
    )

    cor = BRANCO

    informacoes = [
        f"Categoria: {categoria}",
        f"Ranking Mercado Livre: #{ranking}",
    ]

    for texto in informacoes:

        draw.text(
            (
                60,
                y,
            ),
            "✓",
            font=fonte(
                34,
                True,
            ),
            fill=VERDE,
        )

        draw.text(
            (
                105,
                y + 2,
            ),
            texto,
            font=font,
            fill=cor,
        )

        y += 54

    return y


# ============================================================
# SELO DE DESCONTO
# ============================================================

def desenhar_desconto(
    draw,
    percentual,
    centro_x,
    centro_y,
):
    """
    Cria um selo de desconto separado.
    """

    raio = 85

    draw.ellipse(
        (
            centro_x - raio,
            centro_y - raio,
            centro_x + raio,
            centro_y + raio,
        ),
        fill=VERDE,
        outline=BRANCO,
        width=6,
    )

    texto = f"{percentual}% OFF"

    font = fonte(
        30,
        True,
    )

    largura, altura = texto_tamanho(
        draw,
        texto,
        font,
    )

    draw.text(
        (
            centro_x - largura // 2,
            centro_y - altura // 2,
        ),
        texto,
        font=font,
        fill=BRANCO,
    )


# ============================================================
# PREÇOS
# ============================================================

def desenhar_precos(
    draw,
    preco_antigo,
    preco_atual,
    percentual,
):
    """
    Área exclusiva para preços.

    Evita sobreposição entre preço antigo,
    POR e preço atual.
    """

    centro_x = 270

    y = 910

    # --------------------------------------------------------
    # DESCONTO
    # --------------------------------------------------------

    if percentual:

        desenhar_desconto(
            draw,
            percentual,
            270,
            835,
        )

    # --------------------------------------------------------
    # PREÇO ANTIGO
    # --------------------------------------------------------

    if preco_antigo:

        texto_antigo = (
            f"DE R${preco_antigo}"
        )

        font_antigo = fonte(
            34,
            True,
        )

        largura, altura = texto_tamanho(
            draw,
            texto_antigo,
            font_antigo,
        )

        x = (
            centro_x
            - largura // 2
        )

        draw.text(
            (
                x,
                y,
            ),
            texto_antigo,
            font=font_antigo,
            fill=AZUL,
        )

        # Linha de desconto
        draw.line(
            (
                x,
                y + altura // 2,
                x + largura,
                y + altura // 2,
            ),
            fill=AZUL,
            width=5,
        )

        y += 58

    # --------------------------------------------------------
    # POR
    # --------------------------------------------------------

    font_por = fonte(
        34,
        True,
    )

    largura, altura = texto_tamanho(
        draw,
        "POR",
        font_por,
    )

    draw.text(
        (
            centro_x - largura // 2,
            y,
        ),
        "POR",
        font=font_por,
        fill=AMARELO,
    )

    y += 45

    # --------------------------------------------------------
    # PREÇO ATUAL
    # --------------------------------------------------------

    font_atual = fonte(
        58,
        True,
    )

    texto_atual = (
        f"R${preco_atual}"
    )

    # Reduz automaticamente se ficar muito largo

    while True:

        largura, altura = texto_tamanho(
            draw,
            texto_atual,
            font_atual,
        )

        if largura <= 470:
            break

        tamanho_atual = max(
            42,
            font_atual.size - 3,
        )

        font_atual = fonte(
            tamanho_atual,
            True,
        )

    largura, altura = texto_tamanho(
        draw,
        texto_atual,
        font_atual,
    )

    draw.text(
        (
            centro_x - largura // 2,
            y,
        ),
        texto_atual,
        font=font_atual,
        fill=AMARELO,
    )


# ============================================================
# ROBÔS
# ============================================================

def desenhar_robo(
    imagem,
    caminho,
    x,
    y,
    largura=210,
):
    """
    Coloca um robô sem deformá-lo.
    """

    robo = carregar_imagem(
        caminho
    )

    if robo is None:
        return

    proporcao = (
        largura / robo.width
    )

    altura = int(
        robo.height * proporcao
    )

    robo = robo.resize(
        (
            largura,
            altura,
        ),
        Image.Resampling.LANCZOS,
    )

    imagem.alpha_composite(
        robo,
        (
            x,
            y,
        ),
    )


# ============================================================
# RODAPÉ
# ============================================================

def desenhar_rodape(
    imagem,
    draw,
):
    """
    Chamada para o grupo de promoções.
    """

    topo = 1160

    # Faixa branca
    draw.rounded_rectangle(
        (
            35,
            topo,
            LARGURA - 35,
            ALTURA - 30,
        ),
        radius=35,
        fill=BRANCO,
    )

    texto1 = (
        "ENTRE NO GRUPO E RECEBA"
    )

    texto2 = (
        "AS MELHORES PROMOÇÕES!"
    )

    font1 = fonte(
        36,
        True,
    )

    font2 = fonte(
        36,
        True,
    )

    desenhar_texto_centralizado(
        draw,
        texto1,
        topo + 25,
        font1,
        AZUL_ESCURO,
    )

    desenhar_texto_centralizado(
        draw,
        texto2,
        topo + 72,
        font2,
        AZUL_ESCURO,
    )

    # Botão
    botao_largura = 360
    botao_altura = 58

    botao_x = (
        LARGURA
        - botao_largura
    ) // 2

    botao_y = topo + 135

    draw.rounded_rectangle(
        (
            botao_x,
            botao_y,
            botao_x + botao_largura,
            botao_y + botao_altura,
        ),
        radius=30,
        fill=VERDE,
    )

    texto_botao = "LINK NA BIO"

    font_botao = fonte(
        31,
        True,
    )

    largura, altura = texto_tamanho(
        draw,
        texto_botao,
        font_botao,
    )

    draw.text(
        (
            LARGURA // 2 - largura // 2,
            botao_y + 10,
        ),
        texto_botao,
        font=font_botao,
        fill=BRANCO,
    )


# ============================================================
# GERADOR PRINCIPAL
# ============================================================

def gerar_arte(
    produto,
    caminho_saida=None,
):
    """
    Gera uma arte individual para Instagram.

    Espera um dicionário semelhante a:

    {
        "titulo": "...",
        "categoria": "Games",
        "ranking": 5,
        "preco_antigo": "699,00",
        "preco_atual": "469,00",
        "desconto": 33,
        "imagem": "/caminho/foto.png"
    }
    """

    # --------------------------------------------------------
    # FUNDO
    # --------------------------------------------------------

    imagem = Image.new(
        "RGBA",
        (
            LARGURA,
            ALTURA,
        ),
        AZUL_ESCURO,
    )

    draw = ImageDraw.Draw(
        imagem
    )

    # --------------------------------------------------------
    # ELEMENTOS DECORATIVOS
    # --------------------------------------------------------

    draw.rectangle(
        (
            0,
            0,
            LARGURA,
            18,
        ),
        fill=VERDE,
    )

    draw.rectangle(
        (
            0,
            18,
            LARGURA,
            30,
        ),
        fill=AMARELO,
    )

    # --------------------------------------------------------
    # LOGO
    # --------------------------------------------------------

    logo = carregar_imagem(
        LOGO_PATH
    )

    if logo:

        logo.thumbnail(
            (
                430,
                150,
            ),
            Image.Resampling.LANCZOS,
        )

        imagem.alpha_composite(
            logo,
            (
                45,
                50,
            ),
        )

    # --------------------------------------------------------
    # CATEGORIA
    # --------------------------------------------------------

    categoria = str(
        produto.get(
            "categoria",
            "Promoção",
        )
    )

    draw.rounded_rectangle(
        (
            55,
            215,
            270,
            265,
        ),
        radius=25,
        fill=AZUL,
    )

    draw.text(
        (
            80,
            223,
        ),
        categoria.upper(),
        font=fonte(
            23,
            True,
        ),
        fill=BRANCO,
    )

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    ranking = produto.get(
        "ranking"
    )

    if ranking:

        texto_ranking = (
            f"TOP {ranking}"
        )

        draw.text(
            (
                55,
                285,
            ),
            texto_ranking,
            font=fonte(
                29,
                True,
            ),
            fill=AMARELO,
        )

    # --------------------------------------------------------
    # TÍTULO
    # --------------------------------------------------------

    titulo = str(
        produto.get(
            "titulo",
            "Produto em promoção",
        )
    )

    desenhar_titulo(
        imagem,
        draw,
        titulo,
    )

    # --------------------------------------------------------
    # INFORMAÇÕES
    # --------------------------------------------------------

    y_info = 570

    y_info = desenhar_informacoes(
        draw,
        y_info,
        categoria,
        produto.get(
            "ranking",
            "-",
        ),
    )

    # --------------------------------------------------------
    # CÍRCULO DO PRODUTO
    # --------------------------------------------------------

    imagem_produto = produto.get(
        "imagem"
    )

    circulo = criar_area_produto(
        imagem_produto,
        tamanho=470,
    )

    imagem.alpha_composite(
        circulo,
        (
            570,
            360,
        ),
    )

    # --------------------------------------------------------
    # PREÇOS
    # --------------------------------------------------------

    desenhar_precos(
        draw,
        produto.get(
            "preco_antigo"
        ),
        produto.get(
            "preco_atual",
            "0,00",
        ),
        produto.get(
            "desconto"
        ),
    )

    # --------------------------------------------------------
    # ROBÔS
    # --------------------------------------------------------

    desenhar_robo(
        imagem,
        ROBO_FEMININO_PATH,
        35,
        880,
        largura=190,
    )

    desenhar_robo(
        imagem,
        ROBO_MASCULINO_PATH,
        700,
        880,
        largura=190,
    )

    # --------------------------------------------------------
    # RODAPÉ
    # --------------------------------------------------------

    desenhar_rodape(
        imagem,
        draw,
    )

    # --------------------------------------------------------
    # SAÍDA
    # --------------------------------------------------------

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    if caminho_saida is None:

        ml_id = produto.get(
            "ml_id",
            "produto",
        )

        caminho_saida = (
            PASTA_SAIDA
            / f"{ml_id}.png"
        )

    else:
        caminho_saida = Path(
            caminho_saida
        )

        caminho_saida.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    imagem.convert(
        "RGB"
    ).save(
        caminho_saida,
        "PNG",
        optimize=True,
    )

    print(
        f"🖼️ Arte Instagram criada: "
        f"{caminho_saida}"
    )

    return caminho_saida

# ============================================================
# ARTES DO TOP 5 DO DIA
# ============================================================

def gerar_artes_top(produtos):
    """
    Gera automaticamente as artes dos produtos selecionados
    para o Instagram.

    Recebe uma lista de dicionários de produtos.

    Exemplo:

    [
        {
            "ml_id": "123",
            "titulo": "Produto X",
            "categoria": "Games",
            "ranking": 1,
            "preco_antigo": "699,00",
            "preco_atual": "469,00",
            "desconto": 33,
            "imagem": "/caminho/foto.png"
        }
    ]

    Retorna uma lista com os caminhos das artes geradas.
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

    print(
        "\n"
        + "=" * 60
    )
    print(
        "📸 GERANDO ARTES DO INSTAGRAM"
    )
    print(
        "=" * 60
    )

    for posicao, produto in enumerate(
        produtos[:5],
        start=1,
    ):
        try:
            # Garante ranking mesmo que o seletor
            # não tenha enviado esse campo.
            if not produto.get("ranking"):
                produto["ranking"] = posicao

            caminho = gerar_arte(
                produto
            )

            artes.append(
                caminho
            )

            print(
                f"✅ Arte {posicao}/5 criada: "
                f"{caminho}"
            )

        except Exception as erro:
            print(
                f"❌ Erro ao gerar arte "
                f"{posicao}/5: {erro}"
            )

    print(
        f"📸 Total de artes geradas: "
        f"{len(artes)}"
    )

    return artes


def listar_artes_do_dia():
    """
    Lista as artes PNG geradas no dia.

    Como o Render pode reiniciar o serviço e o diretório
    pode ser limpo, esta função serve principalmente para
    uso local e visualização durante o processo.
    """

    if not PASTA_SAIDA.exists():
        return []

    arquivos = sorted(
        PASTA_SAIDA.glob("*.png"),
        key=lambda arquivo: arquivo.stat().st_mtime,
        reverse=True,
    )

    return arquivos