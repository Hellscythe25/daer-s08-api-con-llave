# Paso 8 de la guía: cliente de la API con el token del admin.
# Crea un producto, lo modifica, lo consulta, lo borra y lo vuelve a consultar, mostrando el código de cada respuesta.
#
#   python manage.py runserver          (en otra terminal)
#   powershell -ExecutionPolicy Bypass -File scripts\cliente_api.ps1
#
# Funciona en Windows PowerShell 5.1 y en PowerShell 7.

param(
    [string]$Base = "http://127.0.0.1:8000/api",
    [string]$Token = "admin-token-de-laboratorio-0000000000001"
)

$Cabeceras = @{ Authorization = "Token $Token" }

function Invoke-Api {
    param([string]$Metodo, [string]$Url, $Cuerpo = $null)
    $opciones = @{ Uri = $Url; Method = $Metodo; Headers = $Cabeceras; UseBasicParsing = $true }
    if ($null -ne $Cuerpo) {
        # En UTF-8 explícito: Windows PowerShell 5.1 no lo hace solo y las tildes llegarían rotas.
        $opciones.Body = [Text.Encoding]::UTF8.GetBytes(($Cuerpo | ConvertTo-Json))
        $opciones.ContentType = "application/json; charset=utf-8"
    }
    try {
        $r = Invoke-WebRequest @opciones
        $codigo = [int]$r.StatusCode
        $datos = if ($r.Content) { [Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) | ConvertFrom-Json } else { $null }
    } catch {
        # Invoke-WebRequest lanza una excepción con 4xx y 5xx; el código viene en la respuesta.
        if ($null -eq $_.Exception.Response) { throw }
        $codigo = [int]$_.Exception.Response.StatusCode
        $datos = $null
    }
    Write-Host ("{0,-6} {1,-42} -> {2}" -f $Metodo, $Url.Replace($Base, "/api"), $codigo)
    return [pscustomobject]@{ Codigo = $codigo; Datos = $datos }
}

$nuevo = @{ nombre = "Inca Kola 500ml"; categoria = 3; precio = "2.20"; stock = 12; descripcion = "Gaseosa sabor nacional" }
$creado = Invoke-Api POST "$Base/productos/" $nuevo
if ($creado.Codigo -ne 201) { throw "No se pudo crear el producto (código $($creado.Codigo)). ¿Ya existe? ¿El servidor está levantado?" }
$id = $creado.Datos.id
Write-Host "       creado con id $id, categoría $($creado.Datos.categoria_nombre)"

$cambio = Invoke-Api PATCH "$Base/productos/$id/" @{ precio = "2.50"; stock = 20 }
Write-Host "       precio $($cambio.Datos.precio), stock $($cambio.Datos.stock)"

$leido = Invoke-Api GET "$Base/productos/$id/"
Write-Host "       $($leido.Datos.nombre): $($leido.Datos.precio) soles, $($leido.Datos.stock) en stock"

$null = Invoke-Api DELETE "$Base/productos/$id/"
$null = Invoke-Api GET "$Base/productos/$id/"
