# Sistema de Supermercado — TDE Programação Back-End

Aplicação full-stack de supermercado desenvolvida com **FastAPI + SQLAlchemy + MySQL** (com fallback automático para SQLite caso o MySQL esteja desligado) e **React + Vite + Tailwind CSS v4**, cobrindo todos os requisitos da disciplina:

- **CRUD de Produtos** (`cadastrar`, `listar`, `editar/atualizar` e `deletar` no banco de dados)
- **Interface do Cliente** para simulação de compra em formato de gôndola e cupom fiscal ao vivo
- **Controle de Estoque** com baixa automática a cada venda finalizada e validação de estoque suficiente
- **Regra de Negócio** aplicando **5% de desconto** em compras cujo valor bruto seja **superior a R$ 200,00** (`valor_bruto > 200.00`)

---

## Onde está cada requisito no código

| Requisito | Back-end | Front-end |
| :--- | :--- | :--- |
| **CRUD de Produtos** | `backend/routers/produto_router.py` (`GET`, `POST`, `PUT`, `DELETE /produtos/`) | `frontend/src/components/EstoqueView.jsx` (aba *Produtos e Estoque*) |
| **Simulação de Compra** | `backend/routers/venda_router.py` (`POST /vendas/`) | `frontend/src/components/CaixaView.jsx` (aba *Caixa / Simulação*) |
| **Baixa Automática de Estoque** | `backend/routers/venda_router.py` (`produto.quantidade_estoque -= quantidade`) | Atualização imediata da gôndola e tabela após `POST /vendas/` |
| **Desconto de 5% (> R$ 200,00)** | `backend/routers/venda_router.py` (`if valor_bruto > LIMITE_DESCONTO`) | Medidor ao vivo no cupom fiscal (`CaixaView.jsx`) e histórico (`HistoricoView.jsx`) |
| **Modelagem no Banco** | `backend/models/produto_model.py` e `backend/models/venda_model.py` | — |

---

## Como executar o projeto

### 1. Back-end (FastAPI + MySQL)

> Por padrão (`backend/.env`), o sistema conecta no MySQL local (`mysql+pymysql://root:@localhost:3306/supermercado_tde`) e **cria o banco `supermercado_tde`, as tabelas e 10 produtos iniciais automaticamente**. Se o MySQL estiver parado, ele usa SQLite local (`supermercado.db`) para não travar.

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

- API rodando em: `http://127.0.0.1:8000`
- Documentação Swagger: `http://127.0.0.1:8000/docs`

### 2. Testes Automatizados (Back-end)

```bash
cd backend
pytest test_api.py -v
```

Valida CRUD de produtos, compra exata de **R$ 200,00** (sem desconto), compra de **R$ 250,00** (**5% de desconto = R$ 12,50**), baixa automática de estoque e bloqueio de estoque insuficiente.

### 3. Front-end (React + Vite)

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

- Interface rodando em: `http://localhost:5173`

