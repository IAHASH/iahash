
---

```md
# IA-HASH — Universal Pair Verification Protocol

IA-HASH is a lightweight cryptographic protocol designed to verify the integrity of a **Pair** — two elements whose relationship matters.

It began as a verifier for AI prompt–response interactions.  
It has evolved into a **general-purpose standard** for validating relationships between any two meaningful elements.

---

## 🌱 What Is IA-HASH?

IA-HASH v2.0 provides a simple mechanism to:

- Take **PAR 1** and **PAR 2**
- Normalize and hash them independently
- Combine them into a canonical `pair_hash`
- Sign the result using Ed25519
- Produce a portable IA-HASH document
- Verify that document anywhere, without relying on external providers

The protocol is:

- **Minimal**  
- **Auditable**  
- **Provider-agnostic**  
- **Secure**  
- **Easy to implement**

---

## 🔗 Why Pairs?

Most meaningful relationships in the real world are just pairs:

- Prompt + Response  
- Contract + Company  
- Author + Work  
- Scientist + Report  
- Original + Translation  
- Code + Commit Message  
- Claim + Evidence  
- Property + Owner  
- Document + Signer  

IA-HASH v2 proves:

> “These two elements belonged together, exactly like this, at this moment in time.”

---

## ✨ Key Features

### **Minimal Core**
The entire protocol is implemented in a small, clean module (`iahash/core/`) containing:

- Pair model  
- Text normalization  
- SHA-256 hashing  
- Ed25519 signing and verification  
- IA-HASH document builder  
- Verification engine  
- Strict protocol version handling  

Everything is intentionally simple and transparent.

---

### **Universal & Provider-Agnostic**
IA-HASH works with:

- Human text  
- Generated text  
- Contracts  
- Legal documents  
- Scientific reports  
- Binary files (v2.1+)  
- AI conversations (future adapters)  

No dependencies on OpenAI, Claude, Gemini, or any external API.

---

### **Clean API**
A minimal FastAPI backend exposes:

- `POST /api/issue/pair`
- `POST /api/verify`
- `GET /public-key`
- `GET /health`

Nothing more. Nothing less.

---

### **Elegant Single-Page UI**
IA-HASH includes a simple, modern interface to:

- Issue a Pair  
- Verify an IA-HASH document  
- Read the essentials  
- Explore documentation and GitHub  

Inspired by clean ecosystems like Flarum and GitHub.

---

### **Legacy Preserved**
All v1.x functionality (prompt/response verification, extractors, sequences…)  
is archived in:

```

docs/READMEV.1.2.md

````

It remains available for historical reference.

---

## 📄 IA-HASH Document Example (v2.0)

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

To verify a Pair, users provide:

* The IA-HASH document
* PAR 1
* PAR 2

IA-HASH recomputes hashes, validates the signature, and produces a clear result.

---

## 🚀 Getting Started

### **Run with Docker**

```bash
docker build -t iahash:v2 .
docker run --rm -p 8000:8000 iahash:v2
```

### **Run locally (Python ≥ 3.10)**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn api.main:app --reload
```

---

## 🔧 API Usage

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

## 📁 Project Structure (v2.0)

```
iahash/
  core/          # Protocol logic
  adapters/      # Optional integrations (LLMs, files…)
  storage/       # Optional DB helpers

api/
  main.py        # FastAPI application

web/
  static/        # CSS / JS
  templates/     # Single-page UI

docs/
  PROTOCOL_2.0.md
  ARCHITECTURE_2.0.md
  ROADMAP_v2.md
  VISION.md
  READMEV.1.2.md   # Historical record of v1.x
```

---

## 🗺 Roadmap

* **v2.0** — Universal Pairs, minimal API + UI
* **v2.1** — Binary file support
* **v2.2** — Authenticity via LLM backend APIs (when allowed)
* **v2.3** — Adapter ecosystem (URLs, S3, Git, OCR…)
* **v3.0** — User identity layer (dual signatures)
* **v3.x** — SDKs and CLI tools

Full roadmap: `docs/ROADMAP_v2.md`

---

## 🤝 Contributing

Contributions are welcome.
Please follow these principles:

* Clarity
* Simplicity
* Auditability
* Public benefit
* Minimalism

Open issues and pull requests should target the `v2` branch.

---

## ⚖ License

IA-HASH is released under the **Apache License 2.0**.
You are free to use, modify, integrate, and distribute the project, with strong patent protections.

See [`LICENSE`](./LICENSE) for full details.

```

