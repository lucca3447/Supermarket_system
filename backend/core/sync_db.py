import argparse
from pathlib import Path

from sqlalchemy import create_engine, select, text
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

        if destino_engine.dialect.name == "postgresql":
            _sincronizar_sequences_postgres(dest_conn)

    return contagens


def _sincronizar_sequences_postgres(dest_conn) -> None:
    """Atualiza as sequences SERIAL do PostgreSQL após inserção com IDs explícitos."""
    for tabela in Base.metadata.sorted_tables:
        pks = list(tabela.primary_key.columns)
        if len(pks) != 1:
            continue
        pk_col = pks[0].name
        dest_conn.execute(
            text(
                f"SELECT setval("
                f"pg_get_serial_sequence(:tabela, :pk), "
                f"COALESCE((SELECT MAX({pk_col}) FROM {tabela.name}), 1), "
                f"(SELECT MAX({pk_col}) IS NOT NULL FROM {tabela.name})"
                f")"
            ),
            {"tabela": tabela.name, "pk": pk_col},
        )


def sincronizar_sqlite_para_mysql_se_vazio(
    mysql_engine: Engine,
    sqlite_path: Path = SQLITE_PADRAO_PATH,
) -> dict[str, int] | None:
    """Migra dados do SQLite para MySQL/PostgreSQL na inicialização apenas se o destino estiver vazio."""
    if not sqlite_path.exists() or not banco_esta_vazio(mysql_engine):
        return None

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    try:
        Base.metadata.create_all(bind=sqlite_engine)
        if banco_esta_vazio(sqlite_engine):
            return None
        contagens = copiar_dados(sqlite_engine, mysql_engine, limpar_destino=False)
        print(
            f"[SYNC] Dados migrados de {sqlite_path.name} para {mysql_engine.dialect.name}: {contagens}"
        )
        return contagens
    finally:
        sqlite_engine.dispose()


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Sincroniza dados entre SQLite local e MySQL/PostgreSQL."
    )
    parser.add_argument(
        "--direcao",
        choices=["sqlite-para-remoto", "remoto-para-sqlite", "sqlite-para-mysql", "mysql-para-sqlite"],
        default="sqlite-para-remoto",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Limpa o banco de destino antes de copiar os registros.",
    )
    args = parser.parse_args()

    if ACTIVE_DATABASE_BACKEND not in {"mysql", "postgresql"}:
        raise SystemExit(
            "MySQL/PostgreSQL indisponível no momento. Configure DATABASE_URL antes de sincronizar."
        )
    para_remoto = args.direcao in {"sqlite-para-remoto", "sqlite-para-mysql"}
    if not SQLITE_PADRAO_PATH.exists() and para_remoto:
        raise SystemExit(f"Arquivo SQLite não encontrado: {SQLITE_PADRAO_PATH}")

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PADRAO_PATH}")
    try:
        if para_remoto:
            if not args.forcar and not banco_esta_vazio(engine):
                raise SystemExit(
                    f"O {ACTIVE_DATABASE_BACKEND} já contém dados. Use --forcar para sobrescrever com o SQLite."
                )
            contagens = copiar_dados(sqlite_engine, engine, limpar_destino=args.forcar)
        else:
            if not args.forcar and not banco_esta_vazio(sqlite_engine):
                raise SystemExit(
                    f"O SQLite já contém dados. Use --forcar para sobrescrever com o {ACTIVE_DATABASE_BACKEND}."
                )
            contagens = copiar_dados(engine, sqlite_engine, limpar_destino=args.forcar)
        print(f"[SYNC] Concluído ({args.direcao}): {contagens}")
    finally:
        sqlite_engine.dispose()


if __name__ == "__main__":
    _cli()
