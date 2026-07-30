import re
import unicodedata


class ClassificadorCategorias:
    GRUPOS_VALIDOS = {
        "Celulares", "Games", "Tecnologia", "Casa", "Esportes",
        "Moda Feminina", "Moda Masculina",
    }

    IDS_PRINCIPAIS = {
        "MLB1055": "Celulares",
        "MLB1144": "Games",
        "MLB1648": "Tecnologia",
        "MLB1574": "Casa",
        "MLB264201": "Esportes",
    }

    TERMOS_FEMININOS = {
        "feminino", "feminina", "mulher", "mulheres", "vestido",
        "vestidos", "saia", "saias", "sutia", "calcinha", "lingerie",
        "maternidade",
    }

    TERMOS_MASCULINOS = {
        "masculino", "masculina", "homem", "homens", "cueca", "cuecas",
        "gravata", "terno", "ternos",
    }

    def __init__(self, categorias):
        self.categorias = categorias

    @staticmethod
    def normalizar(texto):
        texto = str(texto or "").lower().strip()
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = re.sub(r"[^a-z0-9]+", " ", texto)
        return " ".join(texto.split())

    def _texto_caminho(self, caminho):
        nomes = [self.normalizar(i.get("name")) for i in caminho if isinstance(i, dict)]
        return " | ".join(n for n in nomes if n)

    @staticmethod
    def _ids_caminho(caminho):
        return {str(i.get("id")) for i in caminho if isinstance(i, dict) and i.get("id")}

    @staticmethod
    def _tem_termo(texto, termos):
        return bool(set(texto.split()).intersection(termos))

    def _classificar_moda(self, caminho_texto, titulo):
        oficial = self.normalizar(caminho_texto)
        titulo = self.normalizar(titulo)

        feminino_oficial = any(t in oficial for t in ("feminina", "feminino", "mulheres", "mulher"))
        masculino_oficial = any(t in oficial for t in ("masculina", "masculino", "homens", "homem"))

        if feminino_oficial and not masculino_oficial:
            return "Moda Feminina"
        if masculino_oficial and not feminino_oficial:
            return "Moda Masculina"

        feminino_titulo = self._tem_termo(titulo, self.TERMOS_FEMININOS)
        masculino_titulo = self._tem_termo(titulo, self.TERMOS_MASCULINOS)

        if feminino_titulo and not masculino_titulo:
            return "Moda Feminina"
        if masculino_titulo and not feminino_titulo:
            return "Moda Masculina"
        return None

    def classificar(self, categoria_id, titulo=None):
        if not categoria_id:
            return None

        caminho = self.categorias.caminho(categoria_id)
        if not caminho:
            return None

        ids = self._ids_caminho(caminho)
        caminho_texto = self._texto_caminho(caminho)
        texto = self.normalizar(caminho_texto)

        for raiz_id, grupo in self.IDS_PRINCIPAIS.items():
            if raiz_id in ids:
                return grupo

        indicadores_moda = any(t in texto for t in (
            "roupas", "calcados", "bolsas", "moda", "acessorios de moda"
        ))
        if indicadores_moda:
            return self._classificar_moda(caminho_texto, titulo)

        if any(t in texto for t in ("celulares", "smartphones", "telefonia")):
            return "Celulares"
        if any(t in texto for t in ("games", "video games", "consoles", "jogos para console")):
            return "Games"
        if any(t in texto for t in ("eletronicos", "informatica", "computadores", "audio", "cameras")):
            return "Tecnologia"
        if any(t in texto for t in ("casa", "moveis", "decoracao", "cozinha", "eletrodomesticos")):
            return "Casa"
        if any(t in texto for t in ("esportes", "fitness", "academia")):
            return "Esportes"
        return None
