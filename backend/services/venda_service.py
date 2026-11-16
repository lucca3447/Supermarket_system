from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.venda_model import ItemVenda, Venda
from repositories.produto_repository import ProdutoRepository
from repositories.venda_repository import VendaRepository
from schemas.venda_schema import VendaCreate

LIMITE_DESCONTO = Decimal("200.00")
PERCENTUAL_DESCONTO = Decimal("0.05")


class VendaService:
    def __init__(self, db: Session):
        self.db = db
        self.venda_repository = VendaRepository(db)
        self.produto_repository = ProdutoRepository(db)

    def listar(self) -> list[Venda]:
        return self.venda_repository.listar()

    def registrar_venda(self, payload: VendaCreate) -> Venda:
        # Agrupa quantidades caso o mesmo produto apareça mais de uma vez no carrinho
        quantidades_por_produto: dict[int, int] = {}
        for item in payload.itens:
            quantidades_por_produto[item.id_produto] = (
                quantidades_por_produto.get(item.id_produto, 0) + item.quantidade
            )

        produtos = self.produto_repository.buscar_por_ids(
            list(quantidades_por_produto.keys())
        )
        produtos_por_id = {produto.id_produto: produto for produto in produtos}

        itens_venda: list[ItemVenda] = []
        valor_bruto = Decimal("0.00")

        # Ordena por ID para evitar deadlocks quando duas vendas disputam os mesmos itens
        for id_produto, quantidade in sorted(quantidades_por_produto.items()):
            produto = produtos_por_id.get(id_produto)
            if not produto:
                self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Produto #{id_produto} não encontrado.",
                )

            nome_produto = produto.nome
            preco_unitario = Decimal(str(produto.preco)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Baixa atômica no estoque dentro da mesma transação da venda
            if not self.produto_repository.baixar_estoque_atomico(id_produto, quantidade):
                self.db.rollback()
                atual = self.produto_repository.buscar_por_id(id_produto)
                disponivel = atual.quantidade_estoque if atual else 0
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Estoque insuficiente para '{nome_produto}'. "
                        f"Disponível: {disponivel}, solicitado: {quantidade}."
                    ),
                )

            subtotal = (preco_unitario * quantidade).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            valor_bruto += subtotal

            itens_venda.append(
                ItemVenda(
                    id_produto=id_produto,
                    nome_produto=nome_produto,
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
        return self.venda_repository.criar(nova_venda)
