import threading
import time

from services.publicador import (
    publicar_proxima_promocao,
)


INTERVALO_SEGUNDOS = 5 * 60

_agendador_iniciado = False
_lock_publicacao = threading.Lock()


def executar_ciclo():
    """
    Executa um ciclo do publicador.

    A trava impede duas publicações ao mesmo tempo.
    """

    if not _lock_publicacao.acquire(
        blocking=False
    ):
        print(
            "⚠️ Publicador já está em execução."
        )
        return

    try:
        print()
        print("=" * 60)
        print("⏰ VERIFICANDO FILA DE PUBLICAÇÃO")
        print("=" * 60)

        resultado = (
            publicar_proxima_promocao()
        )

        if resultado.get("fila_vazia"):
            print(
                "📭 Nenhuma promoção pronta."
            )

        elif resultado.get("sucesso"):
            print(
                "✅ Publicação automática concluída."
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
            "❌ Erro no agendador:"
        )
        print(erro)

    finally:
        _lock_publicacao.release()


def loop_agendador():
    """
    Aguarda 5 minutos antes da primeira execução
    e continua verificando a fila a cada 5 minutos.
    """

    print(
        "⏰ Agendador iniciado."
    )

    print(
        "📤 Intervalo de publicação: "
        "5 minutos."
    )

    while True:

        time.sleep(
            INTERVALO_SEGUNDOS
        )

        executar_ciclo()


def iniciar_agendador():
    """
    Inicia o agendador somente uma vez.
    """

    global _agendador_iniciado

    if _agendador_iniciado:
        return

    _agendador_iniciado = True

    thread = threading.Thread(
        target=loop_agendador,
        daemon=True,
        name="PromoConnAgendador",
    )

    thread.start()