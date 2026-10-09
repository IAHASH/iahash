# Cliente durable y simulador

Instalar Python3.12 y `python -m pip install -c constraints-reference.txt '.[client]'`.
La aplicación calcula PAR localmente y entrega solo huellas. Una cola por proceso
cliente activo; los hilos del mismo cliente se serializan. El reinicio transforma
SENDING en PENDING conservando Idempotency-Key; no abrir una cola desde dos procesos.

```python
from pathlib import Path
from iahash_core import make_pair
from iahash_client import Client

# public_key: Ed25519PublicKey fijada por el operador fuera del certificado.
# trust = {(issuer_id, 'LAB', key_id(public_key)): public_key}
with Client(base_url=issuer_url, queue_path=Path('queue.sqlite'),
            api_token=token, trusted_keys=trust, expected_environment='LAB') as client:
    delivery_key = client.enqueue(make_pair('Prompt', 'Response'))
    delivery = client.send(delivery_key)
    # PENDING requiere reanudación; REJECTED requiere inspección; no fingir confirmación.
```

enqueue persiste antes de enviar. Cinco intentos máximos por ejecución, backoff
1/2/4/8 segundos más jitter, Retry-After persistente y presupuesto de espera30s.
Al agotar intentos o superar la espera, conserva PENDING y su fecha de reintento.
resume_pending no adelanta esa fecha tras reiniciar. CONFIRMED exige certificado
con firma, emisor fijado, entorno y PAR exactos. Repetir envío confirmado no
contacta al servidor.4xx definitivos/redirecciones/certificado falso: REJECTED.
Timeout,408,429,5xx: reintento limitado/PENDING, nunca pérdida de la clave.

HTTPS por defecto, sin redirecciones ni proxies heredados del entorno. Solo
LAB permite HTTP loopback con allow_insecure_localhost=True explícito.
Respuestas de certificado leídas por streaming hasta16KiB; codificación
comprimida rechazada. Cola almacena huellas, clave idempotente, estado, error
sanitizado y recibo confirmado; no originales, token ni privada. El operador
debe proteger el directorio/ACL y mantener espacio disponible. No hay purga.

Para el simulador Maia y pruebas integradas, instalar '.[server,client,test]':
`python tools/maia_simulator.py`. Usa únicamente prompt/respuesta sintéticos,
transportes en memoria y bases temporales. Demuestra productor→cola→API→recibo→
verificación offline de originales. No importa ni modifica Maia.

`python tools/lab_stress.py --output lab-results/trial.json` ejecuta tres ondas
locales acotadas con1/3/6 hilos,12 pares/24 solicitudes por onda y24 solicitudes
de recuperación por ensayo. Exige12 recibos, firmas válidas, integrity_check y
replay idéntico por cada clave. Solo503 no puede producir PASS. No acepta una
URL externa, una carga ilimitada ni un número arbitrario de hilos.
Son solicitudes concurrentes, no número de workers o prueba distribuida.
