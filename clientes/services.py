from django.db import transaction
from rest_framework import serializers

from .models import Pedido, DetallePedido, Producto
ESTADOS_PEDIDO = [
    'pendiente',
    'confirmado',
    'preparando',
    'enviado',
    'entregado',
    'cancelado',
]
TRANSICIONES_PEDIDO = {
    'pendiente': ['confirmado'],
    'confirmado': ['preparando'],
    'preparando': ['enviado'],
    'enviado': ['entregado'],
    'entregado': [],
    'cancelado': [],
}
@transaction.atomic
def cambiar_estado_pedido(instance, nuevo_estado):

    if nuevo_estado not in ESTADOS_PEDIDO:
        raise serializers.ValidationError({
            'estado':
            f'El estado "{nuevo_estado}" no es válido.'
        })

    estado_actual = instance.estado

    estados_permitidos = TRANSICIONES_PEDIDO.get(
        estado_actual,
        []
    )

    if nuevo_estado not in estados_permitidos:
        raise serializers.ValidationError({
            'estado':
            f'No se puede cambiar el pedido de '
            f'"{estado_actual}" a "{nuevo_estado}".'
        })

    instance.estado = nuevo_estado

    instance.save(
        update_fields=['estado']
    )

    return instance
@transaction.atomic
def crear_pedido(validated_data):

    detalles_data = validated_data.pop(
        'detalles',
        []
    )

    total = 0
    detalles_creados = []

    for detalle_data in detalles_data:

        producto = detalle_data['producto']
        cantidad = detalle_data['cantidad']

        producto = Producto.objects.select_for_update().get(
            pk=producto.pk
        )

        if cantidad > producto.stock:
            raise serializers.ValidationError({
                'detalles':
                f'No hay suficiente stock de '
                f'"{producto.nombre}".'
            })

        precio = producto.precio
        subtotal = precio * cantidad

        total += subtotal

        detalles_creados.append({
            'producto': producto,
            'cantidad': cantidad,
            'precio': precio
        })

    pedido = Pedido.objects.create(
        total=total,
        **validated_data
    )

    for detalle in detalles_creados:

        DetallePedido.objects.create(
            pedido=pedido,
            producto=detalle['producto'],
            cantidad=detalle['cantidad'],
            precio=detalle['precio']
        )

        producto = detalle['producto']

        producto.stock -= detalle['cantidad']

        producto.save(
            update_fields=['stock']
        )

    return pedido

@transaction.atomic
def actualizar_pedido(instance, validated_data):

    detalles_data = validated_data.pop(
        'detalles',
        None
    )

    for attr, value in validated_data.items():

        setattr(
            instance,
            attr,
            value
        )

    if detalles_data is not None:

        detalles_anteriores = (
            instance.detalles
            .select_related('producto')
            .all()
        )

        # Restaurar el stock anterior
        for detalle_anterior in detalles_anteriores:

            producto = Producto.objects.select_for_update().get(
                pk=detalle_anterior.producto_id
            )

            producto.stock += detalle_anterior.cantidad

            producto.save(
                update_fields=['stock']
            )

        # Eliminar detalles anteriores
        instance.detalles.all().delete()

        total = 0
        detalles_creados = []

        # Crear los nuevos detalles
        for detalle_data in detalles_data:

            producto = detalle_data['producto']
            cantidad = detalle_data['cantidad']

            producto = Producto.objects.select_for_update().get(
                pk=producto.pk
            )

            if cantidad > producto.stock:

                raise serializers.ValidationError({
                    'detalles':
                    f'No hay suficiente stock de '
                    f'"{producto.nombre}".'
                })

            precio = producto.precio
            subtotal = precio * cantidad

            total += subtotal

            detalles_creados.append({
                'producto': producto,
                'cantidad': cantidad,
                'precio': precio
            })

        # Descontar stock y guardar detalles
        for detalle in detalles_creados:

            DetallePedido.objects.create(
                pedido=instance,
                producto=detalle['producto'],
                cantidad=detalle['cantidad'],
                precio=detalle['precio']
            )

            producto = detalle['producto']

            producto.stock -= detalle['cantidad']

            producto.save(
                update_fields=['stock']
            )

        instance.total = total

    instance.save()

    return instance

@transaction.atomic

def cancelar_pedido(instance):
    instance = Pedido.objects.select_for_update().get(
        pk=instance.pk
    )

    if instance.estado in [
        Pedido.ENVIADO,
        Pedido.ENTREGADO
    ]:
        raise serializers.ValidationError({
            'estado':
            f'El pedido no puede cancelarse porque '
            f'está en estado "{instance.estado}".'
        })

    if instance.estado == Pedido.CANCELADO:
        raise serializers.ValidationError({
            'estado':
            'El pedido ya está cancelado.'
        })

    detalles = (
        instance.detalles
        .select_related('producto')
        .all()
    )

    for detalle in detalles:
        producto = Producto.objects.select_for_update().get(
            pk=detalle.producto_id
        )

        producto.stock += detalle.cantidad
        producto.save(update_fields=['stock'])

    instance.estado = Pedido.CANCELADO
    instance.save(update_fields=['estado'])

    return instance
