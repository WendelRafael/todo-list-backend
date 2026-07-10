"""Testes das ações de tarefas: CRUD, vencimento, lixeira, filtros e isolamento."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from tasks.models import Task

# Vencimento padrão dos fixtures — o campo é obrigatório no model
VENCIMENTO = "2026-07-15T12:00:00Z"


def criar_tarefa(user, title, **extra):
    extra.setdefault("due_date", VENCIMENTO)
    return Task.objects.create(user=user, title=title, **extra)


class BaseTaskTestCase(APITestCase):
    """Cria dois usuários (A autenticado, B intruso) para os cenários."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            "alice", email="alice@example.com", password="senha-forte-123"
        )
        self.user_b = User.objects.create_user(
            "bob", email="bob@example.com", password="senha-forte-123"
        )
        self.token_a = Token.objects.create(user=self.user_a)
        self.token_b = Token.objects.create(user=self.user_b)
        self.auth_as(self.token_a)

    def auth_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class TaskCrudTests(BaseTaskTestCase):
    """CRUD básico de /api/tasks/ com usuário autenticado."""

    def test_criar_tarefa_vincula_ao_usuario_logado(self):
        """Criação responde 201 e o dono é sempre o usuário do token,
        definido pelo servidor (nunca pelo corpo da requisição)."""
        response = self.client.post(
            reverse("task-list"),
            {
                "title": "Estudar DRF",
                "description": "Ler a doc",
                "priority": "alta",
                "due_date": VENCIMENTO,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(id=response.data["id"])
        self.assertEqual(task.user, self.user_a)

    def test_listar_apenas_tarefas_proprias(self):
        """A listagem devolve só as tarefas do usuário logado; as dos
        outros usuários ficam de fora."""
        criar_tarefa(self.user_a, "Minha tarefa")
        criar_tarefa(self.user_b, "Tarefa do outro")
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titulos = [t["title"] for t in response.data]
        self.assertEqual(titulos, ["Minha tarefa"])

    def test_editar_tarefa(self):
        """PATCH altera o título e a mudança persiste no banco."""
        task = criar_tarefa(self.user_a, "Antes")
        response = self.client.patch(
            reverse("task-detail", args=[task.id]), {"title": "Depois"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Depois")

    def test_concluir_tarefa_persiste(self):
        """Marcar completed=True persiste: recarregar o detalhe devolve a
        tarefa ainda concluída."""
        task = criar_tarefa(self.user_a, "Concluir")
        self.client.patch(reverse("task-detail", args=[task.id]), {"completed": True})
        response = self.client.get(reverse("task-detail", args=[task.id]))
        self.assertTrue(response.data["completed"])

    def test_excluir_move_para_lixeira_e_some_da_lista(self):
        """DELETE é soft delete: preenche deleted_at mantendo o registro no
        banco, e a tarefa some da listagem e do detalhe (404)."""
        task = criar_tarefa(self.user_a, "Excluir")
        response = self.client.delete(reverse("task-detail", args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Soft delete: o registro continua no banco, com deleted_at preenchido
        task.refresh_from_db()
        self.assertIsNotNone(task.deleted_at)
        # E some das listagens/detalhe normais
        self.assertEqual(self.client.get(reverse("task-list")).data, [])
        response = self.client.get(reverse("task-detail", args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cliente_nao_define_o_dono_da_tarefa(self):
        """Enviar "user" de outra pessoa no corpo é ignorado: a tarefa nasce
        do usuário autenticado (sem escalar privilégio pelo JSON)."""
        response = self.client.post(
            reverse("task-list"),
            {
                "title": "Tentativa de invasão",
                "due_date": VENCIMENTO,
                "user": self.user_b.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(id=response.data["id"])
        self.assertEqual(task.user, self.user_a)


class TaskDueDateValidationTests(BaseTaskTestCase):
    """O vencimento é obrigatório: criar sem due_date responde 400 tratado."""

    def test_criar_sem_vencimento_retorna_400_com_mensagem(self):
        """Criar sem due_date responde 400 com mensagem apontando o campo,
        e nada é gravado no banco."""
        response = self.client.post(reverse("task-list"), {"title": "Sem prazo"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)
        self.assertIn("vencimento", str(response.data["due_date"][0]))
        self.assertFalse(Task.objects.filter(title="Sem prazo").exists())

    def test_criar_com_vencimento_nulo_retorna_400(self):
        """due_date enviado explicitamente como null também é rejeitado."""
        response = self.client.post(
            reverse("task-list"),
            {"title": "Prazo nulo", "due_date": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)

    def test_criar_com_vencimento_invalido_retorna_400(self):
        """Texto que não é data ("amanhã") responde 400 apontando o campo."""
        response = self.client.post(
            reverse("task-list"), {"title": "Prazo inválido", "due_date": "amanhã"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)

    def test_editar_nao_remove_o_vencimento(self):
        """A edição não pode anular o prazo: PATCH com due_date null responde
        400 e o valor original permanece no banco."""
        task = criar_tarefa(self.user_a, "Com prazo")
        response = self.client.patch(
            reverse("task-detail", args=[task.id]),
            {"due_date": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        task.refresh_from_db()
        self.assertIsNotNone(task.due_date)


class TaskTrashTests(BaseTaskTestCase):
    """Lixeira: trash, restore e exclusão definitiva."""

    def setUp(self):
        super().setUp()
        self.task = criar_tarefa(self.user_a, "Na lixeira")
        self.client.delete(reverse("task-detail", args=[self.task.id]))

    def test_trash_lista_apenas_excluidas_do_usuario(self):
        """GET /tasks/trash/ lista só as tarefas excluídas do usuário; as
        ativas ficam de fora."""
        criar_tarefa(self.user_a, "Ativa")
        response = self.client.get(reverse("task-trash"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titulos = [t["title"] for t in response.data]
        self.assertEqual(titulos, ["Na lixeira"])

    def test_restore_devolve_a_tarefa_para_a_lista(self):
        """Restore limpa o deleted_at: a tarefa volta para a listagem normal
        e sai da lixeira."""
        response = self.client.post(reverse("task-restore", args=[self.task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.deleted_at)
        titulos = [t["title"] for t in self.client.get(reverse("task-list")).data]
        self.assertIn("Na lixeira", titulos)
        self.assertEqual(self.client.get(reverse("task-trash")).data, [])

    def test_permanent_apaga_de_verdade(self):
        """Exclusão definitiva responde 204 e o registro some do banco
        (hard delete, sem volta)."""
        response = self.client.delete(reverse("task-permanent", args=[self.task.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_permanent_exige_tarefa_na_lixeira(self):
        """Tarefa ativa não pode ser apagada de vez: responde 404 e o
        registro continua intacto."""
        ativa = criar_tarefa(self.user_a, "Ativa")
        response = self.client.delete(reverse("task-permanent", args=[ativa.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(id=ativa.id).exists())

    def test_intruso_nao_restaura_nem_apaga_da_lixeira_alheia(self):
        """Outro usuário recebe 404 ao tentar restaurar ou apagar item da
        lixeira alheia, e o registro sobrevive."""
        self.auth_as(self.token_b)
        response = self.client.post(reverse("task-restore", args=[self.task.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.delete(reverse("task-permanent", args=[self.task.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(id=self.task.id).exists())


class TaskFilterTests(BaseTaskTestCase):
    """Busca por título e filtros por data, prioridade e status."""

    def setUp(self):
        super().setUp()
        criar_tarefa(
            self.user_a,
            "Ir ao mercado",
            priority="alta",
            due_date="2026-07-10T18:00:00Z",
        )
        criar_tarefa(
            self.user_a,
            "Estudar Django",
            priority="baixa",
            completed=True,
            due_date="2026-07-20T10:00:00Z",
        )

    def get_titles(self, query):
        response = self.client.get(reverse("task-list") + query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [t["title"] for t in response.data]

    def test_busca_por_titulo(self):
        """?search encontra a tarefa por trecho do título."""
        self.assertEqual(self.get_titles("?search=mercado"), ["Ir ao mercado"])

    def test_filtro_por_prioridade(self):
        """?priority devolve apenas as tarefas daquela prioridade."""
        self.assertEqual(self.get_titles("?priority=alta"), ["Ir ao mercado"])

    def test_filtro_por_status(self):
        """?completed=true devolve apenas as tarefas concluídas."""
        self.assertEqual(self.get_titles("?completed=true"), ["Estudar Django"])

    def test_filtro_por_dia_de_vencimento(self):
        """?due_date=AAAA-MM-DD casa pelo dia do vencimento, ignorando a hora."""
        self.assertEqual(self.get_titles("?due_date=2026-07-10"), ["Ir ao mercado"])

    def test_filtro_vence_ate_a_data(self):
        """?due_date__lte devolve o que vence até a data informada, inclusive."""
        self.assertEqual(
            self.get_titles("?due_date__lte=2026-07-15"), ["Ir ao mercado"]
        )

    def test_ordenacao_por_vencimento(self):
        """?ordering=due_date lista do prazo mais próximo ao mais distante."""
        self.assertEqual(
            self.get_titles("?ordering=due_date"),
            ["Ir ao mercado", "Estudar Django"],
        )


class TaskIsolationTests(BaseTaskTestCase):
    """Usuário B não pode ver, editar ou excluir tarefas do usuário A."""

    def setUp(self):
        super().setUp()
        self.task_de_a = criar_tarefa(self.user_a, "Só da Alice")
        self.auth_as(self.token_b)

    def test_intruso_nao_ve_detalhe(self):
        """Detalhe de tarefa alheia responde 404 — para o intruso ela nem
        existe (sem vazar que há algo lá via 403)."""
        response = self.client.get(reverse("task-detail", args=[self.task_de_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_intruso_nao_edita(self):
        """PATCH em tarefa alheia responde 404 e o título original fica
        intacto."""
        response = self.client.patch(
            reverse("task-detail", args=[self.task_de_a.id]), {"title": "hackeado"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.task_de_a.refresh_from_db()
        self.assertEqual(self.task_de_a.title, "Só da Alice")

    def test_intruso_nao_exclui(self):
        """DELETE em tarefa alheia responde 404 e a tarefa não vai para a
        lixeira."""
        response = self.client.delete(reverse("task-detail", args=[self.task_de_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.task_de_a.refresh_from_db()
        self.assertIsNone(self.task_de_a.deleted_at)

    def test_anonimo_nao_acessa_nada(self):
        """Sem token, listar e criar respondem 401: nenhuma rota de tarefas
        é pública."""
        self.client.credentials()  # remove o token
        self.assertEqual(
            self.client.get(reverse("task-list")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.post(reverse("task-list"), {"title": "x"}).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
