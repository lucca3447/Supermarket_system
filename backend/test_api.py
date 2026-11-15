import os

# Isola os testes do MySQL local antes de importar a aplicação
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import core.database as database_module
import main as main_module
from core.database import Base, _attach_sqlite_pragma, get_db
from main import app, seed_produtos_iniciais
from models.produto_model import Produto
from models.venda_model import Venda
from repositories.venda_repository import VendaRepository


@pytest.fixture()
def db_session_factory():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _attach_sqlite_pragma(test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield TestingSessionLocal

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def client(db_session_factory):
    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _criar_produto(client, nome="Produto Teste", preco="50.00", estoque=10, categoria="Mercearia", unidade="un"):
    return client.post(
        "/produtos/",
        json={
            "nome": nome,
            "categoria": categoria,
            "unidade": unidade,
            "preco": preco,
            "quantidade_estoque": estoque,
        },
    )


def test_home_status(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert "mensagem" in body
    assert body["banco"] in {"mysql", "sqlite", "sqlite-memory"}


def test_seed_produtos_iniciais_idempotente(db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)

    seed_produtos_iniciais()
    with db_session_factory() as db:
        assert db.query(Produto).count() == 10

    # Segunda chamada não duplica os produtos
    seed_produtos_iniciais()
    with db_session_factory() as db:
        assert db.query(Produto).count() == 10


def test_crud_produtos_completo_e_erros_404(client):
    create_res = _criar_produto(
        client,
        nome="  Macarrão Espaguete 500g  ",
        categoria="Massas",
        unidade="pct",
        preco="6.50",
        estoque=25,
    )
    assert create_res.status_code == 201
    produto = create_res.json()
    assert produto["nome"] == "Macarrão Espaguete 500g"
    assert produto["quantidade_estoque"] == 25
    id_produto = produto["id_produto"]

    # List & Get by ID
    list_res = client.get("/produtos/")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    get_res = client.get(f"/produtos/{id_produto}")
    assert get_res.status_code == 200
    assert get_res.json()["id_produto"] == id_produto

    # Update
    update_res = client.put(
        f"/produtos/{id_produto}",
        json={
            "nome": "Macarrão Espaguete Grano Duro 500g",
            "categoria": "Massas",
            "unidade": "pct",
            "preco": "9.90",
            "quantidade_estoque": 30,
        },
    )
    assert update_res.status_code == 200
    assert float(update_res.json()["preco"]) == 9.90
    assert update_res.json()["quantidade_estoque"] == 30

    # Delete
    delete_res = client.delete(f"/produtos/{id_produto}")
    assert delete_res.status_code == 200
    assert delete_res.json()["id_produto"] == id_produto

    # 404 para produto inexistente em GET, PUT e DELETE
    assert client.get(f"/produtos/{id_produto}").status_code == 404
    assert client.put(
        "/produtos/9999",
        json={
            "nome": "Inexistente",
            "categoria": "Geral",
            "unidade": "un",
            "preco": "10.00",
            "quantidade_estoque": 1,
        },
    ).status_code == 404
    assert client.delete("/produtos/9999").status_code == 404


def test_validacoes_schema_produto_e_venda_422(client):
    assert _criar_produto(client, nome="   ", preco="10.00", estoque=5).status_code == 422
    assert _criar_produto(client, nome="Válido", preco="0", estoque=5).status_code == 422
    assert _criar_produto(client, nome="Válido", preco="-5.00", estoque=5).status_code == 422
    assert _criar_produto(client, nome="Válido", preco="10.00", estoque=-1).status_code == 422

    assert client.post("/vendas/", json={"itens": []}).status_code == 422
    assert client.post("/vendas/", json={"itens": [{"id_produto": 1, "quantidade": 0}]}).status_code == 422


def test_venda_ate_200_sem_desconto_e_baixa_estoque(client):
    p = _criar_produto(client, nome="Cesta Básica Padrão", preco="100.00", estoque=10).json()

    # Compra exata de R$ 200,00 NÃO recebe desconto (regra exige superior a R$ 200,00)
    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p["id_produto"], "quantidade": 2}]},
    )
    assert venda_res.status_code == 201
    venda = venda_res.json()
    assert float(venda["valor_bruto"]) == 200.00
    assert float(venda["desconto_aplicado"]) == 0.00
    assert float(venda["valor_final"]) == 200.00
    assert venda["teve_desconto"] is False

    produto_atualizado = client.get(f"/produtos/{p['id_produto']}").json()
    assert produto_atualizado["quantidade_estoque"] == 8


def test_venda_200_e_um_centavo_ativa_desconto(client):
    p = _criar_produto(client, nome="Kit Mercado", preco="200.01", estoque=3).json()

    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p["id_produto"], "quantidade": 1}]},
    )
    assert venda_res.status_code == 201
    venda = venda_res.json()
    assert float(venda["valor_bruto"]) == 200.01
    assert float(venda["desconto_aplicado"]) == 10.00
    assert float(venda["valor_final"]) == 190.01
    assert venda["teve_desconto"] is True


def test_venda_acima_de_200_aplica_5_porcento_desconto(client):
    p = _criar_produto(client, nome="Kit Churrasco Premium", categoria="Carnes", unidade="kit", preco="125.00", estoque=6).json()

    # Compra de R$ 250,00 -> 5% de desconto = R$ 12,50 -> valor final = R$ 237,50
    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p["id_produto"], "quantidade": 2}]},
    )
    assert venda_res.status_code == 201
    venda = venda_res.json()
    assert float(venda["valor_bruto"]) == 250.00
    assert float(venda["desconto_aplicado"]) == 12.50
    assert float(venda["valor_final"]) == 237.50
    assert venda["teve_desconto"] is True

    produto_atualizado = client.get(f"/produtos/{p['id_produto']}").json()
    assert produto_atualizado["quantidade_estoque"] == 4

    historico = client.get("/vendas/").json()
    assert len(historico) == 1
    assert historico[0]["id_venda"] == venda["id_venda"]


def test_venda_agrupa_itens_repetidos_no_mesmo_carrinho(client):
    p = _criar_produto(client, nome="Café 500g", preco="30.00", estoque=5).json()

    # Soma 2 + 3 = 5 unidades e dá baixa completa
    ok_res = client.post(
        "/vendas/",
        json={
            "itens": [
                {"id_produto": p["id_produto"], "quantidade": 2},
                {"id_produto": p["id_produto"], "quantidade": 3},
            ]
        },
    )
    assert ok_res.status_code == 201
    assert float(ok_res.json()["valor_bruto"]) == 150.00
    assert client.get(f"/produtos/{p['id_produto']}").json()["quantidade_estoque"] == 0

    # Novo item duplicado excedendo estoque deve falhar
    p2 = _criar_produto(client, nome="Azeite", preco="40.00", estoque=3).json()
    fail_res = client.post(
        "/vendas/",
        json={
            "itens": [
                {"id_produto": p2["id_produto"], "quantidade": 2},
                {"id_produto": p2["id_produto"], "quantidade": 2},
            ]
        },
    )
    assert fail_res.status_code == 400
    assert client.get(f"/produtos/{p2['id_produto']}").json()["quantidade_estoque"] == 3


def test_venda_produto_inexistente_retorna_404(client):
    res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": 9999, "quantidade": 1}]},
    )
    assert res.status_code == 404
    assert "não encontrado" in res.json()["detail"]


def test_venda_bloqueia_estoque_insuficiente(client):
    p = _criar_produto(client, nome="Azeite Especial", preco="50.00", estoque=3).json()

    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p["id_produto"], "quantidade": 5}]},
    )
    assert venda_res.status_code == 400
    assert "Estoque insuficiente" in venda_res.json()["detail"]

    produto_atualizado = client.get(f"/produtos/{p['id_produto']}").json()
    assert produto_atualizado["quantidade_estoque"] == 3


def test_deletar_produto_vendido_preserva_historico_venda(client):
    p = _criar_produto(client, nome="Salmão Fresco", preco="80.00", estoque=5).json()

    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p["id_produto"], "quantidade": 3}]},
    )
    assert venda_res.status_code == 201

    # Exclui produto que já participou de uma venda
    del_res = client.delete(f"/produtos/{p['id_produto']}")
    assert del_res.status_code == 200

    # Histórico mantém nome/preço do snapshot e marca id_produto=None via ON DELETE SET NULL
    historico = client.get("/vendas/").json()
    assert len(historico) == 1
    item = historico[0]["itens"][0]
    assert item["id_produto"] is None
    assert item["nome_produto"] == "Salmão Fresco"
    assert float(item["preco_unitario"]) == 80.00


def test_venda_repository_rollback_em_erro(db_session_factory, monkeypatch):
    with db_session_factory() as db:
        repo = VendaRepository(db)
        rollback_chamado = False

        def fake_commit():
            raise RuntimeError("Falha simulada no commit")

        def fake_rollback():
            nonlocal rollback_chamado
            rollback_chamado = True

        monkeypatch.setattr(db, "commit", fake_commit)
        monkeypatch.setattr(db, "rollback", fake_rollback)

        venda_invalida = Venda(
            valor_bruto=10,
            desconto_aplicado=0,
            valor_final=10,
            teve_desconto=False,
        )
        with pytest.raises(RuntimeError, match="Falha simulada"):
            repo.criar(venda_invalida)

        assert rollback_chamado is True


def test_database_build_engine_mysql_fallback_e_validacao(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    # Nome de banco MySQL inválido deve disparar ValueError
    monkeypatch.setattr(
        database_module.settings,
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost:3306/banco-invalido!",
    )
    with pytest.raises(ValueError, match="Nome de banco inválido"):
        database_module._build_engine()

    # Quando MySQL estiver indisponível (OperationalError), faz fallback para SQLite local
    monkeypatch.setattr(
        database_module.settings,
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost:3306/supermercado_tde",
    )
    original_create_engine = database_module.create_engine

    def fake_create_engine(url, *args, **kwargs):
        if str(url).startswith("mysql"):
            raise OperationalError("SELECT 1", {}, Exception("MySQL offline"))
        return original_create_engine(url, *args, **kwargs)

    monkeypatch.setattr(database_module, "create_engine", fake_create_engine)
    eng, backend = database_module._build_engine()
    try:
        assert backend == "sqlite"
    finally:
        eng.dispose()


def test_database_build_engine_mysql_cria_schema_quando_disponivel(monkeypatch):
    sqls_executados = []

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt):
            sqls_executados.append(str(stmt))

    class _FakeEngine:
        def begin(self):
            return _FakeConn()

        def connect(self):
            return _FakeConn()

        def dispose(self):
            pass

    monkeypatch.setattr(
        database_module.settings,
        "DATABASE_URL",
        "mysql+pymysql://root:@localhost:3306/supermercado_tde",
    )
    monkeypatch.setattr(database_module, "create_engine", lambda *a, **kw: _FakeEngine())

    eng, backend = database_module._build_engine()
    assert backend == "mysql"
    assert isinstance(eng, _FakeEngine)
    assert any("CREATE DATABASE IF NOT EXISTS `supermercado_tde`" in sql for sql in sqls_executados)


def test_get_db_abre_e_fecha_sessao(db_session_factory, monkeypatch):
    monkeypatch.setattr(database_module, "SessionLocal", db_session_factory)
    gen = get_db()
    db = next(gen)
    fechada = False
    original_close = db.close

    def tracked_close():
        nonlocal fechada
        fechada = True
        original_close()

    monkeypatch.setattr(db, "close", tracked_close)
    with pytest.raises(StopIteration):
        next(gen)
    assert fechada is True
