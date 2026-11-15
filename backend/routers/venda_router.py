from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from models.produto_model import Produto
from models.venda_model import ItemVenda, Venda
from schemas.venda_schema import VendaCreate, VendaResponse

router = APIRouter(prefix="/vendas", tags=["Vendas"])

LIMITE_DESCONTO = Decimal("200.00")
PERCENTUAL_DESCONTO = Decimal("0.05")


@router.get("/", response_model=list[VendaResponse])
def listar_vendas(db: Session = Depends(get_db)):
    return (
        db.query(Venda)
        .options(joinedload(Venda.itens))
        .order_by(Venda.id_venda.desc())
        .all()
    )


@router.post("/", response_model=VendaResponse, status_code=status.HTTP_201_CREATED)
def registrar_venda(payload: VendaCreate, db: Session = Depends(get_db)):
    # Agrupa quantidades caso o mesmo produto apareça mais de uma vez no carrinho
    quantidades_por_produto: dict[int, int] = {}
    for item in payload.itens:
        quantidades_por_produto[item.id_produto] = (
            quantidades_por_produto.get(item.id_produto, 0) + item.quantidade
        )

    produtos = (
        db.query(Produto)
        .filter(Produto.id_produto.in_(quantidades_por_produto.keys()))
        .all()
    )
    produtos_por_id = {produto.id_produto: produto for produto in produtos}

    itens_venda: list[ItemVenda] = []
    valor_bruto = Decimal("0.00")

    for id_produto, quantidade in quantidades_por_produto.items():
        produto = produtos_por_id.get(id_produto)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto #{id_produto} não encontrado.",
            )

        if produto.quantidade_estoque < quantidade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Estoque insuficiente para '{produto.nome}'. "
                    f"Disponível: {produto.quantidade_estoque}, solicitado: {quantidade}."
                ),
            )

        # Baixa automática no estoque
        produto.quantidade_estoque -= quantidade

        preco_unitario = Decimal(str(produto.preco)).quantize(Decimal("0.01"))
        subtotal = (preco_unitario * quantidade).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valor_bruto += subtotal

        itens_venda.append(
            ItemVenda(
                id_produto=produto.id_produto,
                nome_produto=produto.nome,
                preco_unitario=preco_unitario,
                quantidade=quantidade,
                subtotal=subtotal,
            )
        )

    # Regra de negócio: 5% de desconto apenas quando o valor bruto for superior a R$ 200,00
    if valor_bruto > LIMITE_DESCONTO:
        desconto_aplicado = (valor_bruto * PERCENTUAL_DESCONTO).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        teve_desconto = True
    else:
        desconto_aplicado = Decimal("0.00")
        teve_desconto = False

    valor_final = (valor_bruto - desconto_aplicado).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    nova_venda = Venda(
        valor_bruto=valor_bruto,
        desconto_aplicado=desconto_aplicado,
        valor_final=valor_final,
        teve_desconto=teve_desconto,
        itens=itens_venda,
    )
    db.add(nova_venda)
    db.commit()
    db.refresh(nova_venda)
    return nova_venda
