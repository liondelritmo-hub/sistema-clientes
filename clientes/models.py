from django.db import models

# Create your models here.
class Cliente(models.Model):
    
    nombre = models.CharField(max_length=30)
    email = models.EmailField(unique=True) 
    telefono = models.CharField(max_length=30)
    empresa = models.CharField(max_length=100)
    estado = models.BooleanField(default=True)
    fecha_registro = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nombre
class Producto(models.Model):

    nombre = models.CharField(
        max_length=100
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    stock = models.PositiveIntegerField(
        default=0
    )

    estado = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.nombre


class Pedido(models.Model):

    PENDIENTE = 'pendiente'
    CONFIRMADO = 'confirmado'
    PREPARANDO = 'preparando'
    ENVIADO = 'enviado'
    ENTREGADO = 'entregado'
    CANCELADO = 'cancelado'

    ESTADOS_PEDIDO = [
        (PENDIENTE, 'Pendiente'),
        (CONFIRMADO, 'Confirmado'),
        (PREPARANDO, 'En preparación'),
        (ENVIADO, 'Enviado'),
        (ENTREGADO, 'Entregado'),
        (CANCELADO, 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='pedidos'
    )

    descripcion = models.CharField(max_length=200)

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_PEDIDO,
        default=PENDIENTE
    )

    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.descripcion

class DetallePedido(models.Model):

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )

    cantidad = models.PositiveIntegerField()

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"