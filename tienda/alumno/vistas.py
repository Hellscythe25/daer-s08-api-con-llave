"""PARTES 2 y 3 — Las vistas (qué rutas responden y cómo) y sus permisos (quién puede hacer qué).

Usen las vistas genéricas de DRF (generics.ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView,
RetrieveAPIView): con queryset y serializer_class ya dan GET, POST, PUT, PATCH y DELETE con los códigos
correctos (201 al crear, 204 al borrar, 404 si no existe, 400 si el serializer rechaza los datos).

Las rutas ya están en extra08/urls.py; aquí solo se escriben las clases. Las vistas de categoría ya están
hechas, como ejemplo, salvo sus permisos. Comprueben con:

    python manage.py duelo
"""

from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tienda.models import Categoria, Pedido, Producto

from .serializers import CategoriaSerializer, PedidoSerializer, ProductoSerializer


class PorHacer(APIView):
    """Responde 501 («no implementado») a todo. Reemplácenla por la vista de verdad."""

    def por_hacer(self, request, *args, **kwargs):
        return Response({'detail': f'{type(self).__name__} está por hacer.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    get = post = put = patch = delete = por_hacer


# TODO P3-1. Un permiso propio, SoloPersonalEscribe (subclase de permissions.BasePermission):
#            cualquiera puede leer (métodos SAFE_METHODS: GET, HEAD, OPTIONS); crear, cambiar o borrar,
#            solo el personal de la tienda (request.user.is_staff). Úsenlo en categorías y productos.


class CategoriaLista(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    # TODO P3-2. permission_classes


class CategoriaDetalle(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    # TODO P3-2. permission_classes


class ProductoLista(generics.ListCreateAPIView):
    """Lista y alta de productos, con ?categoria=<nombre> y ?q=<texto>."""

    serializer_class = ProductoSerializer
    # TODO P3-2. permission_classes

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
    # TODO P3-2. permission_classes


class PedidoLista(generics.ListAPIView):
    # Cliente en el JOIN y todas las líneas con su producto en una segunda consulta: sin N+1.
    queryset = Pedido.objects.select_related('cliente').prefetch_related('lineas__producto')
    serializer_class = PedidoSerializer
    # TODO P3-3. Solo con credenciales: los pedidos traen datos de clientes.


class PedidoDetalle(generics.RetrieveAPIView):
    queryset = Pedido.objects.select_related('cliente').prefetch_related('lineas__producto')
    serializer_class = PedidoSerializer
    # TODO P3-3. Solo con credenciales.


class AnularPedido(PorHacer):
    """TODO P3-4. APIView con un método post(self, request, pk) que:
    - responde 404 si el pedido no existe (pista: get_object_or_404, no Pedido.objects.get);
    - responde 409 si ya estaba anulado;
    - si no, lo pasa a anulado y devuelve el pedido con PedidoSerializer.
    Solo el personal de la tienda puede anular (permissions.IsAdminUser).
    """


# Para no dejar imports sin usar mientras completan: bórrenlo cuando ya usen `permissions`.
_ = permissions
