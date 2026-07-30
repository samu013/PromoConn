from mercadolivre.client import MercadoLivreClient


class Highlights:
    def __init__(self):
        self.client = MercadoLivreClient()

    @staticmethod
    def _primeira_imagem(item):
        imagem = item.get("imagem") or item.get("picture") or item.get("thumbnail")
        if imagem:
            return imagem

        pictures = item.get("pictures")
        if isinstance(pictures, list) and pictures:
            primeira = pictures[0]
            if isinstance(primeira, dict):
                return primeira.get("url") or primeira.get("secure_url") or primeira.get("id")
            return primeira
        return None

    @staticmethod
    def _normalizar_item(item, posicao):
        if not isinstance(item, dict):
            return None

        ml_id = item.get("id") or item.get("item_id") or item.get("product_id") or item.get("user_product_id")
        tipo = item.get("type") or item.get("tipo") or item.get("entity_type")
        nome = item.get("name") or item.get("title") or item.get("nome")
        categoria_id = item.get("category_id") or item.get("category")

        if isinstance(categoria_id, dict):
            categoria_id = categoria_id.get("id")

        if not ml_id or not nome:
            return None

        return {
            "id": str(ml_id),
            "tipo": tipo or "PRODUCT",
            "nome": nome,
            "imagem": Highlights._primeira_imagem(item),
            "ranking": item.get("position") or item.get("ranking") or item.get("rank") or posicao,
            "category_id": categoria_id,
            "dados_originais": item,
        }

    def buscar(self, categoria_id):
        resposta = self.client.get(f"/highlights/MLB/category/{categoria_id}")

        if resposta.status_code != 200:
            raise RuntimeError(
                f"Erro ao buscar Highlights da categoria {categoria_id}: "
                f"HTTP {resposta.status_code} - {resposta.text[:500]}"
            )

        try:
            dados = resposta.json()
        except Exception as erro:
            raise RuntimeError("A resposta dos Highlights não contém um JSON válido.") from erro

        if isinstance(dados, dict):
            conteudo = dados.get("content") or dados.get("results") or dados.get("items") or []
        elif isinstance(dados, list):
            conteudo = dados
        else:
            conteudo = []

        if not isinstance(conteudo, list):
            return []

        produtos = []
        for posicao, item in enumerate(conteudo, start=1):
            produto = self._normalizar_item(item, posicao)
            if produto:
                produtos.append(produto)
        return produtos
