# Sistema de Supermercado — TDE Programação Back-End

Aplicação full-stack de supermercado desenvolvida com **FastAPI + SQLAlchemy + MySQL** (com fallback automático para SQLite caso o MySQL esteja desligado) e **React + Vite + Tailwind CSS v4**, cobrindo todos os requisitos da disciplina:

- **CRUD de Produtos** (`cadastrar`, `listar`, `editar/atualizar` e `deletar` no banco de dados)
- **Interface do Cliente** para simulação de compra em formato de gôndola e cupom fiscal ao vivo
- **Controle de Estoque** com baixa automática a cada venda finalizada e validação de estoque suficiente
- **Regra de Negócio** aplicando **5% de desconto** em compras cujo valor bruto seja **superior a R$ 200,00** (`valor_bruto > 200.00`)

---

## Onde está cada requisito no código

Arquitetura do back-end em camadas: `routers/` (HTTP) → `services/` (regras de negócio) → `repositories/` (persistência SQLAlchemy) → `models/` (tabelas).

| Requisito | Back-end | Front-end |
| :--- | :--- | :--- |
| **CRUD de Produtos** | `backend/routers/produto_router.py` → `backend/services/produto_service.py` → `backend/repositories/produto_repository.py` | `frontend/src/components/EstoqueView.jsx` (aba *Produtos e Estoque*) |
| **Simulação de Compra** | `backend/routers/venda_router.py` → `backend/services/venda_service.py` → `backend/repositories/venda_repository.py` | `frontend/src/components/CaixaView.jsx` (aba *Caixa / Simulação*) |
| **Baixa Automática de Estoque** | `backend/services/venda_service.py` (`produto.quantidade_estoque -= quantidade`) | Atualização imediata da gôndola e tabela após `POST /vendas/` |
| **Desconto de 5% (> R$ 200,00)** | `backend/services/venda_service.py` (`if valor_bruto > LIMITE_DESCONTO`) | Medidor ao vivo no cupom fiscal (`CaixaView.jsx`) e histórico (`HistoricoView.jsx`) |
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
pytest test_api.py -v --cov=. --cov-report=term-missing
```

Valida os 15 cenários de API, banco e persistência com **100% de cobertura** no back-end (CRUD completo, erros `404` e `422`, fronteira exata de **R$ 200,00** vs **R$ 200,01**, desconto de 5% acima de R$ 200,00, agrupamento de itens repetidos, baixa de estoque, exclusão de produto já vendido preservando histórico, rollback, ciclo `get_db` e criação/fallback MySQL→SQLite).

### 3. Front-end (React + Vite)

Em outro terminal:

```bash
cd frontend
npm install
npm run test:coverage
npm run dev
```

- Interface rodando em: `http://localhost:5173`
- Os testes em `frontend/src/App.test.jsx` e `frontend/src/utils/format.test.js` (Vitest + React Testing Library) cobrem **100% das linhas e funções** de `App.jsx`, `CaixaView.jsx`, `EstoqueView.jsx`, `HistoricoView.jsx`, `api.js` e `format.js`.

