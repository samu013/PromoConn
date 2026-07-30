import time

from database.database import criar_tabelas
from database.oportunidades import salvar_oportunidade
from database.tendencias import desativar_todas, salvar_tendencia
from mercadolivre.categorias import CategoriasMercadoLivre
from mercadolivre.classificador import ClassificadorCategorias
from mercadolivre.highlights import Highlights
from mercadolivre.trends import Trends


INTERVALO_SEGUNDOS = 60 * 60

FONTES_DE_COLETA = {
    "Celulares": "MLB1055",
    "Games": "MLB1144",
    "Tecnologia": "MLB1648",
    "Casa": "MLB1574",
    "Esportes": "MLB264201",
    "Moda": "MLB1430",
}

EXPANDIR_SUBCATEGORIAS = True
MAX_SUBCATEGORIAS_POR_FONTE = 12


def coletar_tendencias():
    print("\n" + "=" * 70)
    print("COLETANDO TENDÊNCIAS")
    print("=" * 70)

    tendencias = Trends().buscar()
    if not tendencias:
        print("Nenhuma tendência retornada.")
        return 0

    desativar_todas()
    total_salvas = 0

    for posicao, tendencia in enumerate(tendencias, start=1):
        if isinstance(tendencia, str):
            palavra, url, posicao_api = tendencia, None, posicao
        elif isinstance(tendencia, dict):
            palavra = tendencia.get("keyword") or tendencia.get("palavra") or tendencia.get("name") or tendencia.get("query")
            url = tendencia.get("url")
            posicao_api = tendencia.get("position") or tendencia.get("posicao") or posicao
        else:
            continue

        if not palavra:
            continue

        salvar_tendencia(palavra=palavra, url=url, posicao=posicao_api)
        total_salvas += 1

    print(f"Tendências recebidas: {len(tendencias)}")
    print(f"Tendências salvas: {total_salvas}")
    return total_salvas


def montar_fontes_de_coleta(categorias_api, nome_fonte, categoria_id):
    fontes = [{"id": categoria_id, "nome": nome_fonte, "principal": True}]
    if not EXPANDIR_SUBCATEGORIAS:
        return fontes

    for filho in categorias_api.filhos(categoria_id)[:MAX_SUBCATEGORIAS_POR_FONTE]:
        fontes.append({
            "id": filho["id"],
            "nome": filho.get("name") or filho["id"],
            "principal": False,
        })
    return fontes


def processar_produtos(produtos, classificador):
    resultado = {
        "recebidos": len(produtos),
        "novos": 0,
        "existentes_ou_recentes": 0,
        "sem_categoria_id": 0,
        "fora_dos_grupos": 0,
        "erros": 0,
    }

    for produto in produtos:
        if not isinstance(produto, dict):
            resultado["fora_dos_grupos"] += 1
            continue

        ml_id = produto.get("id")
        tipo = produto.get("tipo")
        nome = produto.get("nome")
        categoria_id = produto.get("category_id")

        if not ml_id or not tipo or not nome:
            resultado["fora_dos_grupos"] += 1
            continue

        if not categoria_id:
            resultado["sem_categoria_id"] += 1
            continue

        categoria_grupo = classificador.classificar(categoria_id, nome)
        if not categoria_grupo:
            resultado["fora_dos_grupos"] += 1
            continue

        oportunidade = {
            "id": ml_id,
            "tipo": tipo,
            "nome": nome,
            "imagem": produto.get("imagem"),
            "ranking": produto.get("ranking"),
            "category_id": categoria_id,
        }

        try:
            novo = salvar_oportunidade(
                produto=oportunidade,
                fonte="highlights",
                categoria=categoria_grupo,
                origem="mercadolivre",
            )
            if novo:
                resultado["novos"] += 1
            else:
                resultado["existentes_ou_recentes"] += 1
        except Exception as erro:
            resultado["erros"] += 1
            print(f"    Erro ao salvar {ml_id}: {erro}")

    return resultado


def coletar_highlights():
    print("\n" + "=" * 70)
    print("COLETANDO HIGHLIGHTS")
    print("=" * 70)

    highlights = Highlights()
    categorias_api = CategoriasMercadoLivre(highlights.client)
    classificador = ClassificadorCategorias(categorias_api)

    totais = {
        "consultas": 0,
        "recebidos": 0,
        "novos": 0,
        "existentes_ou_recentes": 0,
        "sem_categoria_id": 0,
        "fora_dos_grupos": 0,
        "erros": 0,
    }

    for nome_fonte, categoria_id in FONTES_DE_COLETA.items():
        print("\n" + "#" * 70)
        print(f"FONTE: {nome_fonte}")
        print("#" * 70)

        fontes = montar_fontes_de_coleta(categorias_api, nome_fonte, categoria_id)

        for fonte in fontes:
            totais["consultas"] += 1
            tipo_fonte = "Principal" if fonte["principal"] else "Subcategoria"
            print(f"\n  [{tipo_fonte}] {fonte['nome']} ({fonte['id']})")

            try:
                produtos = highlights.buscar(fonte["id"])
            except Exception as erro:
                totais["erros"] += 1
                print(f"    Erro ao buscar: {erro}")
                continue

            if not produtos:
                print("    Nenhum produto retornado.")
                continue

            resumo = processar_produtos(produtos, classificador)
            for chave in (
                "recebidos", "novos", "existentes_ou_recentes",
                "sem_categoria_id", "fora_dos_grupos", "erros",
            ):
                totais[chave] += resumo[chave]

            print(f"    Recebidos: {resumo['recebidos']}")
            print(f"    Novos: {resumo['novos']}")
            print(f"    Já existentes/recentes: {resumo['existentes_ou_recentes']}")
            print(f"    Sem category_id: {resumo['sem_categoria_id']}")
            print(f"    Fora dos grupos: {resumo['fora_dos_grupos']}")
            if resumo["erros"]:
                print(f"    Erros: {resumo['erros']}")

    print("\n" + "=" * 70)
    print("RESUMO FINAL DOS HIGHLIGHTS")
    print("=" * 70)
    print(f"Consultas realizadas: {totais['consultas']}")
    print(f"Produtos recebidos: {totais['recebidos']}")
    print(f"Novas oportunidades: {totais['novos']}")
    print(f"Já existentes/recentes: {totais['existentes_ou_recentes']}")
    print(f"Sem category_id: {totais['sem_categoria_id']}")
    print(f"Fora dos grupos: {totais['fora_dos_grupos']}")
    print(f"Erros: {totais['erros']}")
    return totais["novos"]


def executar_coleta():
    print("\n" + "=" * 70)
    print("PROMOCONN - COLETA AUTOMÁTICA")
    print("=" * 70)

    try:
        coletar_tendencias()
    except Exception as erro:
        print("Erro geral nas tendências:")
        print(erro)

    try:
        coletar_highlights()
    except Exception as erro:
        print("Erro geral nos highlights:")
        print(erro)


def executar_worker():
    criar_tabelas()
    print("\n" + "=" * 70)
    print("PROMOCONN COLETOR WORKER")
    print("=" * 70)
    print("Intervalo de coleta: 1 hora")
    print("Classificação: categorias oficiais do Mercado Livre")

    while True:
        try:
            executar_coleta()
        except Exception as erro:
            print("\nErro inesperado no ciclo:")
            print(erro)

        print("\nPróxima coleta em 1 hora.\n")
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    executar_worker()
