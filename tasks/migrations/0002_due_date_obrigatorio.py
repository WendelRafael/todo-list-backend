# Torna o vencimento obrigatório. Escrita manualmente porque o makemigrations
# interativo pediria um default; a tabela não tem linhas com due_date nulo
# (banco de desenvolvimento zerado), então o AlterField aplica direto.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="due_date",
            field=models.DateTimeField(verbose_name="vencimento"),
        ),
    ]
