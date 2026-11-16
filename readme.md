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
| **Consultor de Estoque (IA)** | `backend/routers/insight_router.py` → `backend/services/insight_service.py` (Gemini REST + fallback local) | `frontend/src/components/InsightEstoqueCard.jsx` (botão *Gerar Insights* e *Repor +X*) |
| **Autenticação e Níveis de Acesso (RBAC)** | `backend/routers/auth_router.py` → `backend/services/auth_service.py` + `core/security.py` (`bcrypt` + JWT em cookies `HttpOnly` e Refresh Tokens revogáveis) | `frontend/src/components/LoginView.jsx` + `react-router-dom` (`/login`, `/caixa`, `/estoque`, `/historico`) e auto-refresh no `api.js` |
| **Modelagem no Banco** | `backend/models/produto_model.py`, `backend/models/venda_model.py` e `backend/models/usuario_model.py` | — |

---

## Como executar o projeto

### 1. Back-end (FastAPI + MySQL)

> Por padrão (`backend/.env`), o sistema conecta no MySQL local (`mysql+pymysql://root:@localhost:3306/supermercado_tde`) e **cria o banco `supermercado_tde`, as tabelas, 10 produtos iniciais e 2 contas de acesso (`gerente` / `gerente123` e `cliente` / `cliente123`) automaticamente**. Se o MySQL estiver parado, ele usa SQLite local (`supermercado.db`) para não travar.
> Opcionalmente, defina `GEMINI_API_KEY` em `backend/.env` para ativar recomendações geradas pelo modelo `gemini-3.1-flash-lite` em `GET /insights/estoque` (sem chave ou sem internet, o sistema usa automaticamente o motor analítico local).

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

- API rodando em: `http://localhost:8000`
- Documentação Swagger: `http://localhost:8000/docs`

### 2. Testes Automatizados (Back-end)

```bash
cd backend
pytest test_api.py -v --cov=. --cov-report=term-missing
```

Valida os 24 cenários de API, autenticação, RBAC, banco, IA/fallback e persistência com **100% de cobertura** no back-end (login com cookies `HttpOnly`, rotação e revogação de refresh tokens, `401`/`403` entre `cliente` e `gerente`, CRUD completo, erros `404` e `422`, fronteira exata de **R$ 200,00** vs **R$ 200,01**, desconto de 5% acima de R$ 200,00, agrupamento de itens repetidos, baixa de estoque, exclusão de produto já vendido preservando histórico, insights via Gemini/fallback local, rollback, ciclo `get_db` e criação/fallback MySQL→SQLite).

### 3. Front-end (React + Vite)

Em outro terminal:

```bash
cd frontend
npm install
npm run test:coverage
npm run dev
```

- Interface rodando em: `http://localhost:5173`
- Os testes em `frontend/src/App.test.jsx`, `frontend/src/services/api.test.js` e `frontend/src/utils/format.test.js` (Vitest + React Testing Library) validam os 16 cenários de interface, roteamento protegido, auto-refresh em `401`, persistência do carrinho no F5 e regras de cálculo com **99,37% de cobertura em linhas** (`App.jsx`, `LoginView.jsx`, `CaixaView.jsx`, `EstoqueView.jsx`, `InsightEstoqueCard.jsx`, `HistoricoView.jsx`, `api.js` e `format.js`).

