import time


class CategoriasMercadoLivre:
    """
    Consulta categorias oficiais do Mercado Livre e guarda cache em memória.
    """

    TEMPO_CACHE_SEGUNDOS = 6 * 60 * 60

    def __init__(self, client):
        self.client = client
        self._cache = {}

    def _cache_valido(self, categoria_id):
        registro = self._cache.get(categoria_id)

        if not registro:
            return False

        return (
            time.time() - registro["salvo_em"]
            < self.TEMPO_CACHE_SEGUNDOS
        )

    def buscar(self, categoria_id):
        if not categoria_id:
            return None

        categoria_id = str(categoria_id).strip()

        if self._cache_valido(categoria_id):
            return self._cache[categoria_id]["dados"]

        resposta = self.client.get(
            f"/categories/{categoria_id}"
        )

        if resposta.status_code != 200:
            print(
                f"⚠️ Categoria {categoria_id} não encontrada "
                f"(HTTP {resposta.status_code})."
            )
            return None

        try:
            dados = resposta.json()
        except Exception as erro:
            print(
                f"⚠️ JSON inválido para a categoria "
                f"{categoria_id}: {erro}"
            )
            return None

        if not isinstance(dados, dict):
            return None

        self._cache[categoria_id] = {
            "dados": dados,
            "salvo_em": time.time(),
        }

        return dados

    def caminho(self, categoria_id):
        dados = self.buscar(categoria_id)

        if not dados:
            return []

        caminho = dados.get("path_from_root")

        if isinstance(caminho, list) and caminho:
            return [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                }
                for item in caminho
                if isinstance(item, dict)
                and (item.get("id") or item.get("name"))
            ]

        return [{
            "id": dados.get("id", categoria_id),
            "name": dados.get("name"),
        }]

    def filhos(self, categoria_id):
        dados = self.buscar(categoria_id)

        if not dados:
            return []

        filhos = dados.get("children_categories", [])

        if not isinstance(filhos, list):
            return []

        return [
            filho
            for filho in filhos
            if isinstance(filho, dict)
            and filho.get("id")
        ]
