import re
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import settings


def _attach_sqlite_pragma(eng):
    """Ativa foreign keys no SQLite para respeitar ON DELETE SET NULL/CASCADE como no MySQL."""
    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    return eng


def _build_engine():
    """Cria a engine SQLAlchemy garantindo o schema no MySQL, com fallback para SQLite se o MySQL estiver parado."""
    url_str = settings.DATABASE_URL

    if url_str.startswith("mysql"):
        try:
            url = make_url(url_str)
            db_name = url.database
            if db_name:
                if not re.fullmatch(r"[A-Za-z0-9_]+", db_name):
                    raise ValueError(f"Nome de banco inválido: {db_name}")
                root_engine = create_engine(
                    url.set(database=""),
                    connect_args={"connect_timeout": 2},
                )
                with root_engine.begin() as conn:
                    conn.execute(
                        text(
                            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                        )
                    )
                root_engine.dispose()

            mysql_engine = create_engine(url_str, pool_pre_ping=True)
            with mysql_engine.connect():
                pass
            return mysql_engine, "mysql"
        except OperationalError as exc:
            # shortcut: fallback para SQLite garante que o app rode mesmo com MySQL/XAMPP desligado
            print(f"[AVISO] MySQL indisponível ({exc}). Usando SQLite local (supermercado.db).")
            url_str = "sqlite:///./supermercado.db"

    if url_str == "sqlite:///:memory:":
        mem_engine = create_engine(
            url_str,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        return _attach_sqlite_pragma(mem_engine), "sqlite-memory"

    connect_args = {"check_same_thread": False} if url_str.startswith("sqlite") else {}
    eng = create_engine(url_str, connect_args=connect_args, pool_pre_ping=True)
    if url_str.startswith("sqlite"):
        _attach_sqlite_pragma(eng)
    return eng, "sqlite"


engine, ACTIVE_DATABASE_BACKEND = _build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """Fornece uma sessão de banco por requisição e garante o fechamento ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
