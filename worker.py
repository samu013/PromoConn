import time

from database.database import criar_tabelas
from services.publicador import publicar_proxima_promocao


INTERVALO_SEGUNDOS = 5 * 60


def executar_worker():
    print("=" * 60)
    print("🤖 PROMOCONN WORKER")
    print("=" * 60)
    print("Intervalo: 5 minutos")
    print()

    criar_tabelas()

    while True:
        try:
            print("⏰ Verificando fila...")

            resultado = (
                publicar_proxima_promocao()
            )

            if resultado.get("sucesso"):
                print(
                    "✅ Promoção publicada com sucesso."
                )

            elif resultado.get("fila_vazia"):
                print(
                    "📭 Nenhuma promoção pronta na fila."
                )

            else:
                print(
                    "❌ Não foi possível publicar:"
                )

                print(
                    resultado.get(
                        "erro",
                        "Erro desconhecido."
                    )
                )

        except Exception as erro:
            print(
                "❌ Erro durante o ciclo do worker:"
            )

            print(erro)

        print()
        print(
            "⏳ Próxima verificação em 5 minutos."
        )
        print()

        time.sleep(
            INTERVALO_SEGUNDOS
        )


if __name__ == "__main__":
    executar_worker()