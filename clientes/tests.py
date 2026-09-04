from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import serializers
from unittest.mock import patch
from .models import Cliente, Producto, Pedido, DetallePedido
from .serializers import PedidoSerializer
from rest_framework.test import APIClient
from .services import crear_pedido, cancelar_pedido,cambiar_estado_pedido

class CrearPedidoTest(TestCase):

    def test_crear_pedido_calcula_total_y_descuenta_stock(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Test',
            email='test@example.com',
            telefono='70000000',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Laptop Test',
            precio=Decimal('4500.00'),
            stock=10,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido de prueba',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 2,
                }
            ]
        }

        pedido = crear_pedido(validated_data)

        pedido.refresh_from_db()
        producto.refresh_from_db()

        self.assertEqual(
            pedido.total,
            Decimal('9000.00')
        )

        self.assertEqual(
            producto.stock,
            8
        )

        self.assertEqual(
            pedido.detalles.count(),
            1
        )

    def test_crear_pedido_falla_si_no_hay_stock(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Test',
            email='stock@example.com',
            telefono='71111111',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Sin Stock',
            precio=Decimal('100.00'),
            stock=3,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido sin stock suficiente',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 5,
                }
            ]
        }

        with self.assertRaises(serializers.ValidationError) as context:
            crear_pedido(validated_data)

        self.assertIn(
            'No hay suficiente stock',
            str(context.exception)
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            3
        )
    def test_crear_pedido_hace_rollback_si_un_producto_no_tiene_stock(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Rollback',
            email='rollback@example.com',
            telefono='72222222',
            empresa='Empresa Test',
            estado=True
        )

        laptop = Producto.objects.create(
            nombre='Laptop Rollback',
            precio=Decimal('4500.00'),
            stock=10,
            estado=True
        )

        mouse = Producto.objects.create(
            nombre='Mouse Rollback',
            precio=Decimal('80.00'),
            stock=3,
            estado=True
        )

        pedidos_antes = Pedido.objects.count()

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido para probar rollback',
            'detalles': [
                {
                    'producto': laptop,
                    'cantidad': 2,
                },
                {
                    'producto': mouse,
                    'cantidad': 5,
                }
            ]
        }

        with self.assertRaises(serializers.ValidationError):
            crear_pedido(validated_data)

        laptop.refresh_from_db()
        mouse.refresh_from_db()

        self.assertEqual(laptop.stock, 10)
        self.assertEqual(mouse.stock, 3)

        self.assertEqual(
            Pedido.objects.count(),
            pedidos_antes
        )

    def test_no_se_puede_crear_pedido_con_producto_inactivo(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Test',
            email='inactivo@example.com',
            telefono='73333333',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Inactivo',
            precio=Decimal('100.00'),
            stock=10,
            estado=False
        )

        data = {
            'cliente': cliente.id,
            'descripcion': 'Pedido con producto inactivo',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                }
            ]
        }

        serializer = PedidoSerializer(
            data=data
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            'detalles',
            serializer.errors
        )

        self.assertIn(
            'está inactivo',
            str(serializer.errors)
        )

    def test_no_se_puede_crear_pedido_con_cliente_inactivo(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Inactivo',
            email='clienteinactivo@example.com',
            telefono='74444444',
            empresa='Empresa Test',
            estado=False
        )

        producto = Producto.objects.create(
            nombre='Producto Test',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        data = {
            'cliente': cliente.id,
            'descripcion': 'Pedido con cliente inactivo',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                }
            ]
        }

        serializer = PedidoSerializer(
            data=data
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            'cliente',
            serializer.errors
        )

        self.assertIn(
            'está inactivo',
            str(serializer.errors)
        )
    def test_no_se_puede_crear_pedido_con_cantidad_cero(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Test',
            email='cantidadcero@example.com',
            telefono='75555555',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Test',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        data = {
            'cliente': cliente.id,
            'descripcion': 'Pedido con cantidad cero',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 0
                }
            ]
        }

        serializer = PedidoSerializer(
            data=data
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            'detalles',
            serializer.errors
        )
    def test_no_se_puede_crear_pedido_con_cantidad_negativa(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Test',
            email='cantidadnegativa@example.com',
            telefono='76666666',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Test',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        data = {
            'cliente': cliente.id,
            'descripcion': 'Pedido con cantidad negativa',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': -2
                }
            ]
        }

        serializer = PedidoSerializer(
            data=data
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            'detalles',
            serializer.errors
        )
class CancelarPedidoTest(TestCase):

    def test_cancelar_pedido_restaura_stock(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Cancelación',
            email='cancelacion@example.com',
            telefono='73333333',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Cancelación',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido para cancelar',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 4,
                }
            ]
        }

        pedido = crear_pedido(validated_data)

        producto.refresh_from_db()

        self.assertEqual(producto.stock, 6)

        cancelar_pedido(pedido)

        producto.refresh_from_db()
        pedido.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

        self.assertEqual(
            pedido.estado,
            Pedido.CANCELADO
        )

        self.assertEqual(
            pedido.detalles.count(),
            1
        )
    def test_no_se_puede_cancelar_un_pedido_dos_veces(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Doble Cancelación',
            email='doble-cancelacion@example.com',
            telefono='74444444',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Doble Cancelación',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido para probar doble cancelación',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 4,
                }
            ]
        }

        pedido = crear_pedido(validated_data)

        producto.refresh_from_db()
        self.assertEqual(producto.stock, 6)

        cancelar_pedido(pedido)

        producto.refresh_from_db()
        self.assertEqual(producto.stock, 10)

        with self.assertRaises(serializers.ValidationError) as context:
            cancelar_pedido(pedido)

        self.assertIn(
            'ya está cancelado',
            str(context.exception)
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )
    def test_no_se_puede_cancelar_un_pedido_enviado(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Enviado',
            email='enviado@example.com',
            telefono='75555555',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Enviado',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido enviado',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 4,
                }
            ]
        }

        pedido = crear_pedido(validated_data)

        pedido.estado = Pedido.ENVIADO
        pedido.save(update_fields=['estado'])

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            6
        )

        with self.assertRaises(serializers.ValidationError) as context:
            cancelar_pedido(pedido)

        self.assertIn(
            'no puede cancelarse',
            str(context.exception)
        )

        pedido.refresh_from_db()
        producto.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.ENVIADO
        )

        self.assertEqual(
            producto.stock,
            6
        )
    def test_no_se_puede_cancelar_un_pedido_entregado(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Entregado',
            email='entregado@example.com',
            telefono='76666666',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Entregado',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido entregado',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 4,
                }
            ]
        }

        pedido = crear_pedido(validated_data)

        pedido.estado = Pedido.ENTREGADO
        pedido.save(update_fields=['estado'])

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            6
        )

        with self.assertRaises(serializers.ValidationError) as context:
            cancelar_pedido(pedido)

        self.assertIn(
            'no puede cancelarse',
            str(context.exception)
        )

        pedido.refresh_from_db()
        producto.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.ENTREGADO
        )

        self.assertEqual(
            producto.stock,
            6
        )
    def test_cancelar_pedido_revierte_cambios_si_ocurre_un_error(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Rollback',
            email='rollback-cancelar@example.com',
            telefono='77777777',
            empresa='Empresa Test',
            estado=True
        )

        producto = Producto.objects.create(
            nombre='Producto Rollback',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        validated_data = {
            'cliente': cliente,
            'descripcion': 'Pedido para probar rollback',
            'detalles': [
                {
                    'producto': producto,
                    'cantidad': 4,
                }
            ]
        }

        pedido = crear_pedido(validated_data)

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            6
        )

        with patch(
            'clientes.services.Producto.save',
            side_effect=Exception('Error simulado')
        ):
            with self.assertRaises(Exception):
                cancelar_pedido(pedido)

        producto.refresh_from_db()
        pedido.refresh_from_db()

        self.assertEqual(
            producto.stock,
            6
        )

        self.assertEqual(
            pedido.estado,
            Pedido.PENDIENTE
        )
class CambiarEstadoPedidoTest(TestCase):

    def test_pedido_pendiente_puede_confirmarse(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Estado',
            email='estado@example.com',
            telefono='75555555',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido para probar estado',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido = cambiar_estado_pedido(
            pedido,
            Pedido.CONFIRMADO
        )

        pedido.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.CONFIRMADO
        )
    def test_pedido_no_puede_saltar_de_pendiente_a_enviado(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Estado Invalido',
            email='estado-invalido@example.com',
            telefono='76666666',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido para probar transición inválida',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        with self.assertRaises(serializers.ValidationError) as context:
            cambiar_estado_pedido(
                pedido,
                Pedido.ENVIADO
            )

        self.assertIn(
            'No se puede cambiar',
            str(context.exception)
        )

        pedido.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.PENDIENTE
        )
    def test_pedido_puede_completar_todas_las_transiciones(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Ciclo Estados',
            email='ciclo-estados@example.com',
            telefono='77777777',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido para probar ciclo completo',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido = cambiar_estado_pedido(
            pedido,
            Pedido.CONFIRMADO
        )

        self.assertEqual(
            pedido.estado,
            Pedido.CONFIRMADO
        )

        pedido = cambiar_estado_pedido(
            pedido,
            Pedido.PREPARANDO
        )

        self.assertEqual(
            pedido.estado,
            Pedido.PREPARANDO
        )

        pedido = cambiar_estado_pedido(
            pedido,
            Pedido.ENVIADO
        )

        self.assertEqual(
            pedido.estado,
            Pedido.ENVIADO
        )

        pedido = cambiar_estado_pedido(
            pedido,
            Pedido.ENTREGADO
        )

        self.assertEqual(
            pedido.estado,
            Pedido.ENTREGADO
        )
    def test_pedido_entregado_no_puede_volver_a_preparando(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Pedido Entregado',
            email='entregado@example.com',
            telefono='78888888',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido entregado',
            total=Decimal('100.00'),
            estado=Pedido.ENTREGADO
        )

        with self.assertRaises(serializers.ValidationError) as context:
            cambiar_estado_pedido(
                pedido,
                Pedido.PREPARANDO
            )

        self.assertIn(
            'No se puede cambiar',
            str(context.exception)
        )

        pedido.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.ENTREGADO
        )
    def test_pedido_cancelado_no_puede_cambiar_de_estado(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Pedido Cancelado',
            email='cancelado-estado@example.com',
            telefono='79999999',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido cancelado',
            total=Decimal('100.00'),
            estado=Pedido.CANCELADO
        )

        with self.assertRaises(serializers.ValidationError) as context:
            cambiar_estado_pedido(
                pedido,
                Pedido.CONFIRMADO
            )

        self.assertIn(
            'No se puede cambiar',
            str(context.exception)
        )

        pedido.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.CANCELADO
        )
    def test_no_se_puede_cambiar_a_un_estado_inexistente(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Estado Inexistente',
            email='estado-inexistente@example.com',
            telefono='70000001',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido para probar estado inexistente',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        with self.assertRaises(serializers.ValidationError) as context:
            cambiar_estado_pedido(
                pedido,
                'estado_inexistente'
            )

        self.assertIn(
            'no es válido',
            str(context.exception)
        )

        pedido.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.PENDIENTE
        )
    def test_cambiar_estado_revierte_cambios_si_ocurre_un_error(self):
        cliente = Cliente.objects.create(
            nombre='Cliente Rollback Estado',
            email='rollback-estado@example.com',
            telefono='70000002',
            empresa='Empresa Test',
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido para probar rollback de estado',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        with patch(
            'clientes.services.Pedido.save',
            side_effect=Exception('Error simulado')
        ):
            with self.assertRaises(Exception):
                cambiar_estado_pedido(
                    pedido,
                    Pedido.CONFIRMADO
                )

        pedido.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.PENDIENTE
        )
class PedidoAPITest(TestCase):

    def setUp(self):
        self.client_api = APIClient()

        self.usuario = User.objects.create_user(
            username='usuario_test',
            password='password123'
        )

        self.cliente = Cliente.objects.create(
            nombre='Cliente API',
            email='cliente-api@example.com',
            telefono='70000001',
            empresa='Empresa API',
            estado=True
        )

        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido API',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

    def test_usuario_autenticado_puede_consultar_pedidos(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get('/pedidos/')

        self.assertEqual(
            response.status_code,
            200
        )
    def test_usuario_no_autenticado_no_puede_consultar_pedidos(self):
        response = self.client_api.get('/pedidos/')

        self.assertEqual(
            response.status_code,
            401
        )

    def test_usuario_autenticado_no_staff_no_puede_crear_pedido(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido no autorizado',
            'detalles': []
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            403
        )

    def test_usuario_staff_puede_crear_pedido(self):
        usuario_staff = User.objects.create_user(
            username='staff_test',
            password='password123',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto API',
            precio=Decimal('200.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido creado mediante API',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 3
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            201
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            7
        )

        self.assertEqual(
            Decimal(str(response.data['total'])),
            Decimal('600.00')
        )

    def test_usuario_staff_puede_actualizar_pedido(self):
        usuario_staff = User.objects.create_user(
            username='staff_update',
            password='password123',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        data = {
            'descripcion': 'Pedido actualizado mediante API'
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        pedido = Pedido.objects.get(pk=self.pedido.id)

        self.assertEqual(
            pedido.descripcion,
            'Pedido actualizado mediante API'
        )

    def test_usuario_staff_puede_actualizar_detalles_y_ajustar_stock(self):
        usuario_staff = User.objects.create_user(
            username='staff_detalles',
            password='password123',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Laptop actualización',
            precio=Decimal('1000.00'),
            stock=10,
            estado=True
        )

        # Crear el pedido inicialmente con 2 unidades
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido con detalles',
            total=Decimal('2000.00'),
            estado=Pedido.PENDIENTE
        )

        from .models import DetallePedido

        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=2,
            precio=producto.precio
        )

        # El stock debe quedar en 8
        producto.stock -= 2
        producto.save()

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        data = {
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 3
                }
            ]
        }

        response = self.client_api.patch(
            f'/pedidos/{pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        producto.refresh_from_db()
        pedido.refresh_from_db()

        self.assertEqual(
            producto.stock,
            7
        )

        self.assertEqual(
            pedido.total,
            Decimal('3000.00')
        )

        self.assertEqual(
            pedido.detalles.count(),
            1
        )

        detalle = pedido.detalles.first()

        self.assertEqual(
            detalle.cantidad,
            3
        )

    def test_usuario_no_staff_no_puede_actualizar_pedido(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        data = {
            'descripcion': 'Intento de actualización no autorizado'
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            403
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.descripcion,
            'Pedido API'
        )
    def test_usuario_staff_no_puede_eliminar_pedido(self):
        usuario_staff = User.objects.create_user(
            username='staff_delete',
            password='password123',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        response = self.client_api.delete(
            f'/pedidos/{self.pedido.id}/'
        )

        self.assertEqual(
            response.status_code,
            405
        )

        self.assertTrue(
            Pedido.objects.filter(
                pk=self.pedido.id
            ).exists()
        )
    def test_usuario_staff_puede_cancelar_pedido(self):
        usuario_staff = User.objects.create_user(
            username='staff_cancelar',
            password='password123',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto cancelar API',
            precio=Decimal('500.00'),
            stock=10,
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido para cancelar',
            total=Decimal('1000.00'),
            estado=Pedido.PENDIENTE
        )

        from .models import DetallePedido

        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=2,
            precio=producto.precio
        )

        # Simulamos el stock descontado por el pedido
        producto.stock -= 2
        producto.save()

        self.assertEqual(
            producto.stock,
            8
        )

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        response = self.client_api.post(
            f'/pedidos/{pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        pedido.refresh_from_db()
        producto.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.CANCELADO
        )

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_no_staff_no_puede_cancelar_pedido(self):
        producto = Producto.objects.create(
            nombre='Producto cancelar no staff',
            precio=Decimal('500.00'),
            stock=10,
            estado=True
        )

        pedido = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido protegido',
            total=Decimal('1000.00'),
            estado=Pedido.PENDIENTE
        )

        from .models import DetallePedido

        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=2,
            precio=producto.precio
        )

        # Simulamos el stock descontado
        producto.stock -= 2
        producto.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            403
        )

        pedido.refresh_from_db()
        producto.refresh_from_db()

        self.assertEqual(
            pedido.estado,
            Pedido.PENDIENTE
        )

        self.assertEqual(
            producto.stock,
            8
        )
    def test_usuario_staff_cambiar_estado_no_modifica_stock(self):
        usuario_staff = User.objects.create_user(
            username='staff_estado_stock',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Estado',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=3,
            precio=producto.precio
        )

        stock_inicial = producto.stock

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            {
                'estado': Pedido.CONFIRMADO
            },
            format='json'
        )
        self.assertEqual(
            response.status_code,
            200,
            msg=f"Status: {response.status_code} - Data: {response.data}"
        )

        producto.refresh_from_db()

        self.assertEqual(producto.stock, stock_inicial)
        self.assertEqual(producto.stock, 10)

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CONFIRMADO
        )

    def test_usuario_no_staff_no_puede_cambiar_estado_pedido(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        data = {
            'estado': Pedido.CONFIRMADO
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            403
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )
    def test_usuario_staff_no_puede_saltar_estado_pedido(self):
        staff = User.objects.create_user(
            username='staff_salto',
            password='123456',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'estado': Pedido.ENVIADO
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

    def test_usuario_staff_no_puede_enviar_estado_invalido(self):
        staff = User.objects.create_user(
            username='staff_estado_invalido',
            password='123456',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'estado': 'finalizado'
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )
    def test_usuario_no_autenticado_no_puede_cambiar_estado_pedido(self):
        data = {
            'estado': Pedido.CONFIRMADO
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            401
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

    def test_usuario_staff_no_puede_cancelar_pedido_enviado(self):
        staff = User.objects.create_user(
            username='staff_cancelar_enviado',
            password='123456',
            is_staff=True
        )

        self.pedido.estado = Pedido.ENVIADO
        self.pedido.save(update_fields=['estado'])

        self.client_api.force_authenticate(
            user=staff
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.ENVIADO
        )
    def test_usuario_staff_no_puede_cancelar_pedido_entregado(self):
        staff = User.objects.create_user(
            username='staff_cancelar_entregado',
            password='123456',
            is_staff=True
        )

        self.pedido.estado = Pedido.ENTREGADO
        self.pedido.save(update_fields=['estado'])

        self.client_api.force_authenticate(
            user=staff
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.ENTREGADO
        )
    def test_usuario_staff_cancelar_pedido_restaura_stock_de_varios_productos(self):
        from .models import DetallePedido

        staff = User.objects.create_user(
            username='staff_cancelar_varios',
            password='123456',
            is_staff=True
        )

        producto1 = Producto.objects.create(
            nombre='Producto 1',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        producto2 = Producto.objects.create(
            nombre='Producto 2',
            precio=Decimal('200.00'),
            stock=20,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto1,
            cantidad=3,
            precio=producto1.precio
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto2,
            cantidad=5,
            precio=producto2.precio
        )

        producto1.stock -= 3
        producto1.save(update_fields=['stock'])

        producto2.stock -= 5
        producto2.save(update_fields=['stock'])

        self.client_api.force_authenticate(
            user=staff
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.pedido.refresh_from_db()
        producto1.refresh_from_db()
        producto2.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CANCELADO
        )

        self.assertEqual(
            producto1.stock,
            10
        )

        self.assertEqual(
            producto2.stock,
            20
        )
    def test_usuario_staff_no_puede_cancelar_pedido_ya_cancelado(self):
        staff = User.objects.create_user(
            username='staff_cancelar_dos_veces',
            password='123456',
            is_staff=True
        )

        self.pedido.estado = Pedido.CANCELADO
        self.pedido.save(update_fields=['estado'])

        self.client_api.force_authenticate(
            user=staff
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CANCELADO
        )
    def test_usuario_staff_no_puede_actualizar_pedido_sin_stock(self):
        from .models import DetallePedido

        staff = User.objects.create_user(
            username='staff_actualizar_sin_stock',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto sin stock suficiente',
            precio=Decimal('100.00'),
            stock=8,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=2,
            precio=producto.precio
        )

        producto.stock -= 2
        producto.save(update_fields=['stock'])

        self.pedido.total = Decimal('200.00')
        self.pedido.save(update_fields=['total'])

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 20
                }
            ]
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()
        producto.refresh_from_db()

        detalle = self.pedido.detalles.first()

        self.assertEqual(
            self.pedido.total,
            Decimal('200.00')
        )

        self.assertEqual(
            producto.stock,
            6
        )

        self.assertEqual(
            detalle.cantidad,
            2
        )

    def test_usuario_staff_no_puede_actualizar_pedido_con_producto_inactivo(self):
        staff = User.objects.create_user(
            username='staff_producto_inactivo',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Inactivo',
            precio=Decimal('100.00'),
            stock=10,
            estado=False
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                }
            ]
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.detalles.count(),
            0
        )

    def test_usuario_staff_no_puede_repetir_producto_en_pedido(self):
        staff = User.objects.create_user(
            username='staff_producto_duplicado',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Duplicado',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                },
                {
                    'producto': producto.id,
                    'cantidad': 3
                }
            ]
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.detalles.count(),
            0
        )
    def test_usuario_staff_no_puede_actualizar_pedido_con_cantidad_cero(self):
        staff = User.objects.create_user(
            username='staff_cantidad_cero',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Cantidad Cero',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 0
                }
            ]
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.detalles.count(),
            0
        )

    def test_usuario_staff_no_puede_actualizar_pedido_con_cantidad_negativa(self):
        staff = User.objects.create_user(
            username='staff_cantidad_negativa',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Cantidad Negativa',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': -5
                }
            ]
        }

        response = self.client_api.patch(
            f'/pedidos/{self.pedido.id}/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.detalles.count(),
            0
        )
    def test_usuario_staff_no_puede_crear_pedido_para_cliente_inactivo(self):
        staff = User.objects.create_user(
            username='staff_cliente_inactivo',
            password='123456',
            is_staff=True
        )

        cliente_inactivo = Cliente.objects.create(
            nombre='Cliente Inactivo',
            email='clienteinactivo@test.com',
            telefono='70000001',
            empresa='Empresa Inactiva',
            estado=False
        )

        producto = Producto.objects.create(
            nombre='Producto Cliente Inactivo',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': cliente_inactivo.id,
            'descripcion': 'Pedido de cliente inactivo',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido de cliente inactivo'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_staff_no_puede_crear_pedido_con_producto_inactivo(self):
        staff = User.objects.create_user(
            username='staff_crear_producto_inactivo',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Inactivo Creacion',
            precio=Decimal('100.00'),
            stock=10,
            estado=False
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido con producto inactivo',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido con producto inactivo'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_staff_no_puede_crear_pedido_con_cantidad_cero(self):
        staff = User.objects.create_user(
            username='staff_crear_cantidad_cero',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Cantidad Cero Creacion',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido con cantidad cero',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 0
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido con cantidad cero'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_staff_no_puede_crear_pedido_con_cantidad_negativa(self):
        staff = User.objects.create_user(
            username='staff_crear_cantidad_negativa',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Cantidad Negativa Creacion',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido con cantidad negativa',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': -5
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido con cantidad negativa'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_staff_no_puede_crear_pedido_con_producto_repetido(self):
        staff = User.objects.create_user(
            username='staff_crear_producto_repetido',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Repetido Creacion',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido con producto repetido',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                },
                {
                    'producto': producto.id,
                    'cantidad': 3
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido con producto repetido'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_staff_no_puede_crear_pedido_sin_stock(self):
        staff = User.objects.create_user(
            username='staff_crear_sin_stock',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Sin Stock Creacion',
            precio=Decimal('100.00'),
            stock=2,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido sin stock',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 5
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido sin stock'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            2
        )

    def test_usuario_no_autenticado_no_puede_crear_pedido(self):
        producto = Producto.objects.create(
            nombre='Producto Usuario No Autenticado',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido sin autenticacion',
            'detalles': [
                {
                    'producto': producto.id,
                    'cantidad': 2
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            401
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido sin autenticacion'
            ).count(),
            0
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            10
        )

    def test_usuario_no_autenticado_no_puede_cancelar_pedido(self):
        producto = Producto.objects.create(
            nombre='Producto Cancelacion No Autenticado',
            precio=Decimal('100.00'),
            stock=8,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=2,
            precio=Decimal('100.00')
        )

        producto.stock -= 2
        producto.save(update_fields=['stock'])

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/',
            format='json'
        )

        self.assertEqual(
            response.status_code,
            401
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            6
        )

    def test_usuario_staff_no_puede_crear_pedido_y_hace_rollback_si_un_producto_no_tiene_stock(self):
        staff = User.objects.create_user(
            username='staff_crear_rollback_stock',
            password='123456',
            is_staff=True
        )

        producto_a = Producto.objects.create(
            nombre='Producto A Rollback',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        producto_b = Producto.objects.create(
            nombre='Producto B Rollback',
            precio=Decimal('200.00'),
            stock=1,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido rollback API',
            'detalles': [
                {
                    'producto': producto_a.id,
                    'cantidad': 2
                },
                {
                    'producto': producto_b.id,
                    'cantidad': 5
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            Pedido.objects.filter(
                descripcion='Pedido rollback API'
            ).count(),
            0
        )

        producto_a.refresh_from_db()
        producto_b.refresh_from_db()

        self.assertEqual(
            producto_a.stock,
            10
        )

        self.assertEqual(
            producto_b.stock,
            1
        )

    def test_usuario_staff_puede_crear_pedido_con_varios_productos(self):
        staff = User.objects.create_user(
            username='staff_crear_varios_productos',
            password='123456',
            is_staff=True
        )

        producto_a = Producto.objects.create(
            nombre='Producto A Varios',
            precio=Decimal('100.00'),
            stock=10,
            estado=True
        )

        producto_b = Producto.objects.create(
            nombre='Producto B Varios',
            precio=Decimal('250.00'),
            stock=8,
            estado=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido con varios productos',
            'detalles': [
                {
                    'producto': producto_a.id,
                    'cantidad': 2
                },
                {
                    'producto': producto_b.id,
                    'cantidad': 3
                }
            ]
        }

        response = self.client_api.post(
            '/pedidos/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            201
        )

        pedido = Pedido.objects.get(
            descripcion='Pedido con varios productos'
        )

        self.assertEqual(
            pedido.total,
            Decimal('950.00')
        )

        self.assertEqual(
            pedido.detalles.count(),
            2
        )

        producto_a.refresh_from_db()
        producto_b.refresh_from_db()

        self.assertEqual(
            producto_a.stock,
            8
        )

        self.assertEqual(
            producto_b.stock,
            5
        )


    def test_usuario_autenticado_puede_consultar_pedidos_activos(self):
        pedido_activo = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Activo',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_cancelado = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Cancelado',
            total=Decimal('200.00'),
            estado=Pedido.CANCELADO
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/activos/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        ids = [
            pedido['id']
            for pedido in resultados
        ]

        self.assertIn(
            pedido_activo.id,
            ids
        )

        self.assertNotIn(
            pedido_cancelado.id,
            ids
        )

    def test_usuario_no_autenticado_no_puede_consultar_pedidos_activos(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Activo No Autenticado',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        response = self.client_api.get(
            '/pedidos/activos/'
        )

        self.assertEqual(
            response.status_code,
            401
        )

    def test_usuario_no_staff_puede_consultar_pedidos_activos(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Activo Usuario Normal',
            total=Decimal('150.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/activos/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        ids = [
            pedido['id']
            for pedido in resultados
        ]

        self.assertIn(
            self.pedido.id,
            ids
        )
    def test_usuario_autenticado_no_puede_consultar_pedido_inexistente(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/999999/'
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_usuario_staff_no_puede_cancelar_pedido_inexistente(self):
        staff = User.objects.create_user(
            username='staff_cancelar_inexistente',
            password='123456',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        response = self.client_api.post(
            '/pedidos/999999/cancelar/',
            format='json'
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_usuario_staff_puede_cambiar_estado_y_se_guarda(self):
        staff = User.objects.create_user(
            username='staff_cambiar_estado_guardado',
            password='123456',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'estado': Pedido.CONFIRMADO
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CONFIRMADO
        )

    def test_usuario_staff_no_puede_cambiar_pedido_a_estado_invalido(self):
        staff = User.objects.create_user(
            username='staff_estado_invalido',
            password='123456',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=staff
        )

        data = {
            'estado': 'estado_inexistente'
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

    def test_usuario_no_autenticado_no_puede_cambiar_estado_pedido(self):
        estado_original = self.pedido.estado

        data = {
            'estado': Pedido.CONFIRMADO
        }

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            data,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            401
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            estado_original
        )

    def test_usuario_staff_no_puede_cambiar_estado_pedido_inexistente(self):
        usuario_staff = User.objects.create_user(
            username='staff_estado_inexistente',
            password='123456',
            is_staff=True
        )

        self.client_api.force_authenticate(
            user=usuario_staff
        )

        response = self.client_api.post(
            '/api/pedidos/99999/cambiar_estado/',
            {
                'estado': Pedido.CONFIRMADO
            },
            format='json'
        )

        self.assertEqual(response.status_code, 404)

    def test_usuario_staff_cambiar_estado_no_modifica_stock(self):
        staff = User.objects.create_user(
            username='staff_estado_stock',
            password='123456',
            is_staff=True
        )

        producto = Producto.objects.create(
            nombre='Producto Estado',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=3,
            precio=producto.precio
        )

        self.client_api.force_authenticate(user=staff)

        response = self.client_api.post(
            f'/pedidos/{self.pedido.pk}/cambiar_estado/',
            {
                'estado': Pedido.CONFIRMADO
            },
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200,
            msg=f'URL: /pedidos/{self.pedido.pk}/cambiar_estado/'
        )

        producto.refresh_from_db()

        self.assertEqual(producto.stock, 10)

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CONFIRMADO
        )

    def test_usuario_autenticado_puede_filtrar_pedidos_por_estado(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Confirmado',
            total=Decimal('200.00'),
            estado=Pedido.CONFIRMADO
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?estado=pendiente'
        )

        self.assertEqual(response.status_code, 200)

        resultados = response.data['results']

        self.assertEqual(len(resultados), 1)

        self.assertEqual(
            resultados[0]['estado'],
            Pedido.PENDIENTE
        )

    def test_usuario_autenticado_puede_filtrar_pedidos_por_total_minimo(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Menor',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Mayor',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?total__gte=150'
        )

        self.assertEqual(response.status_code, 200)

        resultados = response.data['results']

        self.assertEqual(len(resultados), 1)

        self.assertEqual(
            resultados[0]['descripcion'],
            'Pedido Mayor'
        )

        self.assertEqual(
            Decimal(resultados[0]['total']),
            Decimal('200.00')
        )

    def test_usuario_autenticado_puede_ordenar_pedidos_por_total_descendente(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 100',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 300',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 200',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?ordering=-total'
        )

        self.assertEqual(response.status_code, 200)

        resultados = response.data['results']

        self.assertEqual(len(resultados), 4)

        self.assertEqual(
            Decimal(resultados[0]['total']),
            Decimal('300.00')
        )

        self.assertEqual(
            Decimal(resultados[1]['total']),
            Decimal('200.00')
        )

        self.assertEqual(
            Decimal(resultados[2]['total']),
            Decimal('100.00')
        )

        self.assertEqual(
            Decimal(resultados[3]['total']),
            Decimal('100.00')
        )

    def test_usuario_autenticado_puede_ordenar_pedidos_por_total_ascendente(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 300',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 200',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 100',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?ordering=total'
        )

        self.assertEqual(response.status_code, 200)

        resultados = response.data['results']

        self.assertEqual(len(resultados), 4)

        self.assertEqual(
            Decimal(resultados[0]['total']),
            Decimal('100.00')
        )

        self.assertEqual(
            Decimal(resultados[1]['total']),
            Decimal('100.00')
        )

        self.assertEqual(
            Decimal(resultados[2]['total']),
            Decimal('200.00')
        )

        self.assertEqual(
            Decimal(resultados[3]['total']),
            Decimal('300.00')
        )

    def test_usuario_autenticado_puede_ordenar_pedidos_por_fecha_ascendente(self):
        pedido_antiguo = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Antiguo',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_reciente = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Reciente',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.filter(
            pk=pedido_antiguo.pk
        ).update(
            fecha='2026-08-01'
        )

        Pedido.objects.filter(
            pk=pedido_reciente.pk
        ).update(
            fecha='2026-08-10'
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?ordering=fecha'
        )

        self.assertEqual(response.status_code, 200)

        resultados = response.data['results']

        self.assertEqual(len(resultados), 3)

        self.assertEqual(
            resultados[0]['descripcion'],
            'Pedido Antiguo'
        )

        self.assertEqual(
            resultados[1]['descripcion'],
            'Pedido Reciente'
        )

        self.assertEqual(
            resultados[2]['descripcion'],
            'Pedido API'
        )

    def test_usuario_autenticado_puede_ordenar_pedidos_por_fecha_descendente(self):
        pedido_antiguo = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Antiguo',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_reciente = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Reciente',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.filter(
            pk=pedido_antiguo.pk
        ).update(
            fecha='2026-08-01'
        )

        Pedido.objects.filter(
            pk=pedido_reciente.pk
        ).update(
            fecha='2026-08-10'
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?ordering=-fecha'
        )

        self.assertEqual(response.status_code, 200)

        resultados = response.data['results']

        self.assertEqual(len(resultados), 3)

        self.assertEqual(
            resultados[0]['descripcion'],
            'Pedido API'
        )

        self.assertEqual(
            resultados[1]['descripcion'],
            'Pedido Reciente'
        )

        self.assertEqual(
            resultados[2]['descripcion'],
            'Pedido Antiguo'
        )

    def test_usuario_autenticado_puede_paginar_pedidos(self):
        for i in range(15):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/'
        )
     
        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            16
        )

        self.assertEqual(
            len(response.data['results']),
            5
        )

        self.assertIsNotNone(
            response.data['next']
        )

    def test_usuario_autenticado_puede_consultar_segunda_pagina_de_pedidos(self):
        for i in range(15):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page=2'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            16
        )

        self.assertEqual(
            len(response.data['results']),
            5
        )

        self.assertIsNotNone(
            response.data['previous']
        )

    def test_usuario_autenticado_puede_consultar_ultima_pagina_de_pedidos(self):
        for i in range(15):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page=4'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            16
        )

        self.assertEqual(
            len(response.data['results']),
            1
        )

        self.assertIsNone(
            response.data['next']
        )

        self.assertIsNotNone(
            response.data['previous']
        )

    def test_usuario_autenticado_puede_personalizar_page_size(self):
        for i in range(15):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page_size=10'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            16
        )

        self.assertEqual(
            len(response.data['results']),
            10
        )

        self.assertIsNotNone(
            response.data['next']
        )

    def test_usuario_autenticado_no_puede_superar_page_size_maximo(self):
        for i in range(60):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page_size=100'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            61
        )

        self.assertEqual(
            len(response.data['results']),
            50
        )

        self.assertIsNotNone(
            response.data['next']
        )

    def test_usuario_autenticado_puede_consultar_pedidos_con_page_size_cero(self):
        for i in range(10):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page_size=0'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            len(response.data['results']),
            5
        )
    def test_usuario_autenticado_page_size_negativo_usa_tamano_predeterminado(self):
        for i in range(10):
            Pedido.objects.create(
                cliente=self.cliente,
                descripcion=f'Pedido {i + 1}',
                total=Decimal('100.00'),
                estado=Pedido.PENDIENTE
            )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page_size=-1'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            len(response.data['results']),
            5
        )
    def test_usuario_autenticado_no_puede_consultar_pagina_inexistente(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?page=999'
        )

        self.assertEqual(
            response.status_code,
            404
        )
    def test_usuario_autenticado_puede_combinar_filtro_ordenamiento_y_paginacion(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pendiente 500',
            total=Decimal('500.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pendiente 400',
            total=Decimal('400.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pendiente 300',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Confirmado 600',
            total=Decimal('600.00'),
            estado=Pedido.CONFIRMADO
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?estado=pendiente&ordering=-total&page=2&page_size=2'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            4
        )

        self.assertEqual(
            len(response.data['results']),
            2
        )

        resultados = response.data['results']

        self.assertEqual(
            resultados[0]['total'],
            '300.00'
        )

        self.assertEqual(
            resultados[1]['total'],
            '100.00'
        )

    def test_usuario_autenticado_puede_combinar_filtro_ordenamiento_ascendente_y_paginacion(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pendiente 500',
            total=Decimal('500.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pendiente 400',
            total=Decimal('400.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pendiente 300',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Confirmado 600',
            total=Decimal('600.00'),
            estado=Pedido.CONFIRMADO
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?estado=pendiente&ordering=total&page=1&page_size=2'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            4
        )

        self.assertEqual(
            len(response.data['results']),
            2
        )

        resultados = response.data['results']

        self.assertEqual(
            resultados[0]['total'],
            '100.00'
        )

        self.assertEqual(
            resultados[1]['total'],
            '300.00'
        )

    def test_usuario_autenticado_puede_filtrar_pedidos_por_total_maximo(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 200',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 150',
            total=Decimal('150.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 100',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?total__lte=150'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        self.assertEqual(
            len(resultados),
            3
        )

        totales = [
            resultado['total']
            for resultado in resultados
        ]

        self.assertIn(
            '150.00',
            totales
        )

        self.assertEqual(
            totales.count('100.00'),
            2
        )

    def test_usuario_autenticado_puede_filtrar_pedidos_por_total_exacto(self):
        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 200',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 150',
            total=Decimal('150.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Otro Pedido 150',
            total=Decimal('150.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido 100',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?total=150'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        self.assertEqual(
            len(resultados),
            2
        )

        for resultado in resultados:
            self.assertEqual(
                resultado['total'],
                '150.00'
            )
    def test_usuario_autenticado_puede_filtrar_pedidos_por_cliente(self):
        otro_cliente = Cliente.objects.create(
            nombre='Otro Cliente',
            email='otro-cliente@example.com',
            telefono='70000002',
            empresa='Otra Empresa',
            estado=True
        )

        Pedido.objects.create(
            cliente=otro_cliente,
            descripcion='Pedido Otro Cliente',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Segundo Pedido Cliente API',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            f'/pedidos/?cliente={self.cliente.id}'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        self.assertEqual(
            len(resultados),
            2
        )

        for resultado in resultados:
            self.assertEqual(
                resultado['cliente'],
                self.cliente.id
            )

    def test_usuario_autenticado_puede_filtrar_pedidos_por_fecha_exacta(self):
        pedido_anterior = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Anterior',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_fecha = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Fecha Exacta',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_posterior = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Posterior',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.filter(
            id=pedido_anterior.id
        ).update(fecha='2026-08-05')

        Pedido.objects.filter(
            id=pedido_fecha.id
        ).update(fecha='2026-08-10')

        Pedido.objects.filter(
            id=pedido_posterior.id
        ).update(fecha='2026-08-15')

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?fecha=2026-08-10'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        self.assertEqual(
            len(resultados),
            1
        )

        self.assertEqual(
            resultados[0]['descripcion'],
            'Pedido Fecha Exacta'
        )

        self.assertEqual(
            resultados[0]['fecha'],
            '2026-08-10'
        )

    def test_usuario_autenticado_puede_filtrar_pedidos_por_fecha_minima(self):
        pedido_anterior = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Anterior',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_fecha = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Fecha Minima',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_posterior = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Posterior',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.filter(
            id=pedido_anterior.id
        ).update(fecha='2026-08-05')

        Pedido.objects.filter(
            id=pedido_fecha.id
        ).update(fecha='2026-08-10')

        Pedido.objects.filter(
            id=pedido_posterior.id
        ).update(fecha='2026-08-15')

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?fecha__gte=2026-08-10'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        self.assertGreaterEqual(
            len(resultados),
            2
        )

        fechas = [
            resultado['fecha']
            for resultado in resultados
        ]

        self.assertIn(
            '2026-08-10',
            fechas
        )

        self.assertIn(
            '2026-08-15',
            fechas
        )
    def test_usuario_autenticado_puede_filtrar_pedidos_por_fecha_maxima(self):
        pedido_anterior = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Anterior',
            total=Decimal('100.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_fecha = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Fecha Maxima',
            total=Decimal('200.00'),
            estado=Pedido.PENDIENTE
        )

        pedido_posterior = Pedido.objects.create(
            cliente=self.cliente,
            descripcion='Pedido Posterior',
            total=Decimal('300.00'),
            estado=Pedido.PENDIENTE
        )

        Pedido.objects.filter(
            id=pedido_anterior.id
        ).update(fecha='2026-08-05')

        Pedido.objects.filter(
            id=pedido_fecha.id
        ).update(fecha='2026-08-10')

        Pedido.objects.filter(
            id=pedido_posterior.id
        ).update(fecha='2026-08-15')

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?fecha__lte=2026-08-10'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        resultados = response.data['results']

        fechas = [
            resultado['fecha']
            for resultado in resultados
        ]

        self.assertIn(
            '2026-08-05',
            fechas
        )

        self.assertIn(
            '2026-08-10',
            fechas
        )

        self.assertNotIn(
            '2026-08-15',
            fechas
        )

    def test_usuario_autenticado_recibe_error_con_total_minimo_invalido(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?total__gte=abc'
        )

        self.assertEqual(
            response.status_code,
            400
        )

    def test_usuario_autenticado_recibe_error_con_fecha_invalida(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/pedidos/?fecha=fecha-invalida'
        )

        self.assertEqual(
            response.status_code,
            400
        )

    def test_usuario_staff_no_puede_saltar_estados_del_pedido(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            {
                'estado': Pedido.ENVIADO
            },
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )
    def test_usuario_staff_no_puede_cambiar_pedido_a_estado_inexistente(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            {
                'estado': 'estado_inventado'
            },
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

    def test_usuario_staff_no_puede_cambiar_estado_sin_enviar_estado(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cambiar_estado/',
            {},
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

    def test_usuario_staff_no_puede_cancelar_pedido_ya_cancelado(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.pedido.estado = Pedido.CANCELADO
        self.pedido.save(update_fields=['estado'])

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CANCELADO
        )
    def test_usuario_staff_no_puede_cancelar_pedido_entregado(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.pedido.estado = Pedido.ENTREGADO
        self.pedido.save(update_fields=['estado'])

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.pedido.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.ENTREGADO
        )

    def test_usuario_staff_puede_cancelar_pedido_y_devolver_stock(self):
        self.usuario.is_staff = True
        self.usuario.save()

        producto = Producto.objects.create(
            nombre='Producto Cancelación',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            cantidad=3,
            precio=producto.precio
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.pedido.refresh_from_db()
        producto.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CANCELADO
        )

        self.assertEqual(
            producto.stock,
            13
        )

    def test_usuario_staff_puede_cancelar_pedido_con_varios_productos_y_devolver_stock(self):
        self.usuario.is_staff = True
        self.usuario.save()

        producto_a = Producto.objects.create(
            nombre='Producto A',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        producto_b = Producto.objects.create(
            nombre='Producto B',
            precio=Decimal('30.00'),
            stock=20,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto_a,
            cantidad=3,
            precio=producto_a.precio
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto_b,
            cantidad=5,
            precio=producto_b.precio
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.post(
            f'/pedidos/{self.pedido.id}/cancelar/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.pedido.refresh_from_db()
        producto_a.refresh_from_db()
        producto_b.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.CANCELADO
        )

        self.assertEqual(
            producto_a.stock,
            13
        )

        self.assertEqual(
            producto_b.stock,
            25
            )

    def test_cancelar_pedido_revierte_cambios_si_ocurre_un_error(self):
        self.usuario.is_staff = True
        self.usuario.save()

        producto_a = Producto.objects.create(
            nombre='Producto A',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        producto_b = Producto.objects.create(
            nombre='Producto B',
            precio=Decimal('30.00'),
            stock=20,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto_a,
            cantidad=3,
            precio=producto_a.precio
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto_b,
            cantidad=5,
            precio=producto_b.precio
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        with patch(
            'clientes.services.Producto.save',
            side_effect=[
                None,
                Exception('Error simulado')
            ]
        ):
            with self.assertRaises(Exception):
                self.client_api.post(
                    f'/pedidos/{self.pedido.id}/cancelar/'
                )

        self.pedido.refresh_from_db()
        producto_a.refresh_from_db()
        producto_b.refresh_from_db()

        self.assertEqual(
            self.pedido.estado,
            Pedido.PENDIENTE
        )

        self.assertEqual(
            producto_a.stock,
            10
        )

        self.assertEqual(
            producto_b.stock,
            20
        )

    def test_crear_pedido_revierte_cambios_si_ocurre_un_error(self):
        self.usuario.is_staff = True
        self.usuario.save()

        producto_a = Producto.objects.create(
            nombre='Producto A',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        producto_b = Producto.objects.create(
            nombre='Producto B',
            precio=Decimal('30.00'),
            stock=20,
            estado=True
        )

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido con error',
            'detalles': [
                {
                    'producto': producto_a.id,
                    'cantidad': 3
                },
                {
                    'producto': producto_b.id,
                    'cantidad': 5
                }
            ]
        }

        with patch(
            'clientes.services.DetallePedido.objects.create',
            side_effect=[
                DetallePedido.objects.create(
                    pedido=self.pedido,
                    producto=producto_a,
                    cantidad=3,
                    precio=producto_a.precio
                ),
                Exception('Error simulado')
            ]
        ):
            with self.assertRaises(Exception):
                self.client_api.post(
                    '/pedidos/',
                    datos,
                    format='json'
                )

        producto_a.refresh_from_db()
        producto_b.refresh_from_db()

        self.assertEqual(
            producto_a.stock,
            10
        )

        self.assertEqual(
            producto_b.stock,
            20
        )

        self.assertFalse(
            Pedido.objects.filter(
                descripcion='Pedido con error'
            ).exists()
        )

    def test_actualizar_pedido_revierte_cambios_si_ocurre_un_error(self):
        self.usuario.is_staff = True
        self.usuario.save()

        producto_a = Producto.objects.create(
            nombre='Producto A',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        producto_b = Producto.objects.create(
            nombre='Producto B',
            precio=Decimal('30.00'),
            stock=20,
            estado=True
        )

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto_a,
            cantidad=3,
            precio=producto_a.precio
        )

        producto_a.stock -= 3
        producto_a.save(update_fields=['stock'])

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'cliente': self.cliente.id,
            'descripcion': 'Pedido actualizado',
            'detalles': [
                {
                    'producto': producto_a.id,
                    'cantidad': 4
                },
                {
                    'producto': producto_b.id,
                    'cantidad': 5
                }
            ]
        }

        detalle_original = DetallePedido.objects.create

        with patch(
            'clientes.services.DetallePedido.objects.create',
            side_effect=[
                lambda **kwargs: detalle_original(**kwargs),
                Exception('Error simulado')
            ]
        ):
            with self.assertRaises(Exception):
                self.client_api.put(
                    f'/pedidos/{self.pedido.id}/',
                    datos,
                    format='json'
                )

        self.pedido.refresh_from_db()
        producto_a.refresh_from_db()
        producto_b.refresh_from_db()

        self.assertEqual(
            self.pedido.descripcion,
            'Pedido API'
        )

        self.assertEqual(
            self.pedido.total,
            Decimal('100.00')
        )

        self.assertEqual(
            producto_a.stock,
            7
        )

        self.assertEqual(
            producto_b.stock,
            20
        )

        self.assertEqual(
            self.pedido.detalles.count(),
            1
        )

        detalle = self.pedido.detalles.first()

        self.assertEqual(
            detalle.producto,
            producto_a
        )

        self.assertEqual(
            detalle.cantidad,
            3
        )

class ProductoAPITest(TestCase):

    def setUp(self):
        self.client_api = APIClient()

        self.usuario = User.objects.create_user(
            username='usuario_producto_test',
            password='password123'
        )

        Producto.objects.create(
            nombre='Producto A',
            precio=Decimal('50.00'),
            stock=10,
            estado=True
        )

        Producto.objects.create(
            nombre='Producto B',
            precio=Decimal('30.00'),
            stock=20,
            estado=True
        )

    def test_usuario_autenticado_puede_consultar_productos(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            2
        )

    def test_usuario_no_autenticado_no_puede_consultar_productos(self):
        response = self.client_api.get(
            '/productos/'
        )

        self.assertEqual(
            response.status_code,
            401
        )

    def test_usuario_autenticado_no_staff_no_puede_crear_producto(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'Producto C',
            'precio': '100.00',
            'stock': 5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            403
        )

    def test_usuario_staff_puede_crear_producto(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'Producto C',
            'precio': '100.00',
            'stock': 5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            201
        )

        self.assertEqual(
            response.data['nombre'],
            'Producto C'
        )

        self.assertEqual(
            response.data['precio'],
            '100.00'
        )

        self.assertEqual(
            response.data['stock'],
            5
        )

    def test_staff_no_puede_crear_producto_sin_precio(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'Producto Sin Precio',
            'stock': 5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'precio',
            response.data
        )

    def test_staff_no_puede_crear_producto_con_precio_invalido(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'Producto Precio Invalido',
            'precio': 'abc',
            'stock': 5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'precio',
            response.data
        )
    def test_staff_no_puede_crear_producto_con_stock_negativo(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'Producto Stock Negativo',
            'precio': '100.00',
            'stock': -5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'stock',
            response.data
        )

    def test_staff_puede_crear_producto_con_stock_cero(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'Producto Sin Stock',
            'precio': '100.00',
            'stock': 0,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            201
        )

        self.assertEqual(
            response.data['stock'],
            0
        )

    def test_staff_no_puede_crear_producto_sin_nombre(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'precio': '100.00',
            'stock': 5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'nombre',
            response.data
        )

    def test_staff_no_puede_crear_producto_con_nombre_demasiado_largo(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        datos = {
            'nombre': 'A' * 101,
            'precio': '100.00',
            'stock': 5,
            'estado': True
        }

        response = self.client_api.post(
            '/productos/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'nombre',
            response.data
        )

    def test_usuario_autenticado_puede_consultar_producto_por_id(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        response = self.client_api.get(
            f'/productos/{producto.id}/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['id'],
            producto.id
        )

        self.assertEqual(
            response.data['nombre'],
            'Producto A'
        )

        self.assertEqual(
            response.data['precio'],
            '50.00'
        )

        self.assertEqual(
            response.data['stock'],
            10
        )

        self.assertEqual(
            response.data['estado'],
            True
        )

    def test_usuario_autenticado_no_puede_consultar_producto_inexistente(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/9999/'
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_usuario_staff_puede_actualizar_producto(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        datos = {
            'nombre': 'Producto Modificado',
            'precio': '60.00',
            'estado': True
        }

        response = self.client_api.put(
            f'/productos/{producto.id}/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['nombre'],
            'Producto Modificado'
        )

        self.assertEqual(
            response.data['precio'],
            '60.00'
        )

        self.assertEqual(
            response.data['estado'],
            True
        )

    def test_actualizar_producto_no_modifica_stock(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        stock_original = producto.stock

        datos = {
            'nombre': 'Producto Modificado',
            'precio': '60.00',
            'estado': True,
            'stock': 999
        }

        response = self.client_api.put(
            f'/productos/{producto.id}/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            stock_original
        )

    def test_usuario_staff_puede_actualizar_producto_parcialmente(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        precio_original = producto.precio
        estado_original = producto.estado

        datos = {
            'nombre': 'Producto Actualizado Parcialmente'
        }

        response = self.client_api.patch(
            f'/productos/{producto.id}/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['nombre'],
            'Producto Actualizado Parcialmente'
        )

        self.assertEqual(
            response.data['precio'],
            '50.00'
        )

        self.assertEqual(
            response.data['estado'],
            estado_original
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.precio,
            precio_original
        )

        self.assertEqual(
            producto.estado,
            estado_original
        )
    def test_actualizar_producto_parcialmente_no_modifica_stock(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        stock_original = producto.stock

        datos = {
            'stock': 999
        }

        response = self.client_api.patch(
            f'/productos/{producto.id}/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.stock,
            stock_original
        )
    def test_staff_no_puede_actualizar_producto_con_precio_invalido(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        precio_original = producto.precio

        datos = {
            'precio': 'abc'
        }

        response = self.client_api.patch(
            f'/productos/{producto.id}/',
            datos,
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'precio',
            response.data
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.precio,
            precio_original
        )

    def test_usuario_no_staff_no_puede_activar_producto(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        producto.estado = False
        producto.save()

        response = self.client_api.post(
            f'/productos/{producto.id}/activar/'
        )

        self.assertEqual(
            response.status_code,
            403
        )

    def test_usuario_staff_puede_activar_producto(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        producto.estado = False
        producto.save()

        response = self.client_api.post(
            f'/productos/{producto.id}/activar/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        producto.refresh_from_db()

        self.assertTrue(
            producto.estado
        )

        self.assertEqual(
            response.data['estado'],
            True
        )

    def test_usuario_staff_no_puede_activar_producto_ya_activo(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        # Producto ya activo
        self.assertTrue(producto.estado)

        response = self.client_api.post(
            f'/productos/{producto.id}/activar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            response.data['detail'],
            'El producto ya está activo.'
        )

    def test_usuario_no_staff_no_puede_desactivar_producto(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        # Producto activo
        self.assertTrue(producto.estado)

        response = self.client_api.post(
            f'/productos/{producto.id}/desactivar/'
        )

        self.assertEqual(
            response.status_code,
            403
        )

    def test_usuario_staff_puede_desactivar_producto(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        # El producto comienza activo
        self.assertTrue(producto.estado)

        response = self.client_api.post(
            f'/productos/{producto.id}/desactivar/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        producto.refresh_from_db()

        self.assertFalse(
            producto.estado
        )

        self.assertEqual(
            response.data['estado'],
            False
        )

    def test_usuario_staff_no_puede_desactivar_producto_ya_inactivo(self):
        self.usuario.is_staff = True
        self.usuario.save()

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        producto.estado = False
        producto.save()

        response = self.client_api.post(
            f'/productos/{producto.id}/desactivar/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertEqual(
            response.data['detail'],
            'El producto ya está inactivo.'
        )

    def test_usuario_autenticado_puede_consultar_productos_activos(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto_inactivo = Producto.objects.get(
            nombre='Producto B'
        )

        producto_inactivo.estado = False
        producto_inactivo.save()

        response = self.client_api.get(
            '/productos/activos/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto A'
        )

        self.assertTrue(
            response.data['results'][0]['estado']
        )

    def test_usuario_no_autenticado_no_puede_consultar_productos_activos(self):
        response = self.client_api.get(
            '/productos/activos/'
        )

        self.assertEqual(
            response.status_code,
            401
        )

    def test_productos_activos_utiliza_paginacion(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto_inactivo = Producto.objects.get(
            nombre='Producto B'
        )

        producto_inactivo.estado = False
        producto_inactivo.save()

        response = self.client_api.get(
            '/productos/activos/'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            'count',
            response.data
        )

        self.assertIn(
            'results',
            response.data
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            len(response.data['results']),
            1
        )

    def test_usuario_autenticado_puede_filtrar_productos_por_nombre(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?nombre__icontains=Producto A'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto A'
        )

    def test_usuario_autenticado_puede_filtrar_productos_por_precio_minimo(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?precio__gte=40'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto A'
        )

    def test_usuario_autenticado_puede_filtrar_productos_por_precio_maximo(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?precio__lte=40'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto B'
        )

    def test_usuario_autenticado_puede_filtrar_productos_por_stock_minimo(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?stock__gte=15'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto B'
        )

    def test_usuario_autenticado_puede_filtrar_productos_por_stock_maximo(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?stock__lte=15'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto A'
        )

    def test_usuario_autenticado_puede_filtrar_productos_por_estado(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto_inactivo = Producto.objects.get(
            nombre='Producto B'
        )

        producto_inactivo.estado = False
        producto_inactivo.save()

        response = self.client_api.get(
            '/productos/?estado=true'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['count'],
            1
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto A'
        )

    def test_usuario_autenticado_puede_ordenar_productos_por_precio(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?ordering=precio'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto B'
        )

        self.assertEqual(
            response.data['results'][1]['nombre'],
            'Producto A'
        )
    def test_usuario_autenticado_puede_ordenar_productos_por_precio_descendente(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?ordering=-precio'
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.data['results'][0]['nombre'],
            'Producto A'
        )

        self.assertEqual(
            response.data['results'][1]['nombre'],
            'Producto B'
        )
    def test_usuario_autenticado_no_puede_ordenar_por_campo_no_permitido(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        response = self.client_api.get(
            '/productos/?ordering=estado'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'ordering',
            response.data
        )

    def test_usuario_no_staff_no_puede_eliminar_producto(self):
        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        response = self.client_api.delete(
            f'/productos/{producto.id}/'
        )

        self.assertEqual(
            response.status_code,
            403
        )

        self.assertTrue(
            Producto.objects.filter(
                id=producto.id
            ).exists()
        )

    def test_usuario_staff_puede_eliminar_producto(self):
        self.usuario.is_staff = True
        self.usuario.save(update_fields=['is_staff'])

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        response = self.client_api.delete(
            f'/productos/{producto.id}/'
        )

        self.assertEqual(
            response.status_code,
            204
        )

        self.assertFalse(
            Producto.objects.filter(
                id=producto.id
            ).exists()
        )

    def test_usuario_staff_no_puede_eliminar_producto_utilizado_en_pedido(self):
        self.usuario.is_staff = True
        self.usuario.save(update_fields=['is_staff'])

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        cliente = Cliente.objects.create(
            nombre='Cliente Test',
            email='cliente@test.com',
            telefono='70000000',
            empresa='Empresa Test'
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            descripcion='Pedido Test',
            total=producto.precio
        )

        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=1,
            precio=producto.precio
        )

        response = self.client_api.delete(
            f'/productos/{producto.id}/'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertTrue(
            Producto.objects.filter(
                id=producto.id
            ).exists()
        )

    def test_usuario_no_autenticado_no_puede_eliminar_producto(self):
        producto = Producto.objects.get(
            nombre='Producto A'
        )

        response = self.client_api.delete(
            f'/productos/{producto.id}/'
        )

        self.assertEqual(
            response.status_code,
            401
        )

        self.assertTrue(
            Producto.objects.filter(
                id=producto.id
            ).exists()
        )

    def test_actualizar_producto_parcialmente_rechaza_nombre_demasiado_largo(self):
        self.usuario.is_staff = True
        self.usuario.save(update_fields=['is_staff'])

        self.client_api.force_authenticate(
            user=self.usuario
        )

        producto = Producto.objects.get(
            nombre='Producto A'
        )

        nombre_largo = 'A' * 101

        response = self.client_api.patch(
            f'/productos/{producto.id}/',
            {
                'nombre': nombre_largo
            },
            format='json'
        )

        self.assertEqual(
            response.status_code,
            400
        )

        self.assertIn(
            'nombre',
            response.data
        )

        producto.refresh_from_db()

        self.assertEqual(
            producto.nombre,
            'Producto A'
        )