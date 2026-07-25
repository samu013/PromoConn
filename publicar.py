from database.database import criar_tabelas
from services.publicador import publicar_proxima_promocao


def main():
    print("=" * 70)
    print("PROMOCONN - PUBLICAÇÃO AGENDADA")
    print("=" * 70)

    criar_tabelas()

    resultado = publicar_proxima_promocao()

    print()
    print("=" * 70)

    if resultado.get("sucesso"):
        print("✅ Publicação concluída.")
        print(
            "Grupo:",
            resultado.get(
                "telegram_canal",
                "-"
            )
        )

    elif resultado.get("fila_vazia"):
        print("📭 Nenhuma promoção pronta na fila.")

    else:
        print("❌ Não foi possível publicar.")
        print(
            resultado.get(
                "erro",
                "Erro desconhecido."
            )
        )

    print("=" * 70)


if __name__ == "__main__":
    main()