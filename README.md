Perfecto.
He captado **exactamente** la calidad, el ritmo, la estructura y el estilo editorial del README que dejó Gemini:

* limpio
* profesional
* explicativo
* con secciones cortas y precisas
* visualmente agradable
* sin tecnicismos innecesarios
* muy “GitHub enterprise ready”
* apto tanto para devs como para curiosos
* tono elegante, seguro y moderno

Ese estilo **lo replico ahora**, pero sobre **IA-HASH v2**, su nueva filosofía y arquitectura.

Aquí tienes el **README v2 definitivo**, listo para pegar como `README.md` en la rama `v2`.

---

# ✅ README v2 — estilo Gemini “premium”, en inglés, para GitHub

````md
# IA-HASH — Universal Pair Verification Protocol

IA-HASH is a lightweight, cryptographic protocol for verifying the integrity of a **Pair**:  
two elements whose relationship matters.

It began as a system to verify AI prompt–response interactions.  
It evolved into something much more powerful:  
a universal method to register and validate meaningful relationships between any two elements.

---

## Overview

IA-HASH v2.0 provides a simple way to:

- Take two items — **PAR 1** and **PAR 2**  
- Normalize and hash them independently  
- Combine them into a canonical `pair_hash`  
- Sign the result using Ed25519  
- Produce a portable IA-HASH document  
- Verify that document anywhere, without external dependencies

The protocol is minimal, auditable, and provider-agnostic.  
It works equally well with human text, files (v2.1+), generated content, legal records, translations, code artifacts, and more.

---

## Why Pairs?

Many real-world relationships are simply pairs:

- **Prompt + Response**  
- **Contract + Company**  
- **Author + Work**  
- **Scientist + Report**  
- **Original + Translation**  
- **Claim + Evidence**  
- **Code + Commit Message**  
- **Property + Owner**  
- **Document + Signer**

IA-HASH provides a lightweight, open, cryptographically signed way to prove:

> “These two things belonged together exactly like this, at this moment in time.”

---

## Key Features

### **✔ Minimal Core**
A small, focused implementation under `iahash/core/`:

- Pair model  
- Normalization  
- SHA-256 hashing  
- Ed25519 signing  
- IA-HASH document builder  
- Verification engine  
- Strict protocol versioning  

The entire system is intentionally simple and transparent.

---

### **✔ Universal and Provider-Agnostic**
IA-HASH does not depend on:

- AI models  
- Proprietary APIs  
- Cloud services  
- Closed ecosystems  

It operates purely on the bytes you provide.  
This makes it ideal for:

- Legal tech  
- Scientific reproducibility  
- Authorship and ownership proofs  
- Document integrity  
- Academic citations  
- AI transparency  
- Code provenance  

---

### **✔ Clean API**
IA-HASH exposes a small FastAPI backend:

- `POST /api/issue/pair`  
- `POST /api/verify`  
- `GET /public-key`  
- `GET /health`  

No unnecessary endpoints.  
No heavy dependencies.

---

### **✔ Simple Web Interface**
A single, elegant page that lets you:

- Issue an IA-HASH pair  
- Verify an IA-HASH document  
- Learn the basics  
- Explore the project and documentation  

Inspired by timeless, clean designs like Flarum, GitHub and simple.dev patterns.

---

### **✔ Legacy Preserved**
All v1.x functionality (prompt/response extractors, sequences, flows, old UI…)  
is kept under `docs/READMEV.1.2.md` for historical reference.

The protocol is new — the history remains available for context.

---

## IA-HASH Document (v2.0 Example)

```json
{
  "protocol_version": "IAHASH-2.0",
  "issuer_id": "iahash.com",
  "timestamp": "2025-12-08T20:00:00Z",

  "par1_hash": "a1f5c8...",
  "par2_hash": "b7c9de...",
  "pair_hash": "d3e478...",

  "signature": "f1a2bc...",

  "metadata": {
    "label": "author + work",
    "notes": "Optional metadata attached to this Pair."
  }
}
````

To validate a Pair, users provide:

* The IA-HASH document
* PAR 1
* PAR 2

The system recomputes all hashes, checks the signature, and returns a clear verdict.

---

## Getting Started

### **Run with Docker**

```bash
docker build -t iahash:v2 .
docker run --rm -p 8000:8000 iahash:v2
```

### **Run locally (Python ≥ 3.10)**

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: set key paths
export IAHASH_PRIVATE_KEY_PATH=keys/issuer_private.key
export IAHASH_PUBLIC_KEY_PATH=keys/issuer_public.key

uvicorn api.main:app --reload
```

---

## API Summary

### **Issue a Pair**

`POST /api/issue/pair`

```json
{
  "par1": "Element A",
  "par2": "Element B",
  "metadata": { "label": "example" }
}
```

### **Verify a Pair**

`POST /api/verify`

```json
{
  "iah_document": { "...": "IA-HASH document" },
  "par1": "Element A",
  "par2": "Element B"
}
```

---

## Project Structure (v2.0)

```
iahash/
  core/          # Protocol logic
  adapters/      # Future integrations (optional)
  storage/       # Optional database helpers
api/
  main.py        # FastAPI service
web/
  static/        # CSS, JS, assets
  templates/     # Single-page UI
docs/
  PROTOCOL_2.0.md
  ARCHITECTURE_2.0.md
  ROADMAP_v2.md
  VISION.md
  READMEV.1.2.md   # Historical v1.x reference
```

---

## Roadmap

* **v2.0** — Universal Pairs, minimal API & UI
* **v2.1** — Binary/file support
* **v2.2** — Authenticity via LLM backend APIs (when available)
* **v2.3** — Adapter ecosystem (URLs, S3, Git, OCR)
* **v3.0** — Identity layer (user keypairs + dual signatures)
* **v3.x** — SDKs and CLI tooling

See `docs/ROADMAP_v2.md` for the complete plan.

---

## Contributing

Contributions are welcome.
Please follow the project’s principles:

* clarity
* simplicity
* auditability
* minimalism
* public benefit

Open issues, ideas, and PRs against the `v2` branch.

---

## License

IA-HASH is released under the **Apache License 2.0**.
You are free to use, modify, integrate, and distribute the project with strong patent protections.

See the [`LICENSE`](./LICENSE) file for more information.

```

---


¿Cuál quieres que salga primero?
```
