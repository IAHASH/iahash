# IA-HASH — Workers en Torre Cabral

Fecha: 2026-10-10, Europe/Madrid. El propietario confirma que el hostname
Sobremesa corresponde a Torre Cabral. Se corrige la preparación anterior que
los trataba como máquinas distintas. WinWork y Work Cloud sí son entornos
separados, según aclaración posterior del propietario.

## Política y ejecución real

Contrato D1/D2/D3 aprobado para desarrollo con la única modificación humana:
mínimo tres workers en Torre, ampliables a seis o más si es factible. La sesión
permite cuatro agentes en total: coordinador y tres workers. No se han ejecutado
seis workers. Roles SecurityQA, Performance y Ops se cubrieron mediante revisión
cruzada y trabajo del coordinador; no son tres procesos extra.

Se ejecutaron tres workers concurrentes locales. Cada uno tuvo archivos
exclusivos dentro de iahash-next. El mirror no tiene checkout Git funcional;
se publica con árboles/commits atómicos del conector GitHub en ramas separadas.
Las reservas reales sustituyen el plan anterior de rutas hipotéticas iahash/core.

| Worker / identificador | Reserva entregada | Resultado |
| --- | --- | --- |
| Core / core_audit | iahash_core/__init__.py, prueba Core, vector pair-v1 | 79 casos PASS; revisión independiente Server/Client |
| Server / architecture_audit | iahash_server/app.py y __init__.py, prueba Server | 24 casos PASS; API/SQLite/errores/límites |
| Client / safety_qa | iahash_client/__init__.py, prueba Client | 70 casos PASS; revisión Ops y falso éxito del stress |
| Coordinador / root | Packaging, CLI/Docker, integración, simulador, stress, CI/docs/publicación | 8 casos propios PASS y ensayo Docker remoto |

Archivos entregados y reservas liberadas; cero workers ejecutando tareas al
cierre de implementación. Pico: tres workers más coordinador. No queda proceso
residente, automatización ni servicio publicado en Torre.

## Bases

Base histórica: v1.2@96922745e9062b752c163420d4274215f5a6b3ab. Contrato en PR40;
preservación legacy en PR41@06f01372b2c1ced21f46f85de7ca7530d507bfb5.
Ninguna está fusionada al código base. La referencia usa paquetes y bases de
datos separados, con preservación propia. PR apiladas: 42 Core → 43 Server →
44 Client; SHA y CI exactos en IAHASH_CAMPAIGN.md. Solo publica el coordinador.

## Recursos y entornos

Torre: Windows10, Python3.12, ocho procesadores lógicos y unos 32GB de RAM.
La lectura inicial aproximada de 17GB disponibles no demuestra capacidad de
seis agentes. Se mantuvo el límite real de la sesión. Ensayos sintéticos de
1/3/6 solicitudes concurrentes y recuperación PASS; no son agentes.

CI GitHub Windows/Linux y Docker es evidencia adicional distinta de Work Cloud
y WinWork. El propietario indica que ChatGPT de Torre puede enviar trabajos a
Work Cloud; WinWork requiere portátil o fábrica. Esta campaña no despachó esos
dos trabajos. Paquete preparado: IAHASH_ENVIRONMENT_HANDOFF.md.

Para ampliar workers: verificar slots de la nueva sesión, recursos y paquetes
independientes; reservar archivos/commit exactos y registrar host y resultados.
No duplicar PR ni renombrar la máquina: el propietario pospuso el cambio de nombre.
