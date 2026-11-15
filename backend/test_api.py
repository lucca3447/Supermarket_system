import os

# Isola os testes do MySQL local antes de importar a aplicação
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from main import app


@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_crud_produtos(client):
    # Create
    create_res = client.post(
        "/produtos/",
        json={
            "nome": "Macarrão Espaguete 500g",
            "categoria": "Massas",
            "unidade": "pct",
            "preco": "6.50",
            "quantidade_estoque": 25,
        },
    )
    assert create_res.status_code == 201
    produto = create_res.json()
    assert produto["nome"] == "Macarrão Espaguete 500g"
    assert produto["quantidade_estoque"] == 25

    id_produto = produto["id_produto"]

    # Read
    list_res = client.get("/produtos/")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

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
    assert client.get(f"/produtos/{id_produto}").status_code == 404


def test_venda_ate_200_sem_desconto_e_baixa_estoque(client):
    p = client.post(
        "/produtos/",
        json={
            "nome": "Cesta Básica Padrão",
            "categoria": "Mercearia",
            "unidade": "un",
            "preco": "100.00",
            "quantidade_estoque": 10,
        },
    ).json()

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

    # Estoque deve ter baixado de 10 para 8
    produto_atualizado = client.get(f"/produtos/{p['id_produto']}").json()
    assert produto_atualizado["quantidade_estoque"] == 8


def test_venda_acima_de_200_aplica_5_porcento_desconto(client):
    p = client.post(
        "/produtos/",
        json={
            "nome": "Kit Churrasco Premium",
            "categoria": "Carnes",
            "unidade": "kit",
            "preco": "125.00",
            "quantidade_estoque": 6,
        },
    ).json()

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

    # Estoque deve ter baixado de 6 para 4
    produto_atualizado = client.get(f"/produtos/{p['id_produto']}").json()
    assert produto_atualizado["quantidade_estoque"] == 4

    # Histórico deve listar a venda registrada
    historico = client.get("/vendas/").json()
    assert len(historico) == 1
    assert historico[0]["id_venda"] == venda["id_venda"]


def test_venda_bloqueia_estoque_insuficiente(client):
    p = client.post(
        "/produtos/",
        json={
            "nome": "Azeite Especial",
            "categoria": "Mercearia",
            "unidade": "un",
            "preco": "50.00",
            "quantidade_estoque": 3,
        },
    ).json()

    venda_res = client.post(
        "/vendas/",
        json={"itens": [{"id_produto": p["id_produto"], "quantidade": 5}]},
    )
    assert venda_res.status_code == 400
    assert "Estoque insuficiente" in venda_res.json()["detail"]

    # Estoque deve permanecer intacto em 3
    produto_atualizado = client.get(f"/produtos/{p['id_produto']}").json()
    assert produto_atualizado["quantidade_estoque"] == 3
