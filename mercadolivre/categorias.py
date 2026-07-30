import time
from collections import deque


class CategoriasMercadoLivre:
    TEMPO_CACHE_SEGUNDOS = 6 * 60 * 60

    def __init__(self, client):
        self.client = client
        self._cache = {}

    def _cache_valido(self, categoria_id):
        registro = self._cache.get(categoria_id)
        return bool(registro) and (
            time.time() - registro["salvo_em"] < self.TEMPO_CACHE_SEGUNDOS
        )

    def buscar(self, categoria_id):
        if not categoria_id:
            return None

        categoria_id = str(categoria_id).strip()
        if self._cache_valido(categoria_id):
            return self._cache[categoria_id]["dados"]

        resposta = self.client.get(f"/categories/{categoria_id}")
        if resposta.status_code != 200:
            print(f"⚠️ Categoria {categoria_id} não encontrada (HTTP {resposta.status_code}).")
            return None

        try:
            dados = resposta.json()
        except Exception as erro:
            print(f"⚠️ JSON inválido para a categoria {categoria_id}: {erro}")
            return None

        if not isinstance(dados, dict):
            return None

        self._cache[categoria_id] = {"dados": dados, "salvo_em": time.time()}
        return dados

    def caminho(self, categoria_id):
        dados = self.buscar(categoria_id)
        if not dados:
            return []

        caminho = dados.get("path_from_root")
        if isinstance(caminho, list) and caminho:
            return [
                {"id": item.get("id"), "name": item.get("name")}
                for item in caminho
                if isinstance(item, dict) and (item.get("id") or item.get("name"))
            ]

        return [{"id": dados.get("id", categoria_id), "name": dados.get("name")}]

    def filhos(self, categoria_id):
        dados = self.buscar(categoria_id)
        if not dados:
            return []

        filhos = dados.get("children_categories", [])
        if not isinstance(filhos, list):
            return []

        return [
            filho for filho in filhos
            if isinstance(filho, dict) and filho.get("id")
        ]

    def descendentes(self, categoria_id, max_niveis=3, limite=39):
        """Percorre a árvore oficial em largura até o limite informado."""
        if max_niveis <= 0 or limite <= 0:
            return []

        fila = deque((filho, 1) for filho in self.filhos(categoria_id))
        encontrados = []
        ids_vistos = set()

        while fila and len(encontrados) < limite:
            categoria, nivel = fila.popleft()
            atual_id = str(categoria.get("id") or "").strip()
            if not atual_id or atual_id in ids_vistos:
                continue

            ids_vistos.add(atual_id)
            encontrados.append({
                "id": atual_id,
                "name": categoria.get("name") or atual_id,
                "nivel": nivel,
            })

            if nivel < max_niveis:
                for filho in self.filhos(atual_id):
                    fila.append((filho, nivel + 1))

        return encontrados
