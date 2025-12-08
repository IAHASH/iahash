

````markdown
# IA-HASH: Universal Pair Verification Protocol v2.0

> A tiny, universal cryptographic protocol for verifying **Pairs** – relationships between two meaningful elements.

![IA-HASH logo](web/static/logo.png)

IA-HASH turns “this belongs to that” into a verifiable, signed fact. It does not care if the pair comes from AI, humans, code, contracts or files — it only cares about **integrity** and **proof of existence**.

---

## 💡 About IA-HASH v2.0

**IA-HASH** is a small, provider-agnostic protocol and reference implementation that lets you:

* Take two elements – **PAR 1** and **PAR 2**
* Normalize, hash, and combine them into a single `pair_hash`
* Wrap the hashes into a **signed IA-HASH document**
* Verify that document anywhere, independently of any provider

It started as a way to verify **AI prompt + response** pairs, and has successfully evolved into a **general-purpose Pair verification standard**.

---

## 🤝 Why Pairs? (The Core Idea)

Many critical relationships in the digital and real world are fundamentally just Pairs:

* **LLM Authenticity:** Prompt + Response (The origin)
* **Legal:** Contract + Company
* **Academic:** Scientist + Report
* **Media:** Original + Translation
* **Software:** Code + Commit Message
* **Ownership:** Property + Owner
* **Signature:** Document + Signer

IA-HASH v2.0 focuses on this core concept:

> “Given PAR 1 and PAR 2, prove that this specific relationship was registered by an issuer at a given time, and has not been tampered with since.”

---

## ✨ Key Features

* **Delightfully Small Core:** Minimal Python package under `iahash/core/` handles:
    * Pair model, hashing, and normalization
    * Ed25519 signing and verification
    * IA-HASH document builder and verifier
* **Provider-Agnostic:** The core works with human-written text, files (v2.1+), AI outputs, or any system that can produce bytes.
* **Clear JSON Document Format:** IA-HASH documents are simple JSON: easy to store, share, diff, and audit.
* **Minimal API & UI:** A tiny FastAPI backend and a clean, single-page web UI simplify interaction.
* **Legacy Preserved:** All v1.x code (prompts, sequences, LLM extractors, etc.) lives in `legacy/` for historical reference.

---

## 📄 Example IA-HASH Document (v2.0, simplified)

```json
{
  "protocol_version": "IAHASH-2.0",
  "issuer_id": "iahash.com",
  "timestamp": "2025-12-08T20:00:00Z",

  "par1_hash": "a1f5…",
  "par2_hash": "b7c9…",
  "pair_hash": "d3e4…",

  "signature": "f1a2…",
  "metadata": {
    "label": "contract + company",
    "notes": "Optional metadata goes here"
  }
}
````

> **Note:** The IA-HASH document contains the cryptographic proof. You keep **PAR 1** and **PAR 2** privately. Anyone with the document and the original Pair can verify: (1) that neither element has changed, and (2) that the issuer actually signed this Pair.

-----

## 🚀 Quick Start

### Run with Docker

```bash
# From the repository root
docker build -t iahash:v2 .
docker run --rm -p 8000:8000 iahash:v2
```

The application will be available at:

  * `http://localhost:8000` (Web UI)
  * `http://localhost:8000/docs` (FastAPI documentation)

### Run Locally (Python)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Keys must be set for signing
export IAHASH_PRIVATE_KEY_PATH=keys/issuer_private.key
export IAHASH_PUBLIC_KEY_PATH=keys/issuer_public.key

uvicorn api.main:app --reload
```

> **Note:** Keys/ issuer\_private.key and keys/ issuer\_public.key must be present or generated before running the application.

-----

## 🛠 Basic API Usage

### 1\. Issue a Pair

`POST /api/issue/pair`

```json
{
  "par1": "This is element A (e.g., the Prompt)",
  "par2": "This is element B (e.g., the Response)",
  "metadata": {
    "label": "example",
    "notes": "Optional free-form metadata"
  }
}
```

### 2\. Verify a Document

`POST /api/verify`

```json
{
  "iah_document": { "...": "IA-HASH JSON document" },
  "par1": "This is element A (original)",
  "par2": "This is element B (original)"
}
```

**Response Status:** `status: "VALID"` or `status: "INVALID"`, with detailed errors if validation fails (hash mismatch, signature error, etc.).

-----

## 🌲 Project Structure (v2.0)

```
iahash/
  ├── core/          # 🥇 Protocol, hashing, signing, verification (The kernel)
  ├── adapters/      # Future integrations (LLMs, files, URLs…)
  ├── storage/       # Optional DB helpers
├── api/
  └── main.py        # FastAPI app (Minimal interface)
├── web/
  ├── templates/     # Single-page UI templates
  └── static/
├── legacy/          # 🕰️ All v1.x code is preserved here (for reference)
  └── api_v1/, iahash_v1/, web_v1/, db_v1/ ...
├── docs/
  └── PROTOCOL_2.0.md, ARCHITECTURE_2.0.md, ROADMAP_v2.md, VISION.md
```

-----

## 🗺 Roadmap (Short Version)

| Status | Version | Focus |
| :---: | :---: | :--- |
| ✅ | **v2.0** | Text Pairs, minimal API & UI, clean core (Current release) |
| ⏳ | **v2.1** | File-based Pairs (binary hashing, upload interface) |
| ⏳ | **v2.2** | LLM Authenticity (via provider backend APIs, if access is granted) |
| ⏳ | **v3.0** | Identity Layer (user keypairs, dual signatures, public registries) |
| ⏳ | **v3.x** | SDKs & CLI tools (`iahctl`) |

Full details: [docs/ROADMAP\_v2.md](https://www.google.com/search?q=docs/ROADMAP_v2.md).

-----

## ⚙ Contributing

Contributions are welcome\! ✨

1.  Open an issue to discuss ideas or problems.
2.  Send a pull request targeting the `v2` branch.
3.  Keep code small, clear, and well documented.
4.  Follow the spirit of the project: **simple, transparent, auditable.**

-----

## © License

IA-HASH is released under the **Apache 2**.

See `LICENSE` for details.

```
