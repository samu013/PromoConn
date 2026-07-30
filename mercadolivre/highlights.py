import json
import time

from mercadolivre.client import MercadoLivreClient


class CategoriaHighlightsInvalida(Exception):
    """A categoria existe no catálogo, mas não é aceita pelos Highlights."""


class Highlights:
    """
    Cliente resiliente para o endpoint de Highlights do Mercado Livre.

    Melhorias:
    - aceita diferentes formatos de resposta;
    - tenta novamente quando a API retorna 200 com lista vazia;
    - diferencia categoria inválida (404) de falha temporária;
    - preserva category_id;
    - imprime diagnóstico resumido sem expor o access token.
    """

    TENTATIVAS_PADRAO = 3
    ESPERA_INICIAL_SEGUNDOS = 3

    def __init__(
        self,
        tentativas=None,
        espera_inicial=None,
    ):
        self.client = MercadoLivreClient()

        self.tentativas = (
            tentativas
            if tentativas is not None
            else self.TENTATIVAS_PADRAO
        )

        self.espera_inicial = (
            espera_inicial
            if espera_inicial is not None
            else self.ESPERA_INICIAL_SEGUNDOS
        )

    @staticmethod
    def _resumo_json(dados, limite=800):
        try:
            texto = json.dumps(
                dados,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except Exception:
            texto = repr(dados)

        if len(texto) > limite:
            texto = texto[:limite] + "..."

        return texto

    @staticmethod
    def _encontrar_lista(dados):
        """
        Procura a lista de resultados nos formatos mais comuns.

        Formatos aceitos:
        - uma lista diretamente;
        - {"content": [...]}
        - {"results": [...]}
        - {"items": [...]}
        - {"data": [...]}
        - {"data": {"content": [...]}}
        - {"highlights": [...]}
        """

        if isinstance(dados, list):
            return dados, "raiz"

        if not isinstance(dados, dict):
            return [], "tipo_desconhecido"

        chaves_diretas = (
            "content",
            "results",
            "items",
            "highlights",
            "products",
        )

        for chave in chaves_diretas:
            valor = dados.get(chave)

            if isinstance(valor, list):
                return valor, chave

        data = dados.get("data")

        if isinstance(data, list):
            return data, "data"

        if isinstance(data, dict):
            for chave in chaves_diretas:
                valor = data.get(chave)

                if isinstance(valor, list):
                    return valor, f"data.{chave}"

        # Último recurso: procura apenas um nível abaixo.
        for chave_pai, valor_pai in dados.items():
            if not isinstance(valor_pai, dict):
                continue

            for chave in chaves_diretas:
                valor = valor_pai.get(chave)

                if isinstance(valor, list):
                    return valor, f"{chave_pai}.{chave}"

        return [], "lista_nao_encontrada"

    @staticmethod
    def _primeira_imagem(item):
        imagem = (
            item.get("imagem")
            or item.get("picture")
            or item.get("thumbnail")
            or item.get("secure_thumbnail")
        )

        if isinstance(imagem, dict):
            imagem = (
                imagem.get("url")
                or imagem.get("secure_url")
                or imagem.get("id")
            )

        if imagem:
            return imagem

        pictures = item.get("pictures")

        if isinstance(pictures, dict):
            pictures = (
                pictures.get("pictures")
                or pictures.get("items")
                or []
            )

        if isinstance(pictures, list) and pictures:
            primeira = pictures[0]

            if isinstance(primeira, dict):
                return (
                    primeira.get("url")
                    or primeira.get("secure_url")
                    or primeira.get("id")
                )

            return primeira

        return None

    @staticmethod
    def _normalizar_item(item, posicao, categoria_consultada):
        if not isinstance(item, dict):
            return None

        # Alguns formatos envolvem o produto em "item" ou "product".
        base = item

        for chave in ("item", "product", "data"):
            valor = item.get(chave)

            if isinstance(valor, dict):
                base = {
                    **item,
                    **valor,
                }
                break

        ml_id = (
            base.get("id")
            or base.get("item_id")
            or base.get("product_id")
            or base.get("user_product_id")
            or base.get("catalog_product_id")
        )

        tipo = (
            base.get("type")
            or base.get("tipo")
            or base.get("entity_type")
            or base.get("resource_type")
        )

        nome = (
            base.get("name")
            or base.get("title")
            or base.get("nome")
            or base.get("short_title")
            or base.get("display_name")
        )

        categoria_id = (
            base.get("category_id")
            or base.get("category")
            or categoria_consultada
        )

        if isinstance(categoria_id, dict):
            categoria_id = categoria_id.get("id")

        if not ml_id:
            return None

        # Há respostas de Highlights que possuem apenas ID e TYPE.
        # Nesse caso o nome poderá ser enriquecido depois.
        return {
            "id": str(ml_id),
            "tipo": str(tipo or "PRODUCT"),
            "nome": nome,
            "imagem": Highlights._primeira_imagem(base),
            "ranking": (
                base.get("position")
                or base.get("ranking")
                or base.get("rank")
                or posicao
            ),
            "category_id": categoria_id,
            "dados_originais": item,
        }

    def _enriquecer_produto(self, produto):
        """
        Busca detalhes quando o Highlight retorna somente ID e TYPE.

        PRODUCT:
            GET /products/{id}

        ITEM:
            GET /items/{id}

        USER_PRODUCT:
            GET /user-products/{id}

        Se o endpoint específico não estiver disponível, o produto
        permanece com os dados que já possuía.
        """

        if produto.get("nome") and produto.get("category_id"):
            return produto

        produto_id = produto["id"]
        tipo = str(produto.get("tipo") or "").upper()

        caminhos = []

        if tipo == "USER_PRODUCT" or produto_id.startswith("MLBU"):
            caminhos.append(f"/user-products/{produto_id}")

        if tipo == "ITEM":
            caminhos.append(f"/items/{produto_id}")

        if tipo == "PRODUCT":
            caminhos.append(f"/products/{produto_id}")

        # IDs MLB podem ser produto de catálogo ou anúncio. Quando o tipo
        # não é suficiente, testamos os dois endpoints para reduzir itens
        # sem nome.
        if produto_id.startswith("MLB") and not produto_id.startswith("MLBU"):
            caminhos.append(f"/products/{produto_id}")
            caminhos.append(f"/items/{produto_id}")

        # Evita repetir o mesmo caminho.
        caminhos = list(dict.fromkeys(caminhos))

        for caminho in caminhos:
            try:
                resposta = self.client.get(caminho)
            except Exception:
                continue

            if resposta.status_code != 200:
                continue

            try:
                detalhes = resposta.json()
            except Exception:
                continue

            if not isinstance(detalhes, dict):
                continue

            nome = (
                detalhes.get("name")
                or detalhes.get("title")
                or detalhes.get("short_title")
                or detalhes.get("display_name")
            )

            categoria_id = (
                detalhes.get("category_id")
                or detalhes.get("category")
            )

            if isinstance(categoria_id, dict):
                categoria_id = categoria_id.get("id")

            imagem = self._primeira_imagem(detalhes)

            if nome:
                produto["nome"] = nome

            if categoria_id:
                produto["category_id"] = categoria_id

            if imagem:
                produto["imagem"] = imagem

            if produto.get("nome") and produto.get("category_id"):
                break

        return produto

    def buscar(self, categoria_id):
        endpoint = f"/highlights/MLB/category/{categoria_id}"
        ultimo_diagnostico = None

        for tentativa in range(1, self.tentativas + 1):
            resposta = self.client.get(endpoint)
            status = resposta.status_code

            if status == 404:
                raise CategoriaHighlightsInvalida(
                    f"Categoria {categoria_id} não aceita pelo endpoint "
                    "de Highlights."
                )

            if status in (401, 403):
                raise RuntimeError(
                    f"Falha de autenticação nos Highlights "
                    f"(HTTP {status}): {resposta.text[:500]}"
                )

            if status == 429:
                ultimo_diagnostico = "limite de requisições (HTTP 429)"

            elif status >= 500:
                ultimo_diagnostico = f"falha temporária HTTP {status}"

            elif status != 200:
                raise RuntimeError(
                    f"Erro ao buscar Highlights da categoria "
                    f"{categoria_id}: HTTP {status} - "
                    f"{resposta.text[:500]}"
                )

            else:
                try:
                    dados = resposta.json()
                except Exception as erro:
                    ultimo_diagnostico = (
                        "resposta 200 sem JSON válido: "
                        f"{erro}"
                    )
                else:
                    conteudo, formato = self._encontrar_lista(dados)

                    if conteudo:
                        produtos = []

                        for posicao, item in enumerate(
                            conteudo,
                            start=1,
                        ):
                            produto = self._normalizar_item(
                                item,
                                posicao,
                                categoria_id,
                            )

                            if not produto:
                                continue

                            produto = self._enriquecer_produto(
                                produto
                            )

                            produtos.append(produto)

                        print(
                            f"    Formato da resposta: {formato}; "
                            f"itens normalizados: {len(produtos)}"
                        )

                        return produtos

                    ultimo_diagnostico = (
                        f"HTTP 200, formato={formato}, "
                        "mas sem itens"
                    )

                    # Apenas na última tentativa mostra uma amostra.
                    if tentativa == self.tentativas:
                        print(
                            "    Diagnóstico da resposta vazia: "
                            f"{self._resumo_json(dados)}"
                        )

            if tentativa < self.tentativas:
                espera = self.espera_inicial * tentativa

                print(
                    f"    Resposta vazia/temporária "
                    f"({ultimo_diagnostico}). "
                    f"Nova tentativa em {espera}s "
                    f"[{tentativa}/{self.tentativas}]."
                )

                time.sleep(espera)

        print(
            f"    A categoria {categoria_id} continuou sem produtos "
            f"após {self.tentativas} tentativas "
            f"({ultimo_diagnostico})."
        )

        return []
