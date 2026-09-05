from rest_framework import serializers
from .models import Cliente,Pedido,Producto,DetallePedido
from django.db import transaction
from .services import (
    crear_pedido,
    actualizar_pedido,
    cancelar_pedido,
    cambiar_estado_pedido
)
class ClienteSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(
        error_messages={
            
            'invalid': 'Ingrese un email válido.',
            'required': 'El email es obligatorio.'
        }
    )
    telefono = serializers.CharField(
        allow_blank=True
    )
    class Meta:
        model = Cliente
        fields = '__all__'
    def validate_email(self, value):

        consulta = Cliente.objects.filter(email=value)

        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)

        if consulta.exists():
            raise serializers.ValidationError(
                "Ya existe otro cliente registrado con este email."
            )

        return value

    def validate_telefono(self, value):

        print("VALOR RECIBIDO:", repr(value))
        print("TIPO:", type(value))

        if value == "":
            return value

        if not value.isdigit():
            raise serializers.ValidationError(
                "El teléfono debe contener solamente números."
            )

        if len(value) != 8:
            raise serializers.ValidationError(
                "El teléfono debe contener exactamente 8 dígitos."
            )

        return value

    def validate(self, data):

        estado = data.get('estado')
        telefono = data.get('telefono')

        if estado is True and not telefono:
            raise serializers.ValidationError(
                "Un cliente activo debe tener un teléfono registrado."
            )

        return data
class ClienteResumenSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cliente
        fields = [
            'id',
            'nombre',
            'email'
        ]
class ProductoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre',
            'precio',
            'stock',
            'estado'
        ]

class DetallePedidoSerializer(serializers.ModelSerializer):

    producto_nombre = serializers.CharField(
        source='producto.nombre',
        read_only=True
    )

    precio = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = DetallePedido

        fields = [
            'id',
            'producto',
            'producto_nombre',
            'cantidad',
            'precio',
            'subtotal'
        ]

    def get_subtotal(self, obj):

        return obj.cantidad * obj.precio

    def validate_cantidad(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor que cero."
            )

        return value

class PedidoSerializer(serializers.ModelSerializer):

    cliente_detalle = serializers.SerializerMethodField()

    detalles = DetallePedidoSerializer(
        many=True
    )

    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Pedido

        fields = [
            'id',
            'cliente',
            'cliente_detalle',
            'detalles',
            'descripcion',
            'total',
            'estado',
            'fecha'
        ]

        read_only_fields = [
            'id',
            'fecha',
            'cliente_detalle',
            'total',
            'estado'
        ]

    def get_cliente_detalle(self, obj):

        return ClienteResumenSerializer(
            obj.cliente
        ).data

    def validate(self, attrs):
        cliente = attrs.get('cliente')

        if cliente and not cliente.estado:
            raise serializers.ValidationError({
                'cliente':
                'El cliente está inactivo y no puede realizar pedidos.'
            })

        detalles = attrs.get('detalles')
        cantidades_anteriores = {}

        if self.instance:
            for detalle_anterior in self.instance.detalles.all():
                cantidades_anteriores[detalle_anterior.producto_id] = (
                    cantidades_anteriores.get(
                        detalle_anterior.producto_id,
                        0
                    )
                    + detalle_anterior.cantidad
                )

        if detalles is not None:
            productos_vistos = set()

            for detalle_data in detalles:

                producto = detalle_data['producto']
                cantidad_nueva = detalle_data['cantidad']

                if producto.id in productos_vistos:
                    raise serializers.ValidationError({
                        'detalles':
                        f'El producto "{producto.nombre}" '
                        f'no puede aparecer más de una vez.'
                    })

                productos_vistos.add(producto.id)

                if not producto.estado:
                    raise serializers.ValidationError({
                        'detalles':
                        f'El producto "{producto.nombre}" '
                        f'está inactivo.'
                    })

                stock_disponible = producto.stock

                cantidad_anterior = cantidades_anteriores.get(
                    producto.id,
                    0
                )

                stock_disponible += cantidad_anterior

                if cantidad_nueva > stock_disponible:
                    raise serializers.ValidationError({
                        'detalles':
                        f'No hay suficiente stock de '
                        f'"{producto.nombre}". '
                        f'Stock disponible para este pedido: '
                        f'{stock_disponible}.'
                    })

        return attrs
    @transaction.atomic
    def create(self, validated_data):

        return crear_pedido(
            validated_data
        )


    def update(self, instance, validated_data):
        return actualizar_pedido(instance, validated_data)
    @transaction.atomic
    def actualizar_pedido(instance, validated_data):

        instance = Pedido.objects.select_for_update().get(
            pk=instance.pk
        )

        detalles_data = validated_data.pop('detalles', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

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
class ProductoCrearSerializer(serializers.ModelSerializer):

    class Meta:
        model = Producto
        fields = [
            'nombre',
            'precio',
            'stock',
            'estado'
        ]

    def validate_precio(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'El precio no puede ser negativo.'
            )
        return value
class ProductoListaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre',
            'precio',
            'estado'
        ]

class ProductoDetalleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Producto
        fields = '__all__'

class ProductoActualizarSerializer(serializers.ModelSerializer):

    class Meta:
        model = Producto
        fields = [
            'nombre',
            'precio',
            'estado'
        ]
class CambiarEstadoPedidoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=[
            (Pedido.CONFIRMADO, 'Confirmado'),
            (Pedido.PREPARANDO, 'En preparación'),
            (Pedido.ENVIADO, 'Enviado'),
            (Pedido.ENTREGADO, 'Entregado'),
        ]
    )