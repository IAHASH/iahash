

````markdown
# ✍️ IA-HASH — Universal Pair Verification Protocol

IA-HASH is a lightweight, cryptographic protocol for verifying the integrity of a **Pair**: two elements whose relationship matters.

It began as a system to verify AI prompt–response interactions. It evolved into something much more powerful: a universal method to register and validate meaningful relationships between any two elements.

---

## 🧭 Overview

IA-HASH v2.0 provides a simple, four-step process to achieve provable integrity:

1.  Take two items — **PAR 1** and **PAR 2**.
2.  Normalize and hash them independently, then combine them into a canonical `pair_hash`.
3.  Sign the result using robust Ed25519 cryptography.
4.  Produce a portable, self-contained **IA-HASH document**.

The protocol is minimal, auditable, and provider-agnostic. It works equally well with human text, files (v2.1+), generated content, legal records, translations, code artifacts, and more.

---

## 🤝 Why Pairs?

Many critical real-world relationships are simply pairs:

* **Prompt + Response** (AI Integrity)
* **Contract + Company** (Legal Tech)
* **Author + Work** (Ownership Proof)
* **Scientist + Report** (Reproducibility)
* **Original + Translation** (Media Integrity)
* **Claim + Evidence** (Fact Verification)
* **Code + Commit Message** (Software Provenance)
* **Document + Signer** (Digital Notarization)

IA-HASH provides a lightweight, open, cryptographically signed way to prove:

> “These two things belonged together exactly like this, at this moment in time, as certified by the issuer.”

---

## ✨ Key Features

### **1. Minimal Core**
A small, focused implementation under `iahash/core/` handles:

* Pair model and strict normalization rules
* SHA-256 hashing and aggregation
* Ed25519 signing and verification
* IA-HASH document builder and strict verification engine
* Strict protocol versioning and error codes

The entire system is intentionally simple and transparent for auditing.

### **2. Universal and Provider-Agnostic**
IA-HASH does not depend on:

* AI models or proprietary APIs
* Cloud services or centralized providers
* Closed ecosystems

This makes it an ideal building block for:

* Legal tech and document integrity
* Scientific reproducibility
* Authorship and ownership proofs
* AI transparency
* Code provenance

### **3. Clean API**
IA-HASH exposes a small FastAPI backend with only essential endpoints:

* `POST /api/issue/pair` (Sign a new Pair)
* `POST /api/verify` (Validate an IA-HASH document)
* `GET /public-key` (Issuer's public key)
* `GET /health` (Status check)

### **4. Simple Web Interface**
A single, elegant page allows users to:

* Issue an IA-HASH pair
* Verify an IA-HASH document
* Read the basics and documentation

### **5. Legacy Preserved**
All v1.x functionality (prompt/response extractors, sequences, flows, old UI…) is preserved under `docs/READMEV.1.2.md` for historical context and reference.

---

## 📜 IA-HASH Document (v2.0 Example)

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

> **To validate a Pair**, the verifying party must provide:
>
> 1.  The IA-HASH document (above)
> 2.  The original PAR 1
> 3.  The original PAR 2
>
> The system recomputes all hashes, checks the signature, and returns a clear verdict: **VALID** or **INVALID**.

-----

## 🚀 Getting Started

### **Run with Docker**

```bash
docker build -t iahash:v2 .
docker run --rm -p 8000:8000 iahash:v2
```

### **Run locally (Python ≥ 3.10)**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: set key paths (necessary for issuing)
export IAHASH_PRIVATE_KEY_PATH=keys/issuer_private.key
export IAHASH_PUBLIC_KEY_PATH=keys/issuer_public.key

uvicorn api.main:app --reload
```

-----

## 💡 API Summary

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

-----

## 🌲 Project Structure (v2.0)

```
iahash/
  ├── core/          # 🔑 Protocol logic
  ├── adapters/      # Future integrations (optional)
  └── storage/       # Optional database helpers
├── api/
  └── main.py        # FastAPI service
├── web/
  ├── static/        # CSS, JS, assets
  └── templates/     # Single-page UI
└── docs/
  ├── PROTOCOL_2.0.md
  ├── ARCHITECTURE_2.0.md
  ├── ROADMAP_v2.md
  ├── VISION.md
  └── READMEV.1.2.md # Historical v1.x reference
```

-----

## 🧭 Roadmap

  * **v2.0** — Universal Pairs, minimal API & UI (Current Stable)
  * **v2.1** — Binary/file support
  * **v2.2** — Authenticity via LLM backend APIs (when available)
  * **v3.0** — Identity layer (user keypairs + dual signatures)

See `docs/ROADMAP_v2.md` for the complete plan.

-----

## 💖 Contributing

Contributions are welcome. Please adhere to the project’s core principles:

  * Clarity
  * Simplicity
  * Auditability
  * Minimalism
  * Public Benefit

Open issues, ideas, and PRs against the `v2` branch.

-----

## ⚖️ License

IA-HASH is released under the **Apache License 2.0**. You are free to use, modify, integrate, and distribute the project with strong patent protections.

See the [`LICENSE`](https://www.google.com/search?q=./LICENSE) file for more information.

```
