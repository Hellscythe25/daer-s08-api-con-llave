"""PARTE 1 — El contrato de datos: qué entra y qué sale por la API.

Un serializer decide tres cosas: qué campos se muestran, cuáles se pueden escribir y qué datos se rechazan.
Las pruebas de tienda/tests/test_p1_contrato.py dicen exactamente qué se espera. Comprueben con:

    python manage.py duelo

CategoriaSerializer ya está hecho, como ejemplo.
"""

from rest_framework import serializers

from tienda.models import Categoria, LineaPedido, Pedido, Producto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']


class ProductoSerializer(serializers.ModelSerializer):
    # Se muestra el nombre de la categoría, pero no se puede escribir: la categoría se elige por su id.
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Producto
        # Lista EXPLÍCITA: `costo` no está, así que ni sale en las respuestas ni se acepta al escribir.
        # Con '__all__', cualquier campo que se agregue mañana al modelo saldría por la API sin que nadie lo decida.
        fields = ['id', 'nombre', 'categoria', 'categoria_nombre', 'precio', 'stock', 'descripcion']

    def validate_nombre(self, valor):
        repetidos = Producto.objects.filter(nombre__iexact=valor)
        if self.instance is not None:  # al editar, el propio producto no cuenta como repetido
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError('Ya existe un producto con ese nombre.')
        return valor

    def validate_precio(self, valor):
        if valor <= 0:
            raise serializers.ValidationError('El precio debe ser mayor que cero.')
        return valor

    def validate_stock(self, valor):
        if valor < 0:
            raise serializers.ValidationError('El stock no puede ser negativo.')
        return valor


class LineaPedidoSerializer(serializers.ModelSerializer):
    producto = serializers.CharField(source='producto.nombre', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = LineaPedido
        fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']

    def get_subtotal(self, linea):
        return f'{linea.cantidad * linea.precio_unitario:.2f}'


class PedidoSerializer(serializers.ModelSerializer):
    cliente = serializers.CharField(source='cliente.nombre', read_only=True)
    lineas = LineaPedidoSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = ['id', 'cliente', 'fecha', 'estado', 'lineas', 'total']
        read_only_fields = fields  # por la API un pedido se consulta o se anula, no se edita

    def get_total(self, pedido):
        # .all() reutiliza las líneas que trajo prefetch_related: no hace una consulta por pedido.
        return f'{sum(linea.cantidad * linea.precio_unitario for linea in pedido.lineas.all()):.2f}'
