# Paso 10 de la guía: el token del agente y la diferencia entre 401 y 403.
#
#   python manage.py runserver          (en otra terminal)
#   powershell -ExecutionPolicy Bypass -File scripts\llave_agente.ps1

param([string]$Base = "http://127.0.0.1:8000/api")

function Get-Codigo {
    param([string]$Metodo, [string]$Url, [hashtable]$Cabeceras = @{}, $Cuerpo = $null, [string]$Quien)
    $opciones = @{ Uri = $Url; Method = $Metodo; Headers = $Cabeceras; UseBasicParsing = $true }
    if ($null -ne $Cuerpo) {
        $opciones.Body = [Text.Encoding]::UTF8.GetBytes(($Cuerpo | ConvertTo-Json))
        $opciones.ContentType = "application/json; charset=utf-8"
    }
    try { $codigo = [int](Invoke-WebRequest @opciones).StatusCode }
    catch { if ($null -eq $_.Exception.Response) { throw }; $codigo = [int]$_.Exception.Response.StatusCode }
    Write-Host ("{0,-11} {1,-6} {2,-28} -> {3}" -f $Quien, $Metodo, $Url.Replace($Base, "/api"), $codigo)
}

# 1. El agente pide su token con usuario y clave (Invoke-RestMethod convierte el JSON de respuesta).
$login = @{ username = "agente"; password = "agente12345" } | ConvertTo-Json
$token = (Invoke-RestMethod "$Base/token/" -Method Post -Body $login -ContentType "application/json").token
Write-Host "Token del agente: $token`n"
$conToken = @{ Authorization = "Token $token" }

# 2. Sin token: los pedidos piden credenciales -> 401 (no sé quién eres).
Get-Codigo GET "$Base/pedidos/" -Quien "sin token"
# 3. Con el token del agente: ya sabe quién es y puede leer los pedidos -> 200.
Get-Codigo GET "$Base/pedidos/" -Cabeceras $conToken -Quien "agente"
# 4. Con el token del agente: sabe quién es, pero no es personal de la tienda -> 403 (sé quién eres y no puedes).
Get-Codigo PATCH "$Base/productos/3/" -Cabeceras $conToken -Cuerpo @{ stock = 24 } -Quien "agente"
Get-Codigo POST "$Base/pedidos/6/anular/" -Cabeceras $conToken -Quien "agente"
