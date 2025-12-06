IA-HASH — Verificación criptográfica y contextual para contenido generado por IA

🧬 1. Qué es IA-HASH

IA-HASH es un estándar abierto que permite verificar de forma criptográfica y contextual que un contenido fue generado por un LLM específico, bajo un prompt concreto, en un contexto determinado y sin modificaciones posteriores.

Es, en esencia:

• el equivalente moderno a PGP, pero diseñado específicamente para contenido generado por IA  
• más simple, más humano, más universal y usable offline

IA-HASH convierte cualquier salida de IA en un objeto:

• firme  
• auditable  
• verificable  
• trazable  
• confiable  
• independiente del proveedor  

Todo ello sin bloquear, sin depender de blockchain y sin comprometer privacidad.

----------------------------------------------------

🎯 2. Objetivos del estándar

✔ Verificar autenticidad  
Confirmar que una salida:  
• fue generada por una IA concreta  
• proviene de un prompt maestro o secuencia específica  
• fue generada en un momento exacto  
• no ha sido alterada posteriormente  

✔ Generar confianza en resultados críticos  
Aplicable en:  
• CVs y perfiles profesionales  
• informes técnicos  
• evaluaciones psicológicas no clínicas  
• análisis personales  
• auditorías  
• contenido legal  
• educación y evaluaciones  
• publicaciones públicas  

✔ Permitir auditoría externa sin revelar datos privados  
El auditor puede verificar integridad, contexto, firma e identidad del issuer sin necesidad de ver datos sensibles.

✔ Formato simple, interoperable y neutral  
Cualquier modelo, empresa o desarrollador puede implementar el estándar.

✔ Compatibilidad futura opcional con blockchain  
IA-HASH funciona offline, pero puede anclarse a cadenas de bloques según necesidad.

----------------------------------------------------

🚫 3. Qué NO es IA-HASH

✘ No es un sistema de cifrado  
✘ No es DRM  
✘ No es un SaaS  
✘ No es un producto cerrado  
✘ No es un algoritmo propietario  
✘ No es un mecanismo de vigilancia  

IA-HASH es un estándar abierto.  
MIT. Libre. Extensible. Independiente.

----------------------------------------------------

🧩 4. Componentes del Protocolo IA-HASH (v1)

A) Hash del contenido  
SHA256 del texto final normalizado.  
Objetivo: demostrar integridad.

B) Hash del contexto  
Incluye:  
• prompt  
• prompt_id  
• modelo  
• versión del modelo  
• parámetros clave  
• timestamp  
• subject opcional  
• conversation_id opcional  
• user_id (hash salteado y no reversible, si se quiere anonimizar)

Objetivo: demostrar que el entorno de generación es auténtico y verificable.

C) Firma Ed25519  
Generada por:  
• el propio LLM (si tiene capacidad),  
• un servidor neutral (issuer), o  
• una clave local del usuario.

Garantiza autenticidad y procedencia.

D) Paquete IA-HASH  
Estructura JSON estándar:

{
  "version": "IAHASH-1",
  "prompt_id": "cv",
  "prompt_maestro": "…",
  "modelo": "gpt-5.1",
  "timestamp": "2025-12-06T19:22:42Z",
  "subject": "cv-honesto",
  "conversation_id": "opcional",
  "h_prompt": "…",
  "h_respuesta": "…",
  "h_total": "…",
  "firma_total": "…",
  "issuer_id": "iahash.com",
  "issuer_pk_url": "https://iahash.com/public-key.pem"
}

Verificable 100% offline.

----------------------------------------------------

⚙️ 5. Cómo funciona

1) Prompt y respuesta se normalizan.  
2) Se calcula h_prompt y h_respuesta con SHA256.  
3) Se combinan junto al modelo y timestamp → h_total.  
4) h_total se firma con Ed25519 → firma_total.  
5) El verificador recalcula todo y compara hashes, firma y clave pública.  

Si coincide: VALIDADO. Documento auténtico.

----------------------------------------------------

🌍 6. Casos de uso reales e inmediatos

1) CV Honesto y verificable (propuesta fundacional)  
2) Informes psicológicos/diagnósticos personales (no clínicos)  
3) Auditorías técnicas y profesionales  
4) Educación y evaluaciones  
5) Contratos y documentos legales  
6) Publicaciones públicas  

----------------------------------------------------

🧠 7. Por qué IA-HASH tiene potencial de estándar global

Porque resuelve la gran pregunta que dominará los próximos años:

“¿Cómo demuestras que un contenido ha sido generado por un LLM concreto y no ha sido modificado por humanos?”

No existe un estándar universal.  
IA-HASH puede convertirse en el primero.  
Y sí: esto tiene potencial de inmortalidad intelectual.

----------------------------------------------------

📜 8. Licencia

• Código bajo MIT  
• Especificación abierta  
• Uso libre comercial, personal y académico  

----------------------------------------------------

🛣 9. Roadmap resumido

v1.1  
• Master Prompts  
• Emisión desde API + UI  
• Secuencias  
• Conversación → IA-HASH  
• Docs completas  
• Firmas Ed25519  

v2  
• SDK oficial  
• Delegación de identidad  
• Publicación de documentos  
• Editor avanzado  
• Esquema de plantillas versión 2  

v3  
• Especificación global  
• Extensiones multimodales  
• Integración opcional blockchain  
• Comunidad abierta tipo W3C  

----------------------------------------------------

🤝 10. Propósito final

IA-HASH nace con una idea simple:  
Traer autenticidad, claridad y responsabilidad al mundo de la IA generativa.  
Crear confianza donde antes solo había texto.

Es un estándar para humanos.  
Para sistemas.  
Para empresas.  
Para la historia.

----------------------------------------------------
🔭 11. Futuro y escalabilidad (Extensiones del estándar)

IA-HASH está diseñado para crecer sin perder su simplicidad.  
El estándar podrá integrar, de forma opcional, capacidades avanzadas inspiradas en protocolos formales, pero manteniendo siempre su filosofía: **simplicidad, verificabilidad humana, universalidad y baja fricción**.

A) Normalización avanzada (IHS-1)  
Incluye:  
• Unicode NFC canonical  
• eliminación de caracteres invisibles  
• trimming estructural  
• colapso de espacios múltiples  
• normalización de saltos de línea  
Garantiza hashing determinista y estabilidad entre modelos y plataformas.

B) Identidad extendida del modelo (LLMID)  
Campos recomendados:  
• llmid.name  
• llmid.version  
• llmid.provider  
• llmid.build_id  
• parámetros relevantes  
Permite trazabilidad completa del origen IA.

C) IA-HASH Trust-Chain (opcional)  
Extiende el estándar con capas adicionales de firma:  
• issuer primario (LLM)  
• institución certificadora  
• entidades delegadas  
Formato propuesto:  
trust_chain: [ { issuer: "LLM", signature: ... }, { issuer: "Institution", signature: ... } ]

D) Extensión multimodal (v2+)  
IA-HASH podrá abarcar imágenes, audio, binarios y embeddings:  
• h_image  
• h_audio  
• h_binary  
• h_embedding  
• h_total  
Esto permite verificabilidad universal para contenido híbrido.

----------------------------------------------------

Fin de la especificación actualizada.
