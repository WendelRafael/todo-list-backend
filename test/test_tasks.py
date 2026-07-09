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
    def test_criar_tarefa_vincula_ao_usuario_logado(self):
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
        criar_tarefa(self.user_a, "Minha tarefa")
        criar_tarefa(self.user_b, "Tarefa do outro")
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titulos = [t["title"] for t in response.data]
        self.assertEqual(titulos, ["Minha tarefa"])

    def test_editar_tarefa(self):
        task = criar_tarefa(self.user_a, "Antes")
        response = self.client.patch(
            reverse("task-detail", args=[task.id]), {"title": "Depois"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Depois")

    def test_concluir_tarefa_persiste(self):
        task = criar_tarefa(self.user_a, "Concluir")
        self.client.patch(reverse("task-detail", args=[task.id]), {"completed": True})
        response = self.client.get(reverse("task-detail", args=[task.id]))
        self.assertTrue(response.data["completed"])

    def test_excluir_move_para_lixeira_e_some_da_lista(self):
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
        response = self.client.post(reverse("task-list"), {"title": "Sem prazo"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)
        self.assertIn("vencimento", str(response.data["due_date"][0]))
        self.assertFalse(Task.objects.filter(title="Sem prazo").exists())

    def test_criar_com_vencimento_nulo_retorna_400(self):
        response = self.client.post(
            reverse("task-list"),
            {"title": "Prazo nulo", "due_date": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)

    def test_criar_com_vencimento_invalido_retorna_400(self):
        response = self.client.post(
            reverse("task-list"), {"title": "Prazo inválido", "due_date": "amanhã"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("due_date", response.data)

    def test_editar_nao_remove_o_vencimento(self):
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
        criar_tarefa(self.user_a, "Ativa")
        response = self.client.get(reverse("task-trash"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titulos = [t["title"] for t in response.data]
        self.assertEqual(titulos, ["Na lixeira"])

    def test_restore_devolve_a_tarefa_para_a_lista(self):
        response = self.client.post(reverse("task-restore", args=[self.task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.deleted_at)
        titulos = [t["title"] for t in self.client.get(reverse("task-list")).data]
        self.assertIn("Na lixeira", titulos)
        self.assertEqual(self.client.get(reverse("task-trash")).data, [])

    def test_permanent_apaga_de_verdade(self):
        response = self.client.delete(reverse("task-permanent", args=[self.task.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_permanent_exige_tarefa_na_lixeira(self):
        ativa = criar_tarefa(self.user_a, "Ativa")
        response = self.client.delete(reverse("task-permanent", args=[ativa.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Task.objects.filter(id=ativa.id).exists())

    def test_intruso_nao_restaura_nem_apaga_da_lixeira_alheia(self):
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
        self.assertEqual(self.get_titles("?search=mercado"), ["Ir ao mercado"])

    def test_filtro_por_prioridade(self):
        self.assertEqual(self.get_titles("?priority=alta"), ["Ir ao mercado"])

    def test_filtro_por_status(self):
        self.assertEqual(self.get_titles("?completed=true"), ["Estudar Django"])

    def test_filtro_por_dia_de_vencimento(self):
        self.assertEqual(self.get_titles("?due_date=2026-07-10"), ["Ir ao mercado"])

    def test_filtro_vence_ate_a_data(self):
        self.assertEqual(
            self.get_titles("?due_date__lte=2026-07-15"), ["Ir ao mercado"]
        )

    def test_ordenacao_por_vencimento(self):
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
        response = self.client.get(reverse("task-detail", args=[self.task_de_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_intruso_nao_edita(self):
        response = self.client.patch(
            reverse("task-detail", args=[self.task_de_a.id]), {"title": "hackeado"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.task_de_a.refresh_from_db()
        self.assertEqual(self.task_de_a.title, "Só da Alice")

    def test_intruso_nao_exclui(self):
        response = self.client.delete(reverse("task-detail", args=[self.task_de_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.task_de_a.refresh_from_db()
        self.assertIsNone(self.task_de_a.deleted_at)

    def test_anonimo_nao_acessa_nada(self):
        self.client.credentials()  # remove o token
        self.assertEqual(
            self.client.get(reverse("task-list")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.post(reverse("task-list"), {"title": "x"}).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
