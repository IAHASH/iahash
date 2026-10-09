# IA-HASH Core — referencia PAIR-1

Implementación nueva aislada en `iahash_core`; no importa el paquete legado,
HTTP, SQLite, configuración de entorno ni Maia. Python 3.12 con Unicode15.0.0.
Contrato aprobado para desarrollo en la campaña de [PR40](https://github.com/IAHASH/iahash/pull/40).
La aprobación no autoriza un merge ni un despliegue.

Instalación mínima: `python -m pip install -c constraints-reference.txt .`.
`make_pair(par1, par2)` calcula huellas y `derive_pair_id(pair)` vincula su orden.
Para bytes, declarar explícitamente `profile1='bytes-v1'` y/o `profile2='bytes-v1'`.
No se detecta ni convierte automáticamente un perfil.

`sign_receipt` exige clave Ed25519 suministrada, emisor, entorno, UUID4 y hora UTC
con seis decimales. Firma el cuerpo completo con separación de dominio.
`verify_receipt(certificate, trusted_keys=..., expected_environment='LAB', originals=...)`
separa esquema, firma, confianza, entorno, vinculación y contenido. El trust store
es un diccionario `(issuer_id, environment, key_id) -> Ed25519PublicKey`.
Una clave anunciada por un certificado no se convierte automáticamente en confiable.
Sin originales, el resultado puede ser VERIFIED_RECEIPT; ambos originales
coincidentes permiten VERIFIED_CONTENT. No afirma verdad, procedencia ni tiempo
independiente. No consulta URLs ni crea claves, recibos o archivos al importar.

`docs/vectors/pair-v1.json` fija bytes y firma deterministas con una semilla
pública de prueba. No usar esa semilla para una identidad operativa.
`python -m pytest -q reference_tests/test_reference_core.py` comprueba vectores,
manipulaciones, perfiles, Unicode, confianza, revocación y pureza offline.

`verify_legacy_v1_2(document, public_key, prompt_text=None, response_text=None)`
es un lector explícito y limitado del emisor histórico IA-HASH1.2: seis campos
separados por `|`, firma sobre el hexadecimal de h_total. Devuelve LEGACY_LIMITED
y comprobaciones individuales; la identidad/metadatos antiguos no están firmados.
No adivina otros formatos, elimina ambigüedades históricas ni modifica certificados.

El código histórico, sus formatos y su API siguen separados. Esta referencia
no corrige ni habilita exposición pública del servicio histórico.
