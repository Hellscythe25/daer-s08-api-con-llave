"""PARTES 2 y 3 — Las vistas (qué rutas responden y cómo) y sus permisos (quién puede hacer qué).

Usen las vistas genéricas de DRF (generics.ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView,
RetrieveAPIView): con queryset y serializer_class ya dan GET, POST, PUT, PATCH y DELETE con los códigos
correctos (201 al crear, 204 al borrar, 404 si no existe, 400 si el serializer rechaza los datos).

Las rutas ya están en extra08/urls.py; aquí solo se escriben las clases. Las vistas de categoría ya están
hechas, como ejemplo, salvo sus permisos. Comprueben con:

    python manage.py duelo
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tienda.models import Categoria, Pedido, Producto

from .serializers import CategoriaSerializer, PedidoSerializer, ProductoSerializer


class SoloPersonalEscribe(permissions.BasePermission):
    """Cualquiera lee (GET, HEAD, OPTIONS); solo el personal de la tienda (is_staff) crea, cambia o borra."""

    message = 'Solo el personal de la tienda puede cambiar el catálogo.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Un anónimo no es staff: DRF responde 401 si no mandó credenciales y 403 si las mandó y no alcanzan.
        return bool(request.user and request.user.is_staff)


class CategoriaLista(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [SoloPersonalEscribe]


class CategoriaDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [SoloPersonalEscribe]


class ProductoLista(generics.ListCreateAPIView):
    """Lista y alta de productos, con ?categoria=<nombre> y ?q=<texto>."""

    serializer_class = ProductoSerializer
    permission_classes = [SoloPersonalEscribe]

    def get_queryset(self):
        # select_related: la categoría viene en el mismo JOIN, así categoria_nombre no hace una consulta por fila.
        productos = Producto.objects.select_related('categoria')
        categoria = self.request.query_params.get('categoria')
        if categoria:
            productos = productos.filter(categoria__nombre__iexact=categoria)
        texto = self.request.query_params.get('q')
        if texto:
            productos = productos.filter(Q(nombre__icontains=texto) | Q(descripcion__icontains=texto))
        return productos


class ProductoDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = Producto.objects.select_related('categoria')
    serializer_class = ProductoSerializer
    permission_classes = [SoloPersonalEscribe]


class PedidoLista(generics.ListAPIView):
    # Cliente en el JOIN y todas las líneas con su producto en una segunda consulta: sin N+1.
    queryset = Pedido.objects.select_related('cliente').prefetch_related('lineas__producto')
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated]  # los pedidos traen datos de clientes


class PedidoDetalle(generics.RetrieveAPIView):
    queryset = Pedido.objects.select_related('cliente').prefetch_related('lineas__producto')
    serializer_class = PedidoSerializer
    permission_classes = [permissions.IsAuthenticated]


class AnularPedido(APIView):
    """POST /api/pedidos/<pk>/anular/: solo el personal; 404 si no existe, 409 si ya estaba anulado."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        pedido = get_object_or_404(Pedido, pk=pk)  # Pedido.objects.get daría un 500 con un id inexistente
        if pedido.estado == Pedido.ANULADO:
            return Response({'detail': 'El pedido ya estaba anulado.'}, status=status.HTTP_409_CONFLICT)
        pedido.estado = Pedido.ANULADO
        pedido.save(update_fields=['estado'])
        return Response(PedidoSerializer(pedido).data)
