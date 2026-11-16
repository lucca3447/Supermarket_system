import json
import os
from datetime import datetime, timedelta, timezone

# Isola os testes do MySQL local antes de importar a aplicação
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-com-mais-de-32-chars")

import httpx
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import core.database as database_module
import main as main_module
import services.insight_service as insight_module
from core.config import settings
from core.database import Base, _attach_sqlite_pragma, get_db
from core.security import ALGORITHM, criar_access_token
from main import app, seed_produtos_iniciais, seed_usuarios_iniciais
from models.produto_model import Produto
from models.usuario_model import RefreshToken, Usuario
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
def raw_client(db_session_factory):
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


@pytest.fixture()
def client(raw_client, db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)
    seed_usuarios_iniciais()
    login_res = raw_client.post(
        "/auth/login",
        json={"login": "gerente", "senha": "gerente123"},
    )
    assert login_res.status_code == 200
    return raw_client


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

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"


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

    # List & Get by ID (com e sem barra final, sem redirect 307)
    list_res = client.get("/produtos/")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert client.get("/produtos", follow_redirects=False).status_code == 200
    assert client.get("/vendas", follow_redirects=False).status_code == 200

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
    urls_chamadas = []

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

    def fake_create_engine(url, *a, **kw):
        urls_chamadas.append(url)
        return _FakeEngine()

    monkeypatch.setattr(database_module, "create_engine", fake_create_engine)

    eng, backend = database_module._build_engine()
    assert backend == "mysql"
    assert isinstance(eng, _FakeEngine)
    assert urls_chamadas[0].database == ""
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


def test_insights_estoque_local_com_alertas_e_vendas(client, monkeypatch):
    monkeypatch.setattr(insight_module.settings, "GEMINI_API_KEY", "")

    p_esgotado = _criar_produto(client, nome="Café Esgotado", preco="30.00", estoque=0).json()
    p_baixo = _criar_produto(client, nome="Salmão Baixo", preco="75.00", estoque=4).json()
    p_vendido = _criar_produto(client, nome="Picanha Premium", preco="120.00", estoque=2).json()
    _criar_produto(client, nome="Arroz Parado 5kg", preco="28.00", estoque=20)

    # Venda acima de R$ 200 (ativa 5% OFF) e esgota Picanha ou deixa baixa
    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p_vendido["id_produto"], "quantidade": 2}]},
    )
    assert venda_res.status_code == 201

    # Exclui o produto vendido para garantir que itens_venda com id_produto=NULL sejam tratados
    del_res = client.delete(f"/produtos/{p_vendido['id_produto']}")
    assert del_res.status_code == 200

    # Vende 1 unidade de produto ainda existente para cobrir demanda com id_produto ativo
    p_ativo = _criar_produto(client, nome="Feijão Carioca", preco="9.00", estoque=5).json()
    client.post("/vendas/", json={"itens": [{"id_produto": p_ativo["id_produto"], "quantidade": 1}]})

    res = client.get("/insights/estoque")
    assert res.status_code == 200
    body = res.json()

    assert body["origem"] == "analise_local"
    assert body["modelo"] is None
    assert body["metricas"]["total_produtos"] == 4
    assert body["metricas"]["itens_criticos"] == 1
    assert body["metricas"]["itens_atencao"] == 2
    assert body["metricas"]["total_vendas"] == 2
    assert body["metricas"]["vendas_com_desconto"] == 1
    assert body["metricas"]["faturamento_total"] == "237.00"

    alertas = body["alertas"]
    assert [a["id_produto"] for a in alertas] == [
        p_esgotado["id_produto"],
        p_ativo["id_produto"],
        p_baixo["id_produto"],
    ]
    assert alertas[0]["nivel"] == "critico"
    assert alertas[1]["nivel"] == "atencao"
    assert len(body["recomendacoes"]) == 3
    assert "Arroz Parado 5kg" in body["recomendacoes"][2]


def test_insights_estoque_local_saudavel_sem_alertas_ou_parados(client, monkeypatch):
    monkeypatch.setattr(insight_module.settings, "GEMINI_API_KEY", "")

    p1 = _criar_produto(client, nome="Leite Integral", preco="6.00", estoque=10).json()
    # Vende 1 unidade para tirar de "sem_giro" mantendo estoque >= 6
    client.post("/vendas/", json={"itens": [{"id_produto": p1["id_produto"], "quantidade": 1}]})

    res = client.get("/insights/estoque")
    assert res.status_code == 200
    body = res.json()
    assert body["origem"] == "analise_local"
    assert body["alertas"] == []
    assert "Estoque saudável" in body["resumo_executivo"]
    assert "Conversão da regra de desconto" in body["recomendacoes"][2]

    # Também cobre cenário sem nenhuma venda e sem produtos parados
    p_novo = _criar_produto(client, nome="Azeite", preco="40.00", estoque=8).json()
    assert p_novo["id_produto"] > 0


def test_insights_estoque_local_sem_vendas(client, monkeypatch):
    monkeypatch.setattr(insight_module.settings, "GEMINI_API_KEY", "")
    _criar_produto(client, nome="Azeite", preco="40.00", estoque=8)

    res = client.get("/insights/estoque")
    assert res.status_code == 200
    body = res.json()
    assert body["origem"] == "analise_local"
    assert any("Registre novas vendas" in rec for rec in body["recomendacoes"])


def test_insights_estoque_gemini_sucesso(client, monkeypatch):
    monkeypatch.setattr(insight_module.settings, "GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setattr(insight_module.settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
    _criar_produto(client, nome="Café Especial", preco="35.00", estoque=0)

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "resumo_executivo": "Há 1 item crítico exigindo reposição imediata.",
                                            "recomendacoes": [
                                                "Repor Café Especial hoje.",
                                                "Criar combo acima de R$ 200,00.",
                                            ],
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(insight_module.httpx, "post", fake_post)

    res = client.get("/insights/estoque")
    assert res.status_code == 200
    body = res.json()
    assert body["origem"] == "gemini"
    assert body["modelo"] == "gemini-3.1-flash-lite"
    assert body["resumo_executivo"] == "Há 1 item crítico exigindo reposição imediata."
    assert len(body["recomendacoes"]) == 2
    assert "gemini-3.1-flash-lite:generateContent" in captured["url"]
    assert captured["headers"] == {"x-goog-api-key": "fake-gemini-key"}


def test_insights_estoque_gemini_fallback_em_falhas(client, monkeypatch):
    monkeypatch.setattr(insight_module.settings, "GEMINI_API_KEY", "fake-gemini-key")
    _criar_produto(client, nome="Café Especial", preco="35.00", estoque=2)

    # 1. Timeout na chamada HTTP
    def fake_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(insight_module.httpx, "post", fake_timeout)
    res_timeout = client.get("/insights/estoque")
    assert res_timeout.status_code == 200
    assert res_timeout.json()["origem"] == "analise_local"

    # 2. JSON sem resumo ou recomendações válidas
    class _InvalidPayloadResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps({"resumo_executivo": "", "recomendacoes": []})}]
                        }
                    }
                ]
            }

    monkeypatch.setattr(insight_module.httpx, "post", lambda *a, **kw: _InvalidPayloadResponse())
    res_invalid = client.get("/insights/estoque")
    assert res_invalid.status_code == 200
    assert res_invalid.json()["origem"] == "analise_local"

    # 3. Lista de recomendações só com strings vazias
    class _BlankRecsResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "resumo_executivo": "Resumo válido",
                                            "recomendacoes": ["   ", ""],
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    monkeypatch.setattr(insight_module.httpx, "post", lambda *a, **kw: _BlankRecsResponse())
    res_blank = client.get("/insights/estoque")
    assert res_blank.status_code == 200
    assert res_blank.json()["origem"] == "analise_local"


def test_seed_usuarios_iniciais_idempotente(db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)

    seed_usuarios_iniciais()
    with db_session_factory() as db:
        assert db.query(Usuario).count() == 2

    seed_usuarios_iniciais()
    with db_session_factory() as db:
        assert db.query(Usuario).count() == 2


def test_auth_login_cookies_httponly_refresh_e_logout(raw_client, db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)
    seed_usuarios_iniciais()

    # Sem autenticação: 401 nas rotas privadas e em /auth/me e /auth/refresh
    assert raw_client.get("/auth/me").status_code == 401
    assert raw_client.get("/produtos/").status_code == 401
    assert raw_client.post("/auth/refresh").status_code == 401

    # Login inválido: 401
    bad_login = raw_client.post("/auth/login", json={"login": "gerente", "senha": "errada"})
    assert bad_login.status_code == 401

    # Login válido define cookies HttpOnly access_token e refresh_token
    ok_login = raw_client.post("/auth/login", json={"login": "gerente", "senha": "gerente123"})
    assert ok_login.status_code == 200
    body = ok_login.json()
    assert body["usuario"]["perfil"] == "gerente"
    set_cookie_headers = ok_login.headers.get_list("set-cookie")
    assert any("access_token=" in h and "HttpOnly" in h for h in set_cookie_headers)
    assert any("refresh_token=" in h and "HttpOnly" in h for h in set_cookie_headers)

    # /auth/me autenticado por cookie
    me_res = raw_client.get("/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["login"] == "gerente"

    # /auth/refresh rotaciona o refresh token no banco
    with db_session_factory() as db:
        assert db.query(RefreshToken).filter_by(revoked=False).count() == 1

    refresh_res = raw_client.post("/auth/refresh")
    assert refresh_res.status_code == 200
    with db_session_factory() as db:
        assert db.query(RefreshToken).filter_by(revoked=True).count() == 1
        assert db.query(RefreshToken).filter_by(revoked=False).count() == 1

    # Logout revoga o refresh token ativo e limpa os cookies
    logout_res = raw_client.post("/auth/logout")
    assert logout_res.status_code == 200
    with db_session_factory() as db:
        assert db.query(RefreshToken).filter_by(revoked=False).count() == 0

    # Logout sem cookie continua seguro (no-op)
    assert raw_client.post("/auth/logout").status_code == 200

    # Após logout, /auth/me falha com 401
    assert raw_client.get("/auth/me").status_code == 401


def test_auth_registro_duplicado_e_rbac_cliente_vs_gerente(raw_client, db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)
    seed_usuarios_iniciais()

    # Cria um produto autenticado como gerente via Bearer (para validar fallback HTTPBearer)
    gerente_login = raw_client.post(
        "/auth/login", json={"login": "gerente", "senha": "gerente123"}
    ).json()
    raw_client.cookies.clear()
    gerente_headers = {"Authorization": f"Bearer {gerente_login['access_token']}"}

    produto = raw_client.post(
        "/produtos/",
        headers=gerente_headers,
        json={
            "nome": "Queijo Minas",
            "categoria": "Laticínios",
            "unidade": "un",
            "preco": "25.00",
            "quantidade_estoque": 10,
        },
    ).json()

    # Registro de novo cliente via /auth/registrar
    reg_res = raw_client.post(
        "/auth/registrar",
        json={"nome": "Maria Silva", "login": "maria", "senha": "maria123"},
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["usuario"]["perfil"] == "cliente"

    # Login duplicado retorna 409 Conflict
    dup_res = raw_client.post(
        "/auth/registrar",
        json={"nome": "Outra Maria", "login": "maria", "senha": "maria123"},
    )
    assert dup_res.status_code == 409

    # Cliente pode listar produtos e finalizar compra, mas recebe 403 nas rotas de gerente
    assert raw_client.get("/produtos/").status_code == 200
    assert raw_client.get(f"/produtos/{produto['id_produto']}").status_code == 200
    assert (
        raw_client.post(
            "/vendas/",
            json={"itens": [{"id_produto": produto["id_produto"], "quantidade": 1}]},
        ).status_code
        == 201
    )

    assert raw_client.post("/produtos/", json={"nome": "X", "preco": "1.00", "quantidade_estoque": 1}).status_code == 403
    assert raw_client.put(f"/produtos/{produto['id_produto']}", json={"nome": "X", "categoria": "G", "unidade": "un", "preco": "1.00", "quantidade_estoque": 1}).status_code == 403
    assert raw_client.delete(f"/produtos/{produto['id_produto']}").status_code == 403
    assert raw_client.get("/vendas/").status_code == 403
    assert raw_client.get("/insights/estoque").status_code == 403


def test_auth_tokens_invalidos_expirados_e_usuario_removido(raw_client, db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)
    seed_usuarios_iniciais()

    # Token malformado
    assert (
        raw_client.get("/auth/me", headers={"Authorization": "Bearer token-invalido"}).status_code
        == 401
    )

    # Token expirado
    token_expirado = criar_access_token(1, "gerente", expires_delta=timedelta(seconds=-5))
    assert (
        raw_client.get("/auth/me", headers={"Authorization": f"Bearer {token_expirado}"}).status_code
        == 401
    )

    # Token com sub não numérico
    token_sub_invalido = jwt.encode(
        {
            "sub": "abc",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    assert (
        raw_client.get("/auth/me", headers={"Authorization": f"Bearer {token_sub_invalido}"}).status_code
        == 401
    )

    # Token de usuário inexistente no banco
    token_fantasma = criar_access_token(99999, "gerente")
    assert (
        raw_client.get("/auth/me", headers={"Authorization": f"Bearer {token_fantasma}"}).status_code
        == 401
    )

    # Refresh token expirado ou com usuário inexistente
    raw_client.post("/auth/login", json={"login": "cliente", "senha": "cliente123"})
    with db_session_factory() as db:
        rt = db.query(RefreshToken).first()
        rt.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        db.commit()
    assert raw_client.post("/auth/refresh").status_code == 401

    # Refresh token válido apontando para usuário removido
    raw_client.post("/auth/login", json={"login": "cliente", "senha": "cliente123"})
    with db_session_factory() as db:
        from services.auth_service import AuthService

        svc = AuthService(db)
        rt = (
            db.query(RefreshToken)
            .filter_by(revoked=False)
            .order_by(RefreshToken.id_token.desc())
            .first()
        )
        monkeypatch.setattr(svc.repo, "buscar_refresh_por_hash", lambda _h: rt)
        monkeypatch.setattr(svc.repo, "buscar_por_id", lambda _id: None)
        with pytest.raises(Exception) as exc2:
            svc.rotacionar_refresh("qualquer-valor")
        assert exc2.value.status_code == 401


def test_venda_baixa_atomica_concorrente_e_rollback(client, monkeypatch):
    p1 = _criar_produto(client, nome="Produto A", preco="20.00", estoque=5).json()
    p2 = _criar_produto(client, nome="Produto B", preco="30.00", estoque=1).json()

    from repositories.produto_repository import ProdutoRepository

    original_baixar = ProdutoRepository.baixar_estoque_atomico

    def simular_concorrencia(self, id_produto, quantidade):
        if id_produto == p2["id_produto"]:
            return False
        return original_baixar(self, id_produto, quantidade)

    monkeypatch.setattr(ProdutoRepository, "baixar_estoque_atomico", simular_concorrencia)

    res = client.post(
        "/vendas/",
        json={
            "itens": [
                {"id_produto": p2["id_produto"], "quantidade": 1},
                {"id_produto": p1["id_produto"], "quantidade": 2},
            ]
        },
    )
    assert res.status_code == 400
    # Rollback garante que Produto A voltou para 5 unidades
    assert client.get(f"/produtos/{p1['id_produto']}").json()["quantidade_estoque"] == 5


def test_patch_ajuste_estoque_relativo_e_trava_zero(raw_client, db_session_factory, monkeypatch):
    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)
    seed_usuarios_iniciais()

    raw_client.post("/auth/login", json={"login": "gerente", "senha": "gerente123"})
    p = _criar_produto(raw_client, nome="Café", preco="25.00", estoque=5).json()

    res_mais = raw_client.patch(f"/produtos/{p['id_produto']}/estoque", json={"delta": 10})
    assert res_mais.status_code == 200
    assert res_mais.json()["quantidade_estoque"] == 15

    res_trava = raw_client.patch(f"/produtos/{p['id_produto']}/estoque", json={"delta": -50})
    assert res_trava.status_code == 200
    assert res_trava.json()["quantidade_estoque"] == 0

    assert raw_client.patch("/produtos/9999/estoque", json={"delta": 1}).status_code == 404

    # Cliente não pode ajustar estoque
    raw_client.post("/auth/login", json={"login": "cliente", "senha": "cliente123"})
    assert raw_client.patch(f"/produtos/{p['id_produto']}/estoque", json={"delta": 1}).status_code == 403


def test_validacoes_secret_key_senha_72_bytes_e_produto_limites(client):
    from core.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(SECRET_KEY="tde-supermercado-dev-secret")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(SECRET_KEY="curta")

    # Senhas > 72 bytes UTF-8 retornam 422 em vez de 500 no bcrypt
    assert client.post("/auth/login", json={"login": "gerente", "senha": "a" * 73}).status_code == 422
    assert (
        client.post(
            "/auth/registrar",
            json={"nome": "Teste", "login": "teste72", "senha": "é" * 40},
        ).status_code
        == 422
    )

    # Preço Infinity, > 2 casas decimais e estoque acima de INT32 retornam 422
    assert _criar_produto(client, nome="Inf", preco="Infinity", estoque=1).status_code == 422
    assert _criar_produto(client, nome="Tres Decimais", preco="10.005", estoque=1).status_code == 422
    assert _criar_produto(client, nome="Estoque Gigante", preco="10.00", estoque=2_147_483_648).status_code == 422


def test_auth_registro_integrity_error_e_refresh_concorrente(db_session_factory, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from schemas.auth_schema import RegistroRequest
    from services.auth_service import AuthService

    monkeypatch.setattr(main_module, "SessionLocal", db_session_factory)
    seed_usuarios_iniciais()

    with db_session_factory() as db:
        svc = AuthService(db)
        monkeypatch.setattr(svc.repo, "buscar_por_login", lambda _login: None)

        def fake_criar(_usuario):
            raise IntegrityError("INSERT", {}, Exception("duplicate"))

        monkeypatch.setattr(svc.repo, "criar", fake_criar)
        with pytest.raises(Exception) as exc:
            svc.registrar_cliente(RegistroRequest(nome="Novo", login="gerente", senha="abcd"))
        assert exc.value.status_code == 409

    with db_session_factory() as db:
        svc = AuthService(db)
        _, raw_refresh, _ = svc._emitir_par_tokens(db.query(Usuario).first())
        monkeypatch.setattr(svc.repo, "revogar_refresh_se_ativo", lambda _id: False)
        with pytest.raises(Exception) as exc_refresh:
            svc.rotacionar_refresh(raw_refresh)
        assert exc_refresh.value.status_code == 401


def test_insights_janela_30_dias_utc_e_paginacao_vendas(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(insight_module.settings, "GEMINI_API_KEY", "")
    p = _criar_produto(client, nome="Leite 1L", preco="10.00", estoque=10).json()

    # Insere venda antiga (35 dias atrás) que não deve inflar demanda recente
    from models.venda_model import ItemVenda

    with db_session_factory() as db:
        venda_antiga = Venda(
            data_hora=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=35),
            valor_bruto=500,
            desconto_aplicado=25,
            valor_final=475,
            teve_desconto=True,
            itens=[
                ItemVenda(
                    id_produto=p["id_produto"],
                    nome_produto="Leite 1L",
                    preco_unitario=10,
                    quantidade=50,
                    subtotal=500,
                )
            ],
        )
        db.add(venda_antiga)
        db.commit()

    # Cria 2 vendas recentes para testar paginação e sufixo UTC
    client.post("/vendas/", json={"itens": [{"id_produto": p["id_produto"], "quantidade": 1}]})
    client.post("/vendas/", json={"itens": [{"id_produto": p["id_produto"], "quantidade": 1}]})

    insights = client.get("/insights/estoque").json()
    assert insights["alertas"] == []
    assert insights["metricas"]["total_vendas"] == 3

    paginado = client.get("/vendas/?limit=1&offset=1").json()
    assert len(paginado) == 1
    assert paginado[0]["data_hora"].endswith("Z")


def test_sync_db_migra_sqlite_para_destino_vazio_e_respeita_nao_vazio(tmp_path):
    from core.sync_db import copiar_dados, sincronizar_sqlite_para_mysql_se_vazio
    from models.venda_model import ItemVenda

    sqlite_file = tmp_path / "origem.db"
    origem_engine = create_engine(f"sqlite:///{sqlite_file}")
    destino_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _attach_sqlite_pragma(destino_engine)

    try:
        Base.metadata.create_all(bind=origem_engine)
        Base.metadata.create_all(bind=destino_engine)

        OrigemSession = sessionmaker(bind=origem_engine)
        DestinoSession = sessionmaker(bind=destino_engine)

        with OrigemSession() as db:
            db.add(
                Usuario(
                    nome="Gerente",
                    login="gerente",
                    senha_hash="hash",
                    perfil="gerente",
                )
            )
            prod = Produto(
                nome="Café Especial",
                categoria="Bebidas",
                unidade="pct",
                preco=35,
                quantidade_estoque=10,
            )
            db.add(prod)
            db.flush()
            db.add(
                Venda(
                    valor_bruto=35,
                    desconto_aplicado=0,
                    valor_final=35,
                    teve_desconto=False,
                    itens=[
                        ItemVenda(
                            id_produto=prod.id_produto,
                            nome_produto="Café Especial",
                            preco_unitario=35,
                            quantidade=1,
                            subtotal=35,
                        )
                    ],
                )
            )
            db.commit()

        # 1. Migra automaticamente quando o banco de destino está vazio
        contagens = sincronizar_sqlite_para_mysql_se_vazio(
            destino_engine, sqlite_path=sqlite_file
        )
        assert contagens is not None
        assert contagens["produtos"] == 1
        assert contagens["vendas"] == 1
        assert contagens["itens_venda"] == 1
        assert contagens["usuarios"] == 1

        with DestinoSession() as db:
            assert db.query(Produto).count() == 1
            assert db.query(Venda).count() == 1

        # 2. Se o destino já tem dados, não sobrescreve na inicialização
        assert (
            sincronizar_sqlite_para_mysql_se_vazio(
                destino_engine, sqlite_path=sqlite_file
            )
            is None
        )

        # 3. limpar_destino=True permite sobrescrever com segurança
        forcar = copiar_dados(origem_engine, destino_engine, limpar_destino=True)
        assert forcar["produtos"] == 1
    finally:
        origem_engine.dispose()
        destino_engine.dispose()


def test_database_postgresql_e_sync_sequences(monkeypatch):
    from core.sync_db import _sincronizar_sequences_postgres

    urls_chamadas = []

    def fake_create_engine(url, *args, **kwargs):
        urls_chamadas.append(url)
        return object()

    monkeypatch.setattr(
        database_module.settings,
        "DATABASE_URL",
        "postgres://user:pass@localhost:5432/supermercado_tde",
    )
    monkeypatch.setattr(database_module, "create_engine", fake_create_engine)

    _, backend = database_module._build_engine()
    assert backend == "postgresql"
    assert urls_chamadas[0].startswith("postgresql+psycopg://")

    # Valida que _sincronizar_sequences_postgres gera setval para todas as tabelas com PK única
    executados = []

    class _FakeConn:
        def execute(self, stmt, params=None):
            executados.append((str(stmt), params))

    _sincronizar_sequences_postgres(_FakeConn())
    tabelas_com_setval = {params["tabela"] for _, params in executados}
    assert {"produtos", "usuarios", "vendas", "itens_venda", "refresh_tokens"} <= tabelas_com_setval
