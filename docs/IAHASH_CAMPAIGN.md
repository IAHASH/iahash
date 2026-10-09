# IA-HASH — Estado de campaña

Actualizado: 2026-10-10, Europe/Madrid. Sobremesa es Torre Cabral, confirmado
por el propietario. Se ejecutaron tres workers locales concurrentes más el
coordinador; archivos entregados y reservas liberadas. Detalle en
IAHASH_WORKER_EXECUTION.md. No quedan workers residentes ni servicio publicado.

## Contrato y alcance

D1/D2/D3 aprobadas para desarrollo: G1 satisfecho. Única modificación humana:
mínimo tres workers en Torre, ampliables a seis o más si es factible. La sesión
admite tres workers más coordinador; no se ejecutaron seis. Contrato y decisiones:
IAHASH_PRODUCT_CONTRACT.md e IAHASH_DECISIONS.md.
Base auditada: v1.2@96922745e9062b752c163420d4274215f5a6b3ab.

Referencia implementada: Core offline, Server independiente durable, Client
hash-only con cola, simulador sintético Maia, Docker no-root y backup/restore.
Paquetes nuevos iahash_core/iahash_server/iahash_client; no importan legacy ni
modifican Maia. La API histórica queda separada del nuevo servicio.

## Entregas y estados

| PR / SHA probado | Implementado | Probado | Revisado | Fusionado / desplegado |
| --- | --- | --- | --- | --- |
| [40](https://github.com/IAHASH/iahash/pull/40) | Contrato, decisiones, auditoría, campaña y vectores históricos | Vector Ubuntu PASS en 1953213e650ceae52db0d13fab6ed9ef946827a0; posteriores commits documentales | Contrato aprobado para desarrollo; revisión final humana pendiente | No / No |
| [41](https://github.com/IAHASH/iahash/pull/41) / 06f01372b2c1ced21f46f85de7ca7530d507bfb5 | Preservar SQLite/claves históricos | 25 locales y 25 Ubuntu, shell PASS | Worker QA/coordinador; revisión humana pendiente | No / No |
| [42](https://github.com/IAHASH/iahash/pull/42) / 534972853651d3bc7715b6d4bc7bded6c6db86af | Core, vector PAIR-1, lector legacy limitado | 79 locales, 79 Windows y 79 Linux CI | Core/coordinador; revisión humana pendiente | No / No |
| [43](https://github.com/IAHASH/iahash/pull/43) / 67965fd69afdcf2dcf50afe4c50eca42317899ee | Server, CLI, Docker, operaciones | 107 locales, 107 Windows y 107 Linux CI; Docker PASS | Server/Core/QA/coordinador; revisión humana pendiente | No / No |
| [44](https://github.com/IAHASH/iahash/pull/44) / c944c8da9c5fce7aa8f3e4ffb209ed194315413e | Client, E2E, simulador y concurrencia | 181 locales, 181 Windows y 181 Linux CI; simulador/stress/Docker PASS | Client/Core/QA/coordinador; revisión humana pendiente | No / No |

Todas son borradores. 42 tiene base v1.2; 43 tiene base42; 44 tiene base43.
Revisar en ese orden; retargetear las siguientes después de decidir cada merge.
PR41 sigue independiente, sin fusionar: la preservación de la DB nueva se
implementó por separado. PR39/v2 sigue abierta/conflictiva; no sustituye esta
referencia. No se duplicaron PR40/41 ni se creó otra campaña.

## Evidencia

- Core [CI38001423485](https://github.com/IAHASH/iahash/actions/runs/38001423485):
  Windows job114060141736: 79 passed, 0.36s; Ubuntu114060141973: 79 passed, 0.38s.
- Server [CI38001584086](https://github.com/IAHASH/iahash/actions/runs/38001584086):
  Windows114060659846: 107 passed, 2.86s; Ubuntu114060660067: 107 passed, 1.28s;
  Docker114060659713: build y ciclo de vida/restore PASS.
- Integrado [CI38001741367](https://github.com/IAHASH/iahash/actions/runs/38001741367):
  Windows114061179129: 181 passed, 10.64s; Ubuntu114061179054: 181 passed, 2.63s;
  ambos simulador y stress PASS; Docker114061178868 PASS.
- Torre local: 181 passed, 8.89s, XML lab-results/reference-final-windows.xml;
  ensayo lab-results/torre-cabral-recovered.json. No se subieron DB, privadas ni
  tokens. CI conserva XML y JSON como artifacts.
- PR41 [CI37999377119](https://github.com/IAHASH/iahash/actions/runs/37999377119/job/114053441814):
  25 passed, 4.36s y sh -n start.sh. Vector histórico
  [CI37999715192](https://github.com/IAHASH/iahash/actions/runs/37999715192/job/114054541559).

Suite nueva181 = 79 Core + 24 Server + 70 Client + 4 operaciones + 2 E2E + 2 stress.
Una advertencia Starlette/httpx queda para seguimiento de dependencias. No se
ocultaron fallos históricos: colección aborta por _collect_messages ausente;
resto 26 passed / 9 failed / 3 skipped. IAHASH_BASELINE_AUDIT.md conserva detalle.
La suite nueva verde no declara sano el servicio legado completo.

## Revisión cruzada y concurrencia

Corregidos antes de publicar: SQLite sin cierre en Windows; conexión de backup
filtrada al fallar destino; Retry-After sin persistir en último intento; respuesta
HTTP descargada antes del límite; ensayo que declaraba PASS sin emitir recibos.
Las regresiones ahora comprueban esos fallos efectivos.

Cada ensayo local1/3/6 usa 12 pares, 24 llamadas de onda y 24 de recuperación.
Siempre termina con 12 recibos únicos, firmas válidas, integridad e idéntico
replay. Onda local6: 5 nuevas/19 respuestas429; recuperación final12/12.
No es benchmark productivo ni mide agentes. El límite de cuatro escrituras se
conserva; ampliar workers no elimina ese límite.

## Pendiente

1. Revisión humana de40/41/42/43/44; sin merge ni despliegue automático.
2. Ejecutar el SHA de44 en Work Cloud desde ChatGPT de Torre y en WinWork desde
   portátil/fábrica, según aclaración del propietario. Aún no ejecutados. Paquete:
   IAHASH_ENVIRONMENT_HANDOFF.md.
3. Prueba distribuida contra Torre requiere conexión/endpoint LAB y límites
   identificados. El harness actual es local sintético y no acepta URL externa.
4. Antes de operación pública: resolver exposición/auth/SSRF del legado o mantener
   aislamiento, decidir identidad operativa, retención y TLS. No se probaron
   proveedores reales ni compatibilidad de todos los certificados históricos.

La referencia mínima es un candidato LAB implementado y validado. No declara
terminado el ensayo WinWork/Work Cloud, la seguridad del legado, la integración
real Maia ni una operación productiva. El siguiente coordinador debe leer este
estado y heads/CI antes de crear trabajo, evitando duplicados.
