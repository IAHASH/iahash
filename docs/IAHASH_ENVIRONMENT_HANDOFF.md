# Ensayo reproducible en Work Cloud y WinWork

Preparado en Torre Cabral. Estos dos ensayos aún no fueron enviados/ejecutados.
Son entornos separados, confirmado por el propietario. Work Cloud puede recibir
trabajo desde ChatGPT de Torre; WinWork requiere portátil o fábrica. GitHub
Actions Windows/Linux no sustituye ninguno.

## Encargo listo para trasladar

Validar [PR44](https://github.com/IAHASH/iahash/pull/44), repositorio IAHASH/iahash,
commit exacto c944c8da9c5fce7aa8f3e4ffb209ed194315413e; pila42→43→44.
No fusionar, desplegar, tocar Maia, claves/DB operativas, DNS, secretos o
infraestructura. Usar checkout limpio fuera de sources sincronizados. Registrar
entorno observado, OS, Python/Unicode, SHA, comandos y resultados. No inventar
Torre como host cloud ni equiparar Work Cloud con GitHub Actions.

Python3.12/Unicode15.0.0; instalar en un entorno de pruebas aislado:

```text
python -m pip install -c constraints-reference.txt ".[server,client,test]"
python -m pytest -q reference_tests --junitxml=reference-results.xml
python tools/maia_simulator.py
python tools/lab_stress.py --output stress-results.json
```

Esperado: 181 pruebas, simulador VERIFIED_CONTENT y tres ensayos locales
acotados1/3/6 solicitudes, cada uno con12 recibos finales y replay/firmas/integridad
PASS. No son seis agentes. Duración máxima10min; ante error, parar y preservar
logs/cola sintéticos sin reintentar contra datos reales. No ampliar carga o red.
Conservar XML/JSON, salida/exitcode y SHA256 de informes; devolver enlace de chat
o artifact, defectos y diferencias. No adjuntar bases, tokens o privadas.

Docker es un paso separado, solo si ya está disponible y permitido. No instalarlo
ni crear recursos pagados para completar este ensayo:

```text
docker build -f Dockerfile.reference -t iahash-reference:lab .
python tools/docker_reference_smoke.py --image iahash-reference:lab
```

Usa volumen sintético efímero, network=none, sin puertos publicados; verifica
persistencia/reinicio/restore con identidad idéntica. Si Docker no está disponible,
marcar NO_EJECUTADO: CI del mismo SHA ya lo comprobó en Ubuntu.

## Ensayo distribuido posterior

El harness no acepta URL externa. Para medir productores Work Cloud y WinWork
contra Torre se necesita identificar conectividad, endpoint exclusivamente LAB
y límites. No abrir firewall/túneles ni copiar credenciales productivas como
atajo. Esa medición permanece pendiente; los ensayos locales de cada entorno
son la primera evidencia comparable.
