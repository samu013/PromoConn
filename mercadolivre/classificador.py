import re
import unicodedata


class ClassificadorCategorias:
    IDS_PRINCIPAIS = {
        "MLB1055": "Celulares",
        "MLB1144": "Games",
        "MLB1648": "Tecnologia",
        "MLB1574": "Casa",
        "MLB264201": "Esportes",
        "MLB1246": "Beleza e Cuidados",
    }

    TERMOS_FEMININOS = {
        "feminino", "feminina", "mulher", "mulheres", "vestido", "vestidos",
        "saia", "saias", "sutia", "calcinha", "lingerie", "legging", "leggings",
        "blusa", "blusas",
    }
    TERMOS_MASCULINOS = {
        "masculino", "masculina", "homem", "homens", "cueca", "cuecas",
        "gravata", "terno", "ternos", "camisa masculina", "bermuda masculina",
    }

    def __init__(self, categorias):
        self.categorias = categorias

    @staticmethod
    def normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto or "").lower().strip())
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = re.sub(r"[^a-z0-9]+", " ", texto)
        return " ".join(texto.split())

    @staticmethod
    def _tem_termo(texto, termos):
        return any(termo in texto for termo in termos)

    def _classificar_moda(self, caminho_texto, titulo):
        oficial = self.normalizar(caminho_texto)
        titulo = self.normalizar(titulo)

        feminino_oficial = any(t in oficial for t in ("feminina", "feminino", "mulher", "mulheres"))
        masculino_oficial = any(t in oficial for t in ("masculina", "masculino", "homem", "homens"))

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
        caminho = self.categorias.caminho(categoria_id)
        if not caminho:
            return None

        ids = {str(item.get("id")) for item in caminho if item.get("id")}
        nomes = " | ".join(str(item.get("name") or "") for item in caminho)
        texto = self.normalizar(nomes)

        for categoria_raiz, grupo in self.IDS_PRINCIPAIS.items():
            if categoria_raiz in ids:
                return grupo

        if any(t in texto for t in ("roupas", "calcados", "bolsas", "moda", "acessorios de moda")):
            return self._classificar_moda(nomes, titulo)

        regras = (
            (("beleza", "cuidados pessoais", "maquiagem", "perfumes", "perfumaria", "cabelo", "pele", "higiene pessoal", "barbear", "unhas"), "Beleza e Cuidados"),
            (("celulares", "smartphones", "telefonia"), "Celulares"),
            (("games", "video games", "consoles", "jogos para console"), "Games"),
            (("eletronicos", "informatica", "computadores", "audio", "cameras"), "Tecnologia"),
            (("casa", "moveis", "decoracao", "cozinha", "eletrodomesticos"), "Casa"),
            (("esportes", "fitness", "academia"), "Esportes"),
        )

        for termos, grupo in regras:
            if any(termo in texto for termo in termos):
                return grupo

        return None
