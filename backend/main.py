from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from core.config import settings
from core.database import ACTIVE_DATABASE_BACKEND, Base, SessionLocal, engine
from core.security import gerar_hash_senha
from core.sync_db import sincronizar_sqlite_para_mysql_se_vazio
from models.produto_model import Produto
from models.usuario_model import RefreshToken, Usuario  # noqa: F401 - garante registro das tabelas no metadata
from models.venda_model import ItemVenda, Venda  # noqa: F401 - garante registro das tabelas no metadata
from routers.auth_router import router as auth_router
from routers.insight_router import router as insight_router
from routers.produto_router import router as produto_router
from routers.venda_router import router as venda_router

PRODUTOS_INICIAIS = [
    {"nome": "Picanha Bovina Maturada", "categoria": "Carnes", "unidade": "kg", "preco": Decimal("89.90"), "quantidade_estoque": 18},
    {"nome": "Azeite de Oliva Extra Virgem 500ml", "categoria": "Mercearia", "unidade": "un", "preco": Decimal("48.50"), "quantidade_estoque": 25},
    {"nome": "Café Torrado e Moído Especial 500g", "categoria": "Bebidas", "unidade": "pct", "preco": Decimal("34.90"), "quantidade_estoque": 30},
    {"nome": "Arroz Branco Tipo 1 (5kg)", "categoria": "Grãos", "unidade": "pct", "preco": Decimal("29.90"), "quantidade_estoque": 40},
    {"nome": "Feijão Carioca Selecionado 1kg", "categoria": "Grãos", "unidade": "pct", "preco": Decimal("8.90"), "quantidade_estoque": 50},
    {"nome": "Lava-Roupas Líquido Concentrado 3L", "categoria": "Limpeza", "unidade": "un", "preco": Decimal("42.00"), "quantidade_estoque": 20},
    {"nome": "Queijo Mussarela Fatiado 500g", "categoria": "Laticínios", "unidade": "band", "preco": Decimal("27.50"), "quantidade_estoque": 22},
    {"nome": "Filé de Salmão Fresco", "categoria": "Peixaria", "unidade": "kg", "preco": Decimal("74.90"), "quantidade_estoque": 12},
    {"nome": "Leite UHT Integral 1L", "categoria": "Laticínios", "unidade": "cx", "preco": Decimal("5.80"), "quantidade_estoque": 60},
    {"nome": "Chocolate Meio Amargo 40% Cacau 170g", "categoria": "Bomboniere", "unidade": "un", "preco": Decimal("14.50"), "quantidade_estoque": 35},
]


def seed_produtos_iniciais():
    """Popula o catálogo inicial apenas se a tabela de produtos estiver vazia."""
    with SessionLocal() as db:
        if db.query(Produto).count() == 0:
            try:
                db.add_all(Produto(**item) for item in PRODUTOS_INICIAIS)
                db.commit()
            except IntegrityError:
                db.rollback()


def seed_usuarios_iniciais():
    """Garante os perfis padrão de demonstração (gerente e cliente) se não houver usuários."""
    with SessionLocal() as db:
        if db.query(Usuario).count() == 0:
            try:
                db.add_all(
                    [
                        Usuario(
                            nome="Gerente do Mercado",
                            login="gerente",
                            senha_hash=gerar_hash_senha("gerente123"),
                            perfil="gerente",
                        ),
                        Usuario(
                            nome="Cliente Padrão",
                            login="cliente",
                            senha_hash=gerar_hash_senha("cliente123"),
                            perfil="cliente",
                        ),
                    ]
                )
                db.commit()
            except IntegrityError:
                db.rollback()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if ACTIVE_DATABASE_BACKEND == "mysql":
        sincronizar_sqlite_para_mysql_se_vazio(engine)
    seed_produtos_iniciais()
    seed_usuarios_iniciais()
    yield


app = FastAPI(
    title="Sistema de Supermercado — TDE Back-End",
    description="API REST para CRUD de produtos, controle de estoque e vendas com desconto progressivo.",
    version="1.0.0",
    lifespan=lifespan,
)

allowed_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(produto_router)
app.include_router(venda_router)
app.include_router(insight_router)


@app.get("/")
def home():
    return {
        "mensagem": "API do Supermercado TDE funcionando!",
        "banco": ACTIVE_DATABASE_BACKEND,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "banco": ACTIVE_DATABASE_BACKEND,
    }
