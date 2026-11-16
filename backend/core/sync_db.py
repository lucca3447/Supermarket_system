import argparse
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine

from core.database import ACTIVE_DATABASE_BACKEND, Base, engine

SQLITE_PADRAO_PATH = Path(__file__).resolve().parent.parent / "supermercado.db"


def banco_esta_vazio(target_engine: Engine) -> bool:
    """Retorna True se todas as tabelas mapeadas estiverem vazias no banco alvo."""
    with target_engine.connect() as conn:
        for tabela in Base.metadata.sorted_tables:
            if conn.execute(select(tabela).limit(1)).first() is not None:
                return False
    return True


def copiar_dados(
    origem_engine: Engine,
    destino_engine: Engine,
    limpar_destino: bool = False,
) -> dict[str, int]:
    """Copia todas as tabelas em ordem de dependência de chave estrangeira."""
    Base.metadata.create_all(bind=destino_engine)
    contagens: dict[str, int] = {}

    with origem_engine.connect() as orig_conn, destino_engine.begin() as dest_conn:
        if limpar_destino:
            for tabela in reversed(Base.metadata.sorted_tables):
                dest_conn.execute(tabela.delete())

        for tabela in Base.metadata.sorted_tables:
            linhas = [
                dict(row)
                for row in orig_conn.execute(select(tabela)).mappings().all()
            ]
            if linhas:
                dest_conn.execute(tabela.insert(), linhas)
            contagens[tabela.name] = len(linhas)

    return contagens


def sincronizar_sqlite_para_mysql_se_vazio(
    mysql_engine: Engine,
    sqlite_path: Path = SQLITE_PADRAO_PATH,
) -> dict[str, int] | None:
    """Migra dados do SQLite para o MySQL na inicialização apenas se o MySQL estiver vazio."""
    if not sqlite_path.exists() or not banco_esta_vazio(mysql_engine):
        return None

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    try:
        Base.metadata.create_all(bind=sqlite_engine)
        if banco_esta_vazio(sqlite_engine):
            return None
        contagens = copiar_dados(sqlite_engine, mysql_engine, limpar_destino=False)
        print(f"[SYNC] Dados migrados de {sqlite_path.name} para MySQL: {contagens}")
        return contagens
    finally:
        sqlite_engine.dispose()


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Sincroniza dados entre SQLite local e MySQL."
    )
    parser.add_argument(
        "--direcao",
        choices=["sqlite-para-mysql", "mysql-para-sqlite"],
        default="sqlite-para-mysql",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Limpa o banco de destino antes de copiar os registros.",
    )
    args = parser.parse_args()

    if ACTIVE_DATABASE_BACKEND != "mysql":
        raise SystemExit(
            "MySQL indisponível no momento. Ligue o MySQL/XAMPP antes de sincronizar."
        )
    if not SQLITE_PADRAO_PATH.exists() and args.direcao == "sqlite-para-mysql":
        raise SystemExit(f"Arquivo SQLite não encontrado: {SQLITE_PADRAO_PATH}")

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PADRAO_PATH}")
    try:
        if args.direcao == "sqlite-para-mysql":
            if not args.forcar and not banco_esta_vazio(engine):
                raise SystemExit(
                    "O MySQL já contém dados. Use --forcar para sobrescrever com o SQLite."
                )
            contagens = copiar_dados(sqlite_engine, engine, limpar_destino=args.forcar)
        else:
            if not args.forcar and not banco_esta_vazio(sqlite_engine):
                raise SystemExit(
                    "O SQLite já contém dados. Use --forcar para sobrescrever com o MySQL."
                )
            contagens = copiar_dados(engine, sqlite_engine, limpar_destino=args.forcar)
        print(f"[SYNC] Concluído ({args.direcao}): {contagens}")
    finally:
        sqlite_engine.dispose()


if __name__ == "__main__":
    _cli()
