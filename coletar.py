from database.database import criar_tabelas
from coletor_worker import executar_coleta


def main():
    print("=" * 70)
    print("PROMOCONN - COLETA AGENDADA")
    print("=" * 70)

    criar_tabelas()

    executar_coleta()

    print()
    print("=" * 70)
    print("COLETA FINALIZADA")
    print("=" * 70)


if __name__ == "__main__":
    main()