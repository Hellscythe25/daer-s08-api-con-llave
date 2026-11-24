# Informe — Lab extra S08: la API con llave

Resolución de referencia en la rama `entrega-v1`; `main` sigue siendo la plantilla. Todas las salidas son reales y
salen de esta copia: Python 3.12, Django 6.1 y Django REST Framework 3.18, con los datos fijos de `cargar_datos`.

> Las capturas de pantalla van marcadas como **[CAPTURA: …]**. Las salidas de consola están copiadas tal cual.

| Parte | Qué se hizo | Commit |
|---|---|---|
| 1 · contrato | `tienda/alumno/serializers.py`: campos públicos explícitos y validaciones de nombre, precio y stock | `feat: serializers de la Parte 1…` |
| 2 · endpoints | `tienda/alumno/vistas.py`: vistas genéricas, filtros, sin N+1; `scripts/cliente_api.ps1` | `feat: vistas genéricas de la Parte 2…` |
| 3 · permisos | `SoloPersonalEscribe`, permisos por vista, anulación con 404/409; `scripts/llave_agente.ps1` | `feat: permisos de la Parte 3…` |
| 4 · duelo | `tienda/corregida/`: los cuatro fallos de la IA, uno por commit | `fix: … (fallo 1)` a `fix: … (fallo 4)` |

## Paso 2 — Leer antes de ejecutar

**Rutas y métodos** (`extra08/urls.py`):

| Ruta | Métodos |
|---|---|
| `/api/categorias/` | GET lista · POST crea |
| `/api/categorias/<id>/` | GET · PUT · PATCH · DELETE |
| `/api/productos/` | GET lista (`?categoria=`, `?q=`) · POST crea |
| `/api/productos/<id>/` | GET · PUT · PATCH · DELETE |
| `/api/pedidos/` | GET lista |
| `/api/pedidos/<id>/` | GET detalle con líneas y total |
| `/api/pedidos/<id>/anular/` | POST |
| `/api/token/` | POST usuario y clave → token |
| `/api-auth/` | login y logout de la API navegable |

**El campo interno** es `Producto.costo`, lo que le cuesta el producto a la tienda. No debe salir por la API por dos
razones:
- cualquiera que lea el catálogo vería el margen de cada producto;
- si el serializer lo acepta, quien escribe por la API podría cambiarlo.

**`admin` y `agente`.** Los dos tienen usuario, clave y token, así que la API sabe quién es cada uno. La diferencia es
que `admin` es personal de la tienda (`is_staff=True`) y `agente` no. Por eso el agente puede identificarse y leer lo
que pide credenciales, pero no cambiar el catálogo ni anular pedidos.

## Paso 3 — Punto de partida

```text
Versión: alumno  (tienda/alumno/)
Parte 1 · contrato (serializers)    0 de  6 en verde
Parte 2 · endpoints (vistas)        0 de  6 en verde
Parte 3 · permisos (quién puede)    2 de  8 en verde
18 en rojo de 20.
```

Las dos que ya pasan son de permisos: `PorHacer` responde 501 a todo, y hay pruebas que solo comprueban que algo
**no** se pudo hacer.

## Parte 1 — El contrato de datos

| Momento | En rojo |
|---|---|
| Al empezar | 18 |
| Con los serializers completos (TODO 1 a 7) | 18 |
| Con las vistas de la Parte 2 | 5 (todos de la Parte 3) |

Las pruebas de la Parte 1 pasan **por la API** (`/api/productos/…`). Mientras las vistas respondían 501, siguieron en
rojo aunque el serializer ya estuviera bien. Se pusieron en verde las 6 de una vez al escribir las vistas.

Decisiones del serializer:
- `categoria_nombre` es de solo lectura (`source='categoria.nombre'`). Al crear un producto se manda `categoria` con el
  id, y si alguien manda `categoria_nombre: "Inventada"` se ignora: la prueba lo comprueba.
- `validate_nombre` usa `nombre__iexact`, así que «FANTA 500ML» cuenta como repetido. Al editar, excluye el propio
  producto (`self.instance`), y por eso un PATCH que mantiene el nombre da 200.
- `validate_precio` exige que sea mayor que 0 y `validate_stock` que no sea menor que 0. El modelo, por sí solo, acepta
  precio 0.
- `PedidoSerializer` es todo de solo lectura. `total` suma `pedido.lineas.all()`, que con `prefetch_related` no hace
  una consulta por pedido.

### Paso 5 — Por qué la lista explícita protege el costo

Con `fields = [...]`, la API muestra y acepta solo lo que está escrito en la lista. `costo` no está, así que ni sale en
las respuestas ni se puede cambiar con un POST o un PATCH, aunque alguien lo mande.

Con `'__all__'` pasa lo contrario: sale **todo** lo que tenga el modelo, hoy y mañana. Si mañana se agrega
`proveedor` o `margen_minimo`, aparece en la API pública sin que nadie lo haya decidido y sin que cambie una sola línea
del serializer. Es lo que hizo la IA (fallo 1): «si el modelo crece, la API se actualiza sola» es justamente el
problema.

## Parte 2 — Los endpoints

```text
Parte 1 · contrato (serializers)    6 de  6 en verde
Parte 2 · endpoints (vistas)        6 de  6 en verde
Parte 3 · permisos (quién puede)    3 de  8 en verde
5 en rojo de 20.
```

- **`ProductoLista`** sobrescribe `get_queryset` y lee `?categoria=` (con `categoria__nombre__iexact`) y `?q=` (con
  `Q(nombre__icontains) | Q(descripcion__icontains)`).
- **`select_related('categoria')`** hace que la lista sea una sola consulta aunque muestre `categoria_nombre`. La
  prueba `test_lista_de_productos_en_una_consulta` lo comprueba.
- **Pedidos:** `select_related('cliente')` y `prefetch_related('lineas__producto')` traen el cliente en el JOIN y todas
  las líneas con su producto en una segunda consulta. No hay N+1.

### Paso 7 — La API navegable

- **[CAPTURA: http://127.0.0.1:8000/api/productos/ — la lista de 10 productos]**
- **[CAPTURA: /api/productos/?categoria=GASEOSAS — 3 productos (7up, Coca Cola, Fanta): el filtro ignora mayúsculas]**
- **[CAPTURA: /api/productos/?q=chocolate — 4 productos (Picaras, Princesa, Sublime, Triángulo), encontrados por la descripción]**
- **[CAPTURA: /api/productos/999/ — 404 con `"No Producto matches the given query."`]**

### Paso 8 — Cliente de PowerShell (`scripts/cliente_api.ps1`)

El script usa `Invoke-WebRequest`, que lanza una excepción con los 4xx. El script la captura y saca el código de la
respuesta. El JSON se manda en UTF-8 explícito porque Windows PowerShell 5.1 no lo hace solo, y el `.ps1` se guarda con
BOM para que las tildes no salgan rotas en esa versión.

```text
POST   /api/productos/                            -> 201
       creado con id 12, categoría Gaseosas
PATCH  /api/productos/12/                         -> 200
       precio 2.50, stock 20
GET    /api/productos/12/                         -> 200
       Inca Kola 500ml: 2.50 soles, 20 en stock
DELETE /api/productos/12/                         -> 204
GET    /api/productos/12/                         -> 404
```

## Parte 3 — La llave

```text
Parte 1 · contrato (serializers)    6 de  6 en verde
Parte 2 · endpoints (vistas)        6 de  6 en verde
Parte 3 · permisos (quién puede)    8 de  8 en verde
Todo en verde: 20 de 20.
```

| Vista | Permiso | Por qué |
|---|---|---|
| Categorías y productos | `SoloPersonalEscribe` | el catálogo es público, pero solo el personal lo cambia |
| Lista y detalle de pedidos | `IsAuthenticated` | traen nombres de clientes: sin credenciales, nada |
| Anular pedido | `IsAdminUser` | es una acción del personal, no de cualquiera con cuenta |

La anulación usa `get_object_or_404`, que da 404 si el id no existe, y responde 409 si el pedido ya estaba anulado.

### Paso 10 — El token del agente: 401, 403 y 200 (`scripts/llave_agente.ps1`)

```text
Token del agente: agente-token-de-laboratorio-00000000002

sin token   GET    /api/pedidos/                -> 401
agente      GET    /api/pedidos/                -> 200
agente      PATCH  /api/productos/3/            -> 403
agente      POST   /api/pedidos/6/anular/       -> 403
```

Antes de la Parte 3, el mismo script daba `200, 200, 200, 501`: sin permisos, cualquiera leía los pedidos y el agente
cambió el stock del producto 3 **de verdad**, porque el script no es un simulacro. Hubo que volver a correr
`cargar_datos`.

**401 frente a 403.**
- **401 (no autenticado):** «no sé quién eres». No llegó ninguna credencial, o llegó una inválida. Se arregla
  identificándose.
- **403 (prohibido):** «sé quién eres y no puedes». El agente se identificó bien con su token, pero no es personal de
  la tienda. Mandar el token otra vez no cambia nada: hace falta otro permiso.

### Paso 11 — El plan del agente con tres credenciales (simulacro)

| # | Paso del plan | Motivo del agente | Anónimo | Agente | Admin |
|---|---|---|---|---|---|
| 1 | GET `/api/productos/` | revisar el catálogo | 200 | 200 | 200 |
| 2 | PATCH `/api/productos/3/` stock 24 | «el 7up tiene stock 0» | 401 | 403 | 200 |
| 3 | POST «7UP 500ML» | «por si acaso, otra vez» | 401 | 403 | 400 (nombre repetido) |
| 4 | POST Inca Kola con precio 0 | «que alguien lo corrija» | 401 | 403 | 400 (precio) |
| 5 | GET `/api/pedidos/6/` | «pendiente desde octubre» | 401 | 200 | 200 |
| 6 | POST `/api/pedidos/6/anular/` | «limpiar la lista» | 401 | 403 | **200** |
| | **Pasos cumplidos** | | 1 de 6 | 2 de 6 | 4 de 6 |

**El pedido 6 de Ana con el token del admin.** Habría quedado **anulado** (paso 6: 200, `"estado": "anulado"`). Nadie
le preguntó a Ana ni al personal: el agente vio «pendiente desde octubre» y lo interpretó como basura, pero podía
estar esperando un pago o una entrega.

Con el token del admin, lo único que frenó al agente fueron los serializers: el nombre repetido y el precio 0. Todo lo
que esas validaciones no cubren, el agente lo hace. Por eso **un agente nunca debe recibir el token del personal**:
- ese token no distingue entre «revisar» y «borrar»;
- el agente actúa con la autoridad completa de una persona que no está mirando.

El agente necesita su propia cuenta, con los permisos mínimos para su tarea.

## Parte 4 — El duelo con la IA

### Paso 12 — `duelo ia`

```text
Versión: ia  (tienda/ia/)
Parte 1 · contrato (serializers)    4 de  6 en verde
    - test_precio_debe_ser_mayor_que_cero (FAIL)
    - test_producto_expone_solo_campos_publicos (FAIL)
Parte 2 · endpoints (vistas)        6 de  6 en verde
Parte 3 · permisos (quién puede)    6 de  8 en verde
    - test_anular_un_pedido_inexistente_da_404 (ERROR)
    - test_el_agente_no_cambia_el_catalogo (FAIL)

4 en rojo de 20.
```

### Paso 13 — Los cuatro fallos

| # | Archivo y línea | Qué hizo la IA | Prueba que lo detecta y su mensaje | Qué pasaría en producción |
|---|---|---|---|---|
| 1 | `tienda/ia/serializers.py:24` | `fields = '__all__'` | `test_producto_expone_solo_campos_publicos`: `Items in the first set but not the second: 'costo'` | el costo y el margen de cada producto salen en el catálogo público, y se pueden cambiar por la API |
| 2 | `tienda/ia/serializers.py`, entre las líneas 32 y 34 | no escribió `validate_precio` (se pidió «no repetidos ni stock negativo» y no dijo nada del precio) | `test_precio_debe_ser_mayor_que_cero`: `201 != 400 : precio 0: se aceptó` | productos a S/ 0.00 a la venta: el agente creó la Inca Kola gratis «para que alguien la corrija» |
| 3 | `tienda/ia/vistas.py:37` y `:51` | `IsAuthenticatedOrReadOnly` en las vistas de producto | `test_el_agente_no_cambia_el_catalogo`: `201 != 403 : el agente pudo CREAR un producto` | cualquier cuenta (un cliente, el agente) puede crear, cambiar precios y borrar productos |
| 4 | `tienda/ia/vistas.py:70` | `Pedido.objects.get(pk=pk)` | `test_anular_un_pedido_inexistente_da_404` (ERROR): `Pedido.DoesNotExist: Pedido matching query does not exist.` | un id inexistente da 500 en lugar de 404: un agente que reintenta ante un error del servidor lo seguirá intentando, y el log se llena de trazas |

**El plan con la versión de la IA y el token del agente:**

| # | Paso | Alumno (agente) | IA (agente) |
|---|---|---|---|
| 1 | GET productos | 200 | 200 |
| 2 | PATCH stock del 7up | 403 | **200**, y la respuesta trae `"costo": "1.05"` |
| 3 | POST «7UP 500ML» | 403 | 400 (nombre repetido) |
| 4 | POST Inca Kola a 0 | 403 | **201**, con `"precio": "0.00"` |
| 5 | GET pedido 6 | 200 | 200 |
| 6 | Anular pedido 6 | 403 | 403 |
| | Cumplidos | 2 de 6 | 4 de 6 |

**El más peligroso con un agente conectado es el fallo 3** (los permisos de producto).
- Los otros tres son errores de *datos* o de *forma*.
- El 3 le da al agente una capacidad que no debía tener: escribir en el catálogo. En el simulacro cambió un stock y
  creó un producto, y con la misma llave podría bajar precios o borrar productos.
- Además, el 3 es el que hace que el fallo 2 importe: sin permiso de escritura, el precio 0 del agente se habría
  quedado en un 403.

La IA eligió `IsAuthenticatedOrReadOnly` porque «autenticado» le pareció lo mismo que «personal». En las categorías sí
lo hizo bien: ahí no se notaba el fallo.

### Paso 14 — La versión corregida

Se partió de `python manage.py duelo --iniciar-corregida` y se arregló un fallo por commit, corriendo
`duelo corregida` después de cada uno:

| Tras el arreglo | En rojo | Prueba que se puso en verde |
|---|---|---|
| 1 · lista explícita de campos | 3 | `test_producto_expone_solo_campos_publicos` |
| 2 · `validate_precio` | 2 | `test_precio_debe_ser_mayor_que_cero` |
| 3 · `EsPersonalOSoloLectura` en productos | 1 | `test_el_agente_no_cambia_el_catalogo` |
| 4 · `get_object_or_404` | **0** | `test_anular_un_pedido_inexistente_da_404` |

```text
Versión: corregida  (tienda/corregida/)
Todo en verde: 20 de 20.
```

- Con la versión corregida, el plan como agente da `200, 403, 403, 403, 200, 403`, igual que la versión del alumno.
- `git diff fa3010d -- tienda/tests tienda/ia` sale vacío: no se tocaron las pruebas ni la versión de la IA.
- En el fallo 3 también se reforzó `EsPersonalOSoloLectura` con `bool(request.user and request.user.is_staff)`, igual
  que `SoloPersonalEscribe`. Con un usuario anónimo, `is_staff` es `False`, así que no cambia el resultado: solo deja
  claro que se trata de un booleano.

## Paso 15 — Uso de IA, reparto y conclusión

| Qué se le pidió | Qué respondió | Qué se aceptó o rechazó y por qué |
|---|---|---|
| *[pareja: completar con sus propios pedidos a la IA]* | | |
| Ejemplo: «¿por qué el agente recibe 403 y no 401?» | 401 = sin credenciales válidas; 403 = autenticado sin permiso | aceptado: coincide con la salida del paso 10 |
| Ejemplo: «hazme el permiso para que solo el staff escriba» | propuso `IsAuthenticatedOrReadOnly` | **rechazado**: es el fallo 3 de la Parte 4; deja escribir al agente |

| Integrante | Partes |
|---|---|
| *[integrante 1]* | *[p. ej. Parte 1, paso 8, Parte 4 fallos 1–2]* |
| *[integrante 2]* | *[p. ej. Parte 2, Parte 3, Parte 4 fallos 3–4]* |

**Conclusión: si una empresa conecta un agente de IA a su API…**

- **¿Qué token le daría?** Uno propio del agente, de una cuenta que **no** es personal (`is_staff=False`). Nunca el de
  un administrador ni el de una persona. Así lo que hace el agente queda a su nombre, y se le puede quitar el acceso
  sin tocar el de nadie más.
- **¿Qué rutas le dejaría usar?** Lectura del catálogo y de los pedidos, que es lo que necesita para *revisar*. Las
  rutas que cambian cosas (PATCH de stock, POST de productos, anular) le responden 403. Eso lo decide la API con sus
  permisos, no el agente ni sus instrucciones.
- **¿Quién revisa lo que propone antes de aplicarlo?** Una persona del personal. El agente entrega su plan, el plan
  corre primero en simulacro (`ejecutar_plan` sin `--aplicar`) y alguien con el token del personal aplica solo los
  pasos que aprueba. En este plan habría aprobado el paso 2 (reponer el 7up) y rechazado el 3 (duplicado), el 4
  (precio 0) y el 6 (anular el pedido de Ana sin preguntarle).

La llave la ponen el serializer y los permisos. Una API que confía en que el agente «se porte bien» ya está abierta.
