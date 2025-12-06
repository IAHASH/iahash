🛣 IA-HASH · Roadmap oficial

Este roadmap define todas las fases necesarias para construir IA-HASH desde la primera versión funcional (v1.0) hasta la visión completa del estándar (v3+).
Está diseñado para ser simple, modular y ejecutable, con prioridad total a:

claridad

robustez criptográfica

rendimiento

neutralidad del estándar

facilidad de adopción

🚀 FASE 1 — v1.0 (Completada / estabilizando)

El objetivo de esta fase es obtener un sistema funcional de emisión y verificación IA-HASH, usable tanto por humanos como por sistemas.

✅ 1. Arquitectura base

Reorganización del repo: /iahash, /api, /web, /docs, /scripts.

Limpieza de módulos, imports y dependencias.

Estructura estándar de librería Python.

Claves Ed25519 + issuer.

Estándar JSON IAHASH-1.

✅ 2. Emisión IA-HASH ("Issuer")

Normalización de prompt, respuesta y contexto.

Hash SHA256: h_prompt, h_respuesta.

Construcción de h_total.

Firma Ed25519 (firma_total).

Generación del paquete IA-HASH.

✅ 3. Verificador offline

Re-cálculo de hashes.

Verificación de la firma.

Validación de consistencia.

✅ 4. UI Mínima funcional

Página única para emitir.

Página única para verificar.

Interfaz limpia, inspirada en Flarum + diseño “neutral técnico”.

Copiar JSON.

Descarga JSON.

🔧 Pendiente menor (1.0.x)

Mejoras visuales.

Mejorar mensajes de error.

Refinar estados VALID / INVALID / WARNING.

Sanitizar inputs.

🧭 FASE 2 — v1.1 (En construcción)

Aquí construimos la versión “utilizable para el mundo real”: master prompts, secuencias, exportaciones, plantillas y soporte multi-modelo.

🎯 Objetivo general

Convertir IA-HASH en una herramienta práctica para:

CVs

informes

análisis

diagnósticos personales

auditorías técnicas

educación

contenido profesional

🔹 1. Master Prompts (v1.1 core)

Implementar prompts oficiales IA-HASH “certificados”:

CV Honesto v1

Análisis psicológico (no clínico)

Autoevaluación profesional

Auditoría técnica básica

Requisitos:

Editable en UI y API.

Guardado directo en JSON.

Versión y hash propios (PROMPT-ID).

Compatible con cualquier LLM.

🔹 2. Sistema de Secuencias (Prompt Flow IA-HASH)

Permite generar:

Un único IA-HASH para una secuencia de pasos.

O varios IA-HASH encadenados (1 por paso).

Ideal para análisis largos o CVs evolutivos.

MVP:

UI para añadir pasos.

API para recibir steps[].

IA-HASH final incluye:

n_steps

hash_steps[]

h_total_sequence

🔹 3. Módulo “Conversación → IA-HASH”

Extracto verificable de una conversación completa con un LLM.

Opciones:

Seleccionar mensajes manualmente

Auto-resume

Export completo

Resultado:

IAHASH-CONVERSATION-1
h_conversation
h_prompt
h_respuesta
firma_total

🔹 4. Exportaciones

JSON (actual)

TXT (raw text + IA-HASH footer)

Markdown

IA-HASH Lite (formato compacto, 1 línea)

Para el futuro: PDF con sello IA-HASH

🔹 5. Verificador avanzado (v1.1)

Validación estructural JSON

Explicación de diferencias si se detectan

Vista previa del contenido normalizado

Colores semáforo (OK / WARNING / INVALID)

Enlace para comparar con fuente original

🧱 FASE 3 — v2.0 (Estándar completo)

IA-HASH deja de ser solo una librería: se convierte en un protocolo estándar.

🌐 1. Especificación oficial (Specs v2)**

Documento completo que describe:

Normalización

Algoritmos

Firmas

Campos obligatorios/opcionales

Versionado

Compatibilidad

Reglas de interoperabilidad

Formato:
/docs/specs/IAHASH-v2.md

🧩 2. SDK oficial

Lenguajes objetivo:

Python

JavaScript

Rust

Go

Incluye:

Normalización

Hashing

Firma

Validación

Utilidades de prompts

🪪 3. Identidad delegada

Permite que:

Empresas

Universidades

Instituciones

Actúen como issuers verificados bajo su propia clave.

Útil para:

Exámenes

Auditorías

Certificaciones profesionales

Laboratorios IA

📚 4. Repositorio de plantillas IA-HASH

Repositorio público con plantillas oficiales y comunitarias:

CVs

diagnósticos

marcos analíticos

informes

cursos

exámenes

pruebas técnicas

🔍 5. Extensión multimodal (texto + imagen + audio)

Generar hashes de:

imágenes

waveform

embeddings

Ejemplo futura versión:

h_image
h_audio
h_text
h_total
firma_total

🛡 FASE 4 — v3.0 (Ecosistema IA-HASH)

La visión final: IA-HASH como estándar cultural, técnico y social.

🌍 1. IA-HASH Registry (opcional)

Registro público y descentralizado

Para IA-HASHs que quieran hacerse públicos

Similar a un DOI para IA generada

🔗 2. Integración con blockchain (opcional)

Para proyectos que requieran inmutabilidad absoluta

No obligatorio

Módulo complementario

👥 3. Comunidad IA-HASH

Chat público

Documentación colaborativa

Mejora de propuestas (IAH-Ps, tipo RFCs)

Extensiones del protocolo

📦 4. IA-HASH Cloud (opcional, open-source)

Self-hosted

Gestión de claves

Emisiones firmadas

Backups

Auditorías

🧲 ALCANCE DEL MVP COMPLETO (lo que Codex debe construir ya)
Backend

Issuer completo

Verificador completo

Normalización robusta

Firmas Ed25519

API pública /issue, /verify

Master prompts

Secuencias

Conversación → IA-HASH

Exportadores

Frontend

Panel unificado

UI moderna y neutral (inspiración Flarum)

Editor avanzado de prompts

Constructor de secuencias

Verificador comparativo

Documentación integrada

DevOps

Docker

Healthcheck correcto

Variables env

Soporte Coolify

Clave pública accesible

🏁 Conclusión

IA-HASH no es una aplicación.
No es una web.
Es un estándar.
