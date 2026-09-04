from django.db import migrations, models


def convertir_estados(apps, schema_editor):

    Pedido = apps.get_model('clientes', 'Pedido')

    Pedido.objects.filter(
        estado__in=['1', 'True', 'true']
    ).update(
        estado='pendiente'
    )

    Pedido.objects.filter(
        estado__in=['0', 'False', 'false']
    ).update(
        estado='cancelado'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0008_remove_pedido_productos'),
    ]

    operations = [

        migrations.AlterField(
            model_name='pedido',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('confirmado', 'Confirmado'),
                    ('preparando', 'En preparación'),
                    ('enviado', 'Enviado'),
                    ('entregado', 'Entregado'),
                    ('cancelado', 'Cancelado')
                ],
                default='pendiente',
                max_length=20
            ),
        ),

        migrations.RunPython(
            convertir_estados
        ),
    ]