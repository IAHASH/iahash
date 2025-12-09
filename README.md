```md
# IA-HASH — Universal Pair Verification Protocol

IA-HASH is a lightweight, cryptographic protocol for verifying the integrity of a **Pair** —  
two elements whose relationship matters.

It began as a way to verify AI prompt–response interactions.  
It has evolved into a general and elegant standard for validating relationships between **any two meaningful elements**.

---

## 🌱 What Is IA-HASH?

IA-HASH v2.0 provides a simple, auditable mechanism to:

- Take **PAR 1** and **PAR 2**
- Normalize and hash them independently
- Combine them into a canonical `pair_hash`
- Sign the result using Ed25519
- Produce a portable IA-HASH document
- Verify that document anywhere

The protocol is:

- minimal  
- transparent  
- provider-agnostic  
- easy to integrate  
- secure by design  

---

## 🔗 Why Pairs?

Most human, legal, scientific and digital relationships are just pairs:

- Prompt + Response  
- Contract + Company  
- Author + Work  
- Scientist + Report  
- Original + Translation  
- Code + Commit Message  
- Claim + Evidence  
- Property + Owner  
- Document + Signer  

IA-HASH v2 proves, cryptographically:

> “These two elements belonged together, exactly like this, at this moment in time.”

---

## ✨ Key Features

### **✔ Minimal Core**
A compact module (`iahash/core/`) implementing:

- Pair model  
- Normalization  
- SHA-256 hashing  
- Ed25519 signing  
- IA-HASH document structure  
- Verification engine  

Intentionally simple. Easy to audit. Easy to extend.

---

### **✔ Universal & Provider-Agnostic**

IA-HASH works with:

- human text  
- generated text  
- legal documents  
- research notes  
- translations  
- code fragments  
- binary files (v2.1+)  
- AI conversations (future adapters)

You control the input.  
IA-HASH only cares about integrity.

---

### **✔ Clean & Modern API**

Minimal FastAPI endpoints:

- `POST /api/issue/pair`  
- `POST /api/verify`  
- `GET /public-key`  
- `GET /health`  

No complexity. No unnecessary overhead.

---

### **✔ Elegant Single-Page UI**

A simple, modern interface inspired by Flarum and GitHub:

- Issue a Pair  
- Verify a document  
- Understand IA-HASH at a glance  
- Explore the ecosystem  

Built to feel friendly, focused and minimal.

---

### **✔ Legacy Preserved**

All v1.x functionality (prompt/response validation, extractors, sequences…) lives as historical reference in:

```

docs/READMEV.1.2.md

````

v2 starts clean.  
v1 remains available.

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
    "notes": "Optional metadata for human context."
  }
}
````

To verify a Pair, users provide:

* the IA-HASH document
* PAR 1
* PAR 2

IA-HASH recomputes everything and validates the signature.

---

## 🚀 Getting Started

### **Run with Docker**

```bash
docker build -t iahash:v2 .
docker run --rm -p 8000:8000 iahash:v2
```

### **Run Locally (Python ≥ 3.10)**

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
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
  adapters/      # Optional integrations
  storage/       # Optional persistence
api/
  main.py        # FastAPI service
web/
  static/        # CSS / JS
  templates/     # Single-page UI
docs/
  PROTOCOL_2.0.md
  ARCHITECTURE_2.0.md
  ROADMAP_v2.md
  VISION.md
  READMEV.1.2.md   # Historical v1.x reference
```

---

## 🗺 Roadmap

* **v2.0** — Universal Pairs, minimal API + UI
* **v2.1** — Binary file support
* **v2.2** — Authenticity via LLM backend APIs (when permitted)
* **v2.3** — Adapter ecosystem (URLs, Git, OCR, S3…)
* **v3.0** — Identity layer (user keypairs + dual signatures)
* **v3.x** — SDKs and CLI tools

Full roadmap: `docs/ROADMAP_v2.md`

---

## 🤝 Contributing

Contributions are welcome.
Please follow the project principles:

* clarity
* simplicity
* auditability
* minimalism
* public benefit

PRs should target the `v2` branch.

---

## ⚖ License

IA-HASH is released under the **Apache License 2.0**.
You are free to use, modify, integrate and distribute the project
with strong protections for contributors and users.

See the [`LICENSE`](./LICENSE) file for details.

```
