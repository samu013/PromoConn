import time


class CategoriasMercadoLivre:
    TEMPO_CACHE_SEGUNDOS = 6 * 60 * 60

    def __init__(self, client):
        self.client = client
        self._cache = {}

    def _cache_valido(self, categoria_id):
        registro = self._cache.get(categoria_id)
        if not registro:
            return False
        return time.time() - registro["salvo_em"] < self.TEMPO_CACHE_SEGUNDOS

    def buscar(self, categoria_id):
        if not categoria_id:
            return None

        categoria_id = str(categoria_id).strip()

        if self._cache_valido(categoria_id):
            return self._cache[categoria_id]["dados"]

        resposta = self.client.get(f"/categories/{categoria_id}")

        if resposta.status_code != 200:
            print(f"⚠️ Categoria não encontrada: {categoria_id} (HTTP {resposta.status_code})")
            return None

        try:
            dados = resposta.json()
        except Exception as erro:
            print(f"⚠️ Não foi possível ler a categoria {categoria_id}: {erro}")
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
            resultado = []
            for item in caminho:
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id")
                nome = item.get("name")
                if item_id or nome:
                    resultado.append({"id": item_id, "name": nome})
            if resultado:
                return resultado

        return [{"id": dados.get("id", categoria_id), "name": dados.get("name")}]

    def filhos(self, categoria_id):
        dados = self.buscar(categoria_id)
        if not dados:
            return []
        filhos = dados.get("children_categories", [])
        if not isinstance(filhos, list):
            return []
        return [f for f in filhos if isinstance(f, dict) and f.get("id")]

    def limpar_cache(self):
        self._cache.clear()
