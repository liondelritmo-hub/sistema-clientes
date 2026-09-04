from .models import Producto,Pedido
import django_filters

class ProductoFilter(django_filters.FilterSet):

    class Meta:
        model = Producto
        fields = {
            'nombre': ['exact', 'icontains'],
            'precio': ['exact', 'gte', 'lte'],
            'stock': ['exact', 'gte', 'lte'],
            'estado': ['exact'],
        }
class PedidoFilter(django_filters.FilterSet):

    class Meta:
        model = Pedido
        fields = {
            'cliente': ['exact'],
            'estado': ['exact'],
            'total': ['exact', 'gte', 'lte'],
            'fecha': ['exact', 'gte', 'lte'],
        }