from django.shortcuts import render
from .models import Cliente,Producto
from .forms import FormularioClientes
from django.views.generic import ListView,CreateView,UpdateView,DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import ProtectedError

# Create your views here.
class ListaClientes(ListView):
    model = Cliente
    template_name = 'clientes/cliente_list.html'
    context_object_name = 'clientes'

class RegistrarClientes(CreateView):
    model = Cliente
    form_class=FormularioClientes
    template_name='clientes/crear.html'
    success_url = reverse_lazy('cliente_list')
    def form_valid(self, form):
        messages.success(self.request, '¡Cliente se registro correctamente!')
        return super().form_valid(form)




class EditarCliente(UpdateView):

    model = Cliente
    template_name = 'clientes/editar.html'
    form_class = FormularioClientes
    success_url = reverse_lazy('cliente_list')   
    def form_valid(self, form):
        try:

            messages.success(self.request, 'Cliente se modifico correctamente.')
        except Exception:
            messages.error(self.request, 'No se pudo modificar el cliente.')

        return super().form_valid(form)

class EliminarCliente(DeleteView):
  model = Cliente
  template_name = ('clientes/eliminar.html')
  success_url = reverse_lazy('cliente_list')
  def form_valid(self, form):
        try:

            messages.success(self.request, 'Cliente se pudo eliminar correctamente.')
        except Exception:
            messages.error(self.request, 'No se pudo eliminar el cliente.')

        return super().form_valid(form)




from rest_framework.permissions import DjangoModelPermissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView
from .models import Cliente,Pedido
from .serializers import CambiarEstadoPedidoSerializer,ProductoActualizarSerializer,ProductoDetalleSerializer,ProductoListaSerializer,ClienteSerializer,PedidoSerializer,ProductoSerializer,ProductoCrearSerializer
from .permissions import ClienteModelPermissions
from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter
from .pagination import ClientePagination
from rest_framework.viewsets import ModelViewSet
from .permissions import PuedeModificarCliente
from rest_framework.decorators import action
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView
)

from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductoFilter
from .permissions import IsStaffUser
from .filters import PedidoFilter
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin
)
from .services import cancelar_pedido
from rest_framework.filters import OrderingFilter
class ClienteViewSet(ModelViewSet):

    queryset = Cliente.objects.all()

    serializer_class = ClienteSerializer
    @action(
        detail=True,
        methods=['get'],
        url_path='pedidos'
    )
    def pedidos(self, request, pk=None):

        cliente = self.get_object()

        pedidos = cliente.pedidos.all()

        # Búsqueda
        search = request.query_params.get('search')

        if search:
            pedidos = pedidos.filter(
                descripcion__icontains=search
            )

        # Ordenamiento
        ordering = request.query_params.get('ordering')

        if ordering:
            pedidos = pedidos.order_by(ordering)

        # Paginación
        paginator = ClientePagination()

        pagina = paginator.paginate_queryset(
            pedidos,
            request
        )

        serializer = PedidoSerializer(
            pagina,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )
    
class ClienteGenericoAPIView(ListCreateAPIView):

    queryset = Cliente.objects.all()

    serializer_class = ClienteSerializer

    permission_classes = [IsAuthenticated]

    pagination_class = ClientePagination

    filter_backends = [
        SearchFilter,
        OrderingFilter
    ]

    search_fields = [
        'nombre',
        'email'
    ]

    ordering_fields = [
        'nombre',
        'email',
        'fecha_registro'
    ]
    
class ClienteDetalleGenericoAPIView(RetrieveUpdateDestroyAPIView):

    queryset = Cliente.objects.all()

    serializer_class = ClienteSerializer

    permission_classes = [IsAuthenticated]

class ClienteAPIView(APIView):
    queryset = Cliente.objects.all()
    def get_permissions(self):

        return [
            IsAuthenticated(),
            ClienteModelPermissions()
        ]

    # =========================
    # GET
    # =========================

    def get(self, request):

        clientes = Cliente.objects.all()

        # -------------------------
        # Búsqueda por nombre
        # -------------------------

        nombre = request.query_params.get('nombre')

        if nombre:

            clientes = clientes.filter(
                nombre__icontains=nombre
            )

        # -------------------------
        # Búsqueda por email
        # -------------------------

        email = request.query_params.get('email')

        if email:

            clientes = clientes.filter(
                email__icontains=email
            )

        # -------------------------
        # Ordenamiento
        # -------------------------

        ordering = request.query_params.get('ordering')

        campos_permitidos = [
            'nombre',
            'email',
            'fecha_registro'
        ]

        if ordering:

            campo = ordering.lstrip('-')

            if campo not in campos_permitidos:

                return Response(
                    {
                        "error":
                        "Campo de ordenamiento no permitido."
                    },
                    status=400
                )

            clientes = clientes.order_by(ordering)

        # -------------------------
        # Paginación
        # -------------------------

        paginator = PageNumberPagination()

        try:

            page_size = int(
                request.query_params.get(
                    'page_size',
                    5
                )
            )

            if page_size < 1 or page_size > 50:

                return Response(
                    {
                        "error":
                        "page_size debe estar entre 1 y 50."
                    },
                    status=400
                )

        except ValueError:

            return Response(
                {
                    "error":
                    "page_size debe ser un número entero."
                },
                status=400
            )

        paginator.page_size = page_size

        resultado = paginator.paginate_queryset(
            clientes,
            request
        )

        serializer = ClienteSerializer(
            resultado,
            many=True
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    # =========================
    # POST
    # =========================

    def post(self, request):

        serializer = ClienteSerializer(
            data=request.data
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data,
                status=201
            )

        return Response(
            serializer.errors,
            status=400
        )

    # =========================
    # PUT
    # =========================

    def put(self, request, pk):

        try:

            cliente = Cliente.objects.get(
                pk=pk
            )

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error":
                    "El cliente no existe."
                },
                status=404
            )

        serializer = ClienteSerializer(
            cliente,
            data=request.data
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data,
                status=200
            )

        return Response(
            serializer.errors,
            status=400
        )

    # =========================
    # PATCH
    # =========================

    def patch(self, request, pk):

        try:

            cliente = Cliente.objects.get(
                pk=pk
            )

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error":
                    "El cliente no existe."
                },
                status=404
            )

        serializer = ClienteSerializer(
            cliente,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data,
                status=200
            )

        return Response(
            serializer.errors,
            status=400
        )

    # =========================
    # DELETE
    # =========================

    def delete(self, request, pk):

        try:

            cliente = Cliente.objects.get(
                pk=pk
            )

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error":
                    "El cliente no existe."
                },
                status=404
            )

        cliente.delete()

        return Response(
            {
                "mensaje":
                "Cliente eliminado correctamente."
            },
            status=200
        )

class ClienteDetalleAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        try:
            cliente = Cliente.objects.get(pk=pk)

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error": "Cliente no encontrado."
                },
                status=404
            )

        serializer = ClienteSerializer(cliente)

        return Response(
            serializer.data,
            status=200
        )

    def put(self, request, pk):

        try:
            cliente = Cliente.objects.get(pk=pk)

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error": "Cliente no encontrado."
                },
                status=404
            )

        serializer = ClienteSerializer(
            cliente,
            data=request.data
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data,
                status=200
            )

        return Response(
            serializer.errors,
            status=400
        )
    def patch(self, request, pk):

        try:

            cliente = Cliente.objects.get(
                pk=pk
            )

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error":
                    "El cliente no existe."
                },
                status=404
            )

        serializer = ClienteSerializer(
            cliente,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response(
                serializer.data,
                status=200
            )

        return Response(
            serializer.errors,
            status=400
        )
    def delete(self, request, pk):

        try:
            cliente = Cliente.objects.get(pk=pk)

        except Cliente.DoesNotExist:

            return Response(
                {
                    "error": "Cliente no encontrado."
                },
                status=404
            )

        cliente.delete()

        return Response(
            {
                "mensaje": "Cliente eliminado correctamente."
            },
            status=204
        )
from .services import (
    cancelar_pedido,
    cambiar_estado_pedido
)
class PedidoViewSet(ModelViewSet):

    queryset = (
        Pedido.objects
        .select_related('cliente')
        .prefetch_related(
            'detalles__producto'
        )
    )

    serializer_class = PedidoSerializer
    pagination_class = ClientePagination

    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
    ]

    filterset_class = PedidoFilter

    ordering_fields = [
        'total',
        'fecha',
    ]

    ordering = ['id']

    def get_permissions(self):
        if self.action in [
            'create',
            'update',
            'partial_update',
            'destroy',
            'cancelar',
            'cambiar_estado',
        ]:
            return [
                IsAuthenticated(),
                IsStaffUser()
            ]

        return [IsAuthenticated()]
        
    def get_queryset(self):

        queryset = Pedido.objects.all()

        cliente = self.request.query_params.get('cliente')
        estado = self.request.query_params.get('estado')
        ordering = self.request.query_params.get('ordering')

        if cliente:
            queryset = queryset.filter(
                cliente_id=cliente
            )

        if estado == 'true':
            queryset = queryset.filter(
                estado=True
            )

        elif estado == 'false':
            queryset = queryset.filter(
                estado=False
            )

        if ordering:

            campos_permitidos = [
                'total',
                '-total',
                'fecha',
                '-fecha'
            ]

            if ordering not in campos_permitidos:
                raise ValidationError({
                    'ordering':
                    'El campo de ordenamiento no es válido.'
                })

            queryset = queryset.order_by(ordering)

        return queryset
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[
            IsAuthenticated,
            IsStaffUser
        ]
    )
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        pedido = self.get_object()
        pedido = cancelar_pedido(pedido)
        serializer = self.get_serializer(pedido)
        return Response(serializer.data)
    @action(
        detail=False,
        methods=['get']
    )
    def activos(self, request):

        queryset = self.get_queryset().exclude(
            estado='cancelado'
        )

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = self.get_serializer(
            queryset,
            many=True
        )

        return Response(serializer.data)
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        pedido = self.get_object()

        serializer = CambiarEstadoPedidoSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        nuevo_estado = serializer.validated_data['estado']

        pedido = cambiar_estado_pedido(
            pedido,
            nuevo_estado
        )

        serializer_respuesta = self.get_serializer(pedido)

        return Response(serializer_respuesta.data)
    def destroy(self, request, *args, **kwargs):
            return Response(
                {
                    'detail':
                    'Los pedidos no pueden eliminarse. '
                    'Utilice la opción de cancelar el pedido.'
                },
                status=405
            )
class ProductoViewSet(ModelViewSet):

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    filter_backends = [
        DjangoFilterBackend,
        OrderingFilter,
    ]

    filterset_class = ProductoFilter
    ordering_fields = [
        'nombre',
        'precio',
        'stock',
    ]

    ordering = ['id']
    def get_permissions(self):

        print(
            "USUARIO:",
            self.request.user,
            "STAFF:",
            self.request.user.is_staff,
            "SUPERUSER:",
            self.request.user.is_superuser,
            "ACTION:",
            self.action
        )

        if self.action in [
            'create',
            'update',
            'partial_update',
            'destroy',
            'activar',
            'desactivar',
        ]:
            return [
                IsAuthenticated(),
                IsStaffUser()
            ]

        return [
            IsAuthenticated()
        ]
    def get_serializer_class(self):

        if self.action in ['list', 'activos']:
            return ProductoListaSerializer

        if self.action == 'retrieve':
            return ProductoDetalleSerializer

        if self.action == 'create':
            return ProductoCrearSerializer

        if self.action in ['update', 'partial_update']:
            return ProductoActualizarSerializer

        return ProductoSerializer
    def get_queryset(self):

        queryset = Producto.objects.all()


        ordering = self.request.query_params.get('ordering')


        if ordering:

            campos_permitidos = [
                'nombre',
                'precio',
                'stock',
                '-nombre',
                '-precio',
                '-stock'
            ]

            if ordering not in campos_permitidos:
                raise ValidationError({
                    'ordering': 'El campo de ordenamiento no es válido.'
                })

            queryset = queryset.order_by(ordering)

        return queryset
    @action(
        detail=False,
        methods=['get']
    )
    def activos(self, request):

        queryset = self.get_queryset().filter(
            estado=True
        )

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True
            )

            return self.get_paginated_response(
                serializer.data
            )

        serializer = self.get_serializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, IsStaffUser]
    )
    def activar(self, request, pk=None):

        producto = self.get_object()

        if producto.estado:
            return Response(
                {
                    'detail': 'El producto ya está activo.'
                },
                status=400
            )

        producto.estado = True
        producto.save(update_fields=['estado'])

        serializer = self.get_serializer(producto)

        return Response(serializer.data)
    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated, IsStaffUser]
    )
    def desactivar(self, request, pk=None):

        producto = self.get_object()

        if not producto.estado:
            return Response(
                {
                    'detail': 'El producto ya está inactivo.'
                },
                status=400
            )

        producto.estado = False
        producto.save(update_fields=['estado'])

        serializer = self.get_serializer(producto)

        return Response(serializer.data)
    def destroy(self, request, *args, **kwargs):
        producto = self.get_object()

        try:
            producto.delete()

        except ProtectedError:
            return Response(
                {
                    'detail':
                    'No se puede eliminar el producto porque '
                    'está asociado a uno o más pedidos.'
                },
                status=400
            )

        return Response(
            status=204
    )
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin
)


class ProductoListaAPIView(
    ListModelMixin,
    CreateModelMixin,
    GenericAPIView
):

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class ProductoDetalleAPIView(
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    GenericAPIView
):

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

class ProductoActualizarAPIView(
    UpdateModelMixin,
    GenericAPIView
):

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

class ProductoEliminarAPIView(
    DestroyModelMixin,
    GenericAPIView
):

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

class ProductoListaCrearAPIView(
    ListModelMixin,
    CreateModelMixin,
    GenericAPIView
):

    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAdminUser])
@api_view(['GET'])
@permission_classes([IsAdminUser])
def prueba_email(request):
    from django.conf import settings
    return Response({
        'EMAIL_HOST_existe': bool(settings.MAILERS['default']['OPTIONS'].get('host')),
        'EMAIL_PORT_existe': bool(settings.MAILERS['default']['OPTIONS'].get('port')),
        'EMAIL_HOST_USER_existe': bool(settings.MAILERS['default']['OPTIONS'].get('username')),
        'EMAIL_HOST_PASSWORD_existe': bool(settings.MAILERS['default']['OPTIONS'].get('password')),
    })