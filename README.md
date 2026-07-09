# To-Do List — Backend (Django Rest Framework)

API REST de gerenciamento de tarefas pessoais com **autenticação por token** e
**isolamento de dados por usuário**. Roda **100% local**: o banco é um arquivo
SQLite (`db.sqlite3`) criado na raiz desta pasta — nenhum serviço externo é necessário.

## Requisitos

- Python 3.12+
- Windows, Linux ou macOS

## Setup

```powershell
# 1. Entrar na pasta do backend
cd todo-list-backend

# 2. Criar e ativar o ambiente virtual
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Linux/macOS

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Configurar as variáveis de ambiente
copy .env.example .env         # Windows (cp no Linux/macOS)
# edite o .env e defina uma SECRET_KEY própria:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 5. Criar o banco local (SQLite) e aplicar as migrações
python manage.py migrate

# 6. (Opcional) Criar um superusuário para o admin
python manage.py createsuperuser

# 7. Subir o servidor
python manage.py runserver
```

A API fica em `http://127.0.0.1:8000/api/` e a documentação interativa (Swagger)
em `http://127.0.0.1:8000/api/docs/`.

> **Para acessar do celular (Expo Go):** suba com
> `python manage.py runserver 0.0.0.0:8000`, adicione o IP do seu PC na rede
> local ao `ALLOWED_HOSTS` do `.env` (ex.: `ALLOWED_HOSTS=localhost,127.0.0.1,192.168.0.10`)
> e use `http://<ip-do-pc>:8000` no app.

## Testes

Os testes unitários ficam na pasta [test/](test/):

```powershell
python manage.py test
```

## Endpoints

Todas as rotas de tarefas exigem o header `Authorization: Token <token>`.

### Autenticação

| Método | Rota | Autenticado? | Descrição |
|---|---|---|---|
| POST | `/api/auth/register/` | Não | Cria a conta (`username`, `email`, `password`) |
| POST | `/api/auth/login/` | Não | Retorna `{ token, user }` |
| POST | `/api/auth/logout/` | Sim | Invalida o token no servidor |

### Tarefas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/tasks/` | Lista as tarefas do usuário (aceita busca e filtros) |
| POST | `/api/tasks/` | Cria tarefa vinculada ao usuário logado — **`due_date` é obrigatório** (sem vencimento → 400) |
| GET | `/api/tasks/{id}/` | Detalha uma tarefa |
| PUT / PATCH | `/api/tasks/{id}/` | Atualiza uma tarefa |
| DELETE | `/api/tasks/{id}/` | **Move para a lixeira** (soft delete) |
| GET | `/api/tasks/trash/` | Lista a lixeira do usuário |
| POST | `/api/tasks/{id}/restore/` | Restaura da lixeira |
| DELETE | `/api/tasks/{id}/permanent/` | Exclui definitivamente (só itens na lixeira) |

### Busca, filtros e ordenação em `GET /api/tasks/`

```
?search=mercado           → busca pelo título
?due_date=2026-07-10      → tarefas que vencem nesse dia
?due_date__lte=2026-07-10 → tarefas que vencem até essa data
?due_date__gte=2026-07-10 → tarefas que vencem a partir dessa data
?priority=alta            → baixa | media | alta
?completed=false          → true | false
?ordering=due_date        → ordena por vencimento (-due_date inverte)
```

### Documentação viva

| Rota | Descrição |
|---|---|
| `/api/docs/` | Swagger UI interativo |
| `/api/schema/` | Schema OpenAPI (JSON/YAML) |

## Estrutura

```
todo-list-backend/
├── manage.py            # Comandos Django
├── requirements.txt     # Dependências fixadas
├── .env.example         # Modelo das variáveis de ambiente
├── db.sqlite3           # Banco LOCAL (criado pelo migrate; fora do git)
├── config/              # Configuração global (settings, urls raiz)
├── accounts/            # Registro, login (token) e logout
├── tasks/               # Model, serializer, filtros e viewset de tarefas
└── test/                # Testes unitários (test_accounts.py, test_tasks.py)
```

## Segurança

- Toda rota nasce protegida (`IsAuthenticated` + `TokenAuthentication` globais);
  registro e login liberam acesso explicitamente.
- O queryset de tarefas sempre filtra por `request.user` — acessar tarefa de
  outro usuário responde **404**.
- O campo `user` não é gravável pelo cliente; o dono é sempre o usuário autenticado.
- Senhas com hash (validadores de força do Django); `SECRET_KEY` fora do código, no `.env`.
