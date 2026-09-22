from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inspection", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspection",
            name="revoked_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="撤回时间"),
        ),
        migrations.AddField(
            model_name="inspection",
            name="revoked_by",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="撤回人"),
        ),
        migrations.AddField(
            model_name="inspection",
            name="revoke_reason",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="撤回原因"),
        ),
    ]
