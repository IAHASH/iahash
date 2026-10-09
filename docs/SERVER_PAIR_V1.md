# Servidor de referencia y operación LAB

Este servicio importa exclusivamente `iahash_core` y `iahash_server`. No monta
la API ni los extractores históricos. Instalar Python3.12 y
`python -m pip install -c constraints-reference.txt '.[server,test]'`.

## Identidad y arranque local

Crear un directorio privado propiedad del operador. En Windows, proteger sus
ACL NTFS: chmod/0600 no demuestra privacidad en NTFS. Copias y claves requieren
la misma protección. No subir material privado ni tokens al repositorio.

Inicialización explícita de una identidad LAB nueva:

```text
python -m iahash_server init-key --private lab-private/issuer.private --public lab-private/issuer.pub
python -m iahash_server serve --db lab-private/registry.sqlite --private lab-private/issuer.private --issuer-id operator.lab --environment LAB
```

Antes de arrancar, suministrar IAHASH_API_TOKEN por entorno con un secreto local
de al menos32 caracteres. El token no se imprime ni se guarda en SQLite. Bind
por defecto127.0.0.1:8000. Un proxy TLS y acceso externo requieren configuración
operativa separada; esta campaña no expone un servicio.

La inicialización no sustituye archivos existentes. Pública ausente: derivar
de la privada conservada. Privada ausente con pública existente: detener y
restaurar identidad; no crear otra. Claves incompatibles: error explícito.

## API y persistencia

Namespace `/api/pair-v1`: POST receipts (P y Idempotency-Key64hex), GET
receipts/{UUID4}, POST verify ({certificate, originals?}), GET issuer,
GET health y ready. Las dos últimas devuelven estados mínimos; el resto exige
Bearer token. Errores: `{error:{code,message}}`, sin volcar excepciones.
Nuevo recibo201; misma clave/P200 con bytes idénticos; otra P409.
Verificación malformada422; firma/trust/contenido negativo200 con resultado
explícito. Originales solamente en memoria durante verificación, nunca en DB.

60 solicitudes/minuto por token del proceso, cuatro escrituras simultáneas,
16KiB de emisión, 3MiB de verificación y1MiB por original.429 incluye Retry-After.
Límites locales al proceso: operar un único proceso servidor por base/token.
SQLite WAL/FULL, BEGIN IMMEDIATE, busy_timeout5000; responder tras commit.
Base/identidad/esquema desconocido falla sin borrado ni reinicialización.
Esta versión no tiene migrador, rotación automática ni purga de recibos.

## Copia, restauración y rollback

```text
python -m iahash_server backup --source lab-private/registry.sqlite --output lab-private/snapshot.sqlite
python -m iahash_server restore --source lab-private/snapshot.sqlite --output lab-private/restored.sqlite
```

Son copias SQLite consistentes a archivos nuevos con integrity_check. Nunca
sobrescriben el origen ni un destino. Un fallo conserva la salida parcial para
diagnóstico; no usarla como restauración válida. Conservar aparte privada,
pública y configuración de identidad/entorno; la DB no contiene la privada.
Ensayar el arranque de restored.sqlite con la misma identidad, comprobar conteo,
firmas y replay exacto antes de elegirla como base operativa. Mantener la original.
Rollback: detener candidato, conservar datos/claves, volver al último binario
compatible y usar una copia ensayada. No abrir esta DB con el servidor histórico.

## Docker aislado

`docker build -f Dockerfile.reference -t iahash-reference:lab .` crea imagen
Python3.12 con versiones de librerías fijadas, UID10001 y sin claves incorporadas.
El tag de imagen base no fija un digest: no se promete reproducción bit a bit.
`python tools/docker_reference_smoke.py --image iahash-reference:lab` prueba con
identidad sintética, volumen temporal, network=none y ningún puerto publicado:
reinicio, persistencia, firma, backup y restauración. Elimina solamente sus
contenedores/volumen de nombres únicos. No ejecutarlo contra datos operativos.

Docker no está instalado en Torre Cabral al preparar esta entrega; consultar
el resultado CI del SHA exacto antes de dar por superada esa comprobación.
La nueva suite reference_tests está separada de los fallos históricos; una
prueba nueva verde no declara sano el servicio legado.
