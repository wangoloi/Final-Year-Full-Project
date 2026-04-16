# GlucoSense — UI Architecture Diagrams (Mermaid)

Use these in **Slide 8** (Design) or as appendix figures. Render in [Mermaid Live Editor](https://mermaid.live), VS Code Mermaid preview, or export to PNG/SVG for PowerPoint.

**What these reflect (current system):**
- **GlucoSense (Clinical)**: React (Vite dev typically **:5173**) → FastAPI API **:8000** → SQLite + inference bundle.
- **Meal Plan (Nutrition)**: React (Vite dev **:5175**) → FastAPI API **:8001** → SQLite + background seed + Chroma RAG (+ optional Typesense).
- **Integration**: GlucoSense embeds Meal Plan UI in an **iframe** and performs **SSO via JWT handoff**:
  1) GlucoSense calls Meal API `POST /api/auth/integration/glucosense` with `X-Glucosense-Embed-Key`
  2) Receives a Meal Plan JWT
  3) Sends JWT into the iframe using `window.postMessage({ type: 'GLUCOSENSE_MEAL_PLAN_TOKEN', token })`

**Tip:** If a viewer does not support `classDef` styling, diagrams still render with default colors.

---

## 1. Big picture: integrated runtime topology (dev)

```mermaid
flowchart TB
  subgraph Browser["🌐 Browser (single user session)"]
    direction TB
    GSUI["<b>GlucoSense UI</b><br/>React · Vite<br/>dev: :5173"]
    IFRAME["<b>Embedded Meal Plan</b><br/>iframe to :5175/?embed=glucosense"]
    MPUI["<b>Meal Plan UI</b><br/>React · Vite<br/>dev: :5175"]
  end

  subgraph GS["🔷 GlucoSense Clinical API · :8000"]
    API_GS["FastAPI · CDS routes<br/>/api/*"]
    DB_GS[("SQLite<br/>clinical + audit")]
    BUNDLE["Inference bundle<br/>joblib / pipeline"]
  end

  subgraph MP["🟢 Meal Plan API · :8001"]
    API_MP["FastAPI · auth · search · chatbot · recommendations<br/>/api/*"]
    DB_MP[("SQLite<br/>users · foods · logs")]
    SEED["Startup seed (bg)<br/>CSV foods → DB"]
    RAG["Chroma RAG store (bg)<br/>sentence-transformers embeddings"]
    TYPE["Optional search<br/>Typesense sync"]
  end

  %% GlucoSense calls its own API through Vite proxy (/api → :8000)
  GSUI -->|"/api (Vite proxy)"| API_GS
  API_GS --> DB_GS
  API_GS --> BUNDLE

  %% Meal Plan UI calls its API through Vite proxy (/api → :8001)
  MPUI -->|"/api (Vite proxy)"| API_MP
  API_MP --> DB_MP
  API_MP --> SEED
  API_MP --> RAG
  API_MP -. optional .-> TYPE

  %% Integration in the browser
  GSUI -.->|"<b>iframe</b> embed"| IFRAME
  IFRAME --> MPUI

  %% SSO / JWT handoff path
  GSUI -->|"POST /api/auth/integration/glucosense<br/>X-Glucosense-Embed-Key"| API_MP
  GSUI -.->|"postMessage JWT<br/>(GLUCOSENSE_MEAL_PLAN_TOKEN)"| IFRAME

  classDef browser fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
  classDef gluco fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
  classDef meal fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#e65100
  classDef data fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f
  classDef ops fill:#ede7f6,stroke:#5e35b1,stroke-width:2px,color:#311b92

  class GSUI,IFRAME,MPUI browser
  class API_GS,BUNDLE gluco
  class API_MP meal
  class DB_GS,DB_MP data
  class SEED,RAG,TYPE ops
```

---

## 2. Embed + SSO: GlucoSense → Meal Plan JWT handoff (sequence)

```mermaid
sequenceDiagram
  autonumber
  participant G as GlucoSense UI (:5173)
  participant MAPI as Meal Plan API (:8001)
  participant IF as Meal Plan iframe (:5175)
  participant MF as Meal Plan UI (iframe app)

  Note over G,IF: Meal Plan is loaded as /?embed=glucosense
  G->>MAPI: POST /api/auth/integration/glucosense<br/>Header: X-Glucosense-Embed-Key<br/>Body: email, display_name, role
  MAPI-->>G: 200 { token: JWT, user }

  G-->>IF: postMessage({ type: "GLUCOSENSE_MEAL_PLAN_TOKEN", token })
  IF-->>MF: message event (allowed origin check)
  MF->>MF: store JWT (localStorage) + refresh /me
  Note over MF: Subsequent /api calls send Authorization: Bearer JWT
```

---

## 3. Clinical workflow: assessment → recommendation (sequence)

```mermaid
sequenceDiagram
  autonumber
  participant UI as GlucoSense Dashboard (UI)
  participant API as Clinical API :8000
  participant DB as Clinical SQLite
  participant ML as Inference bundle

  UI->>API: POST /api/... (assessment payload)
  API->>DB: Load patient + validate inputs
  API->>ML: predict dose (regression) + safety rules
  API->>DB: Persist assessment + recommendation + audit
  API-->>UI: Recommendation + rationale + warnings
  Note over UI,API: CDS only — clinician must review
```

---

## 4. Meal Plan: request handling (RAG chatbot + engine)

```mermaid
flowchart LR
  subgraph UI["📥 Meal Plan UI (embedded or standalone)"]
    Q["User intent<br/>search / chat / plan"]
  end

  subgraph API["🟢 Meal Plan API :8001"]
    AUTH["JWT auth<br/>/api/auth/*"]
    CH{"Request type?"}
    S["Search module<br/>SQLite fuzzy (+ optional Typesense)"]
    R["Chatbot module<br/>RAG retrieval (Chroma)"]
    L["LLM configured?<br/>OpenAI / local LLM"]
    A["Answer builder<br/>RAG + LLM"]
    F["Fallback response<br/>rules/templates"]
    E["Recommendations engine<br/>constraints + scoring"]
  end

  subgraph DATA["📦 Data layer"]
    DB[("SQLite foods/users/logs")]
    V[("Chroma vector store")]
  end

  Q --> AUTH --> CH
  CH -->|search| S --> DB
  CH -->|chat| R --> V --> L
  L -->|yes| A
  L -->|no| F
  CH -->|weekly plan| E --> DB
  A --> DB
  F --> DB
```

---

## 5. UI route map (GlucoSense clinician vs patient)

```mermaid
flowchart TB
  subgraph GS["🔷 GlucoSense UI"]
    direction TB
    PUB["Public<br/>Landing / Login"]
    W["Clinician workspace<br/>/workspace/*"]
    D["Dashboard<br/><i>assessment + embed</i>"]
    PT["Patients"]
    TR["Glucose trends"]
    IM["Insulin management"]
    RP["Reports"]
    AL["Alerts"]
    EMB["Meal Plan embed page<br/>/workspace/meal-plan<br/><i>iframe</i>"]
  end

  subgraph MP["🟢 Meal Plan UI"]
    direction TB
    LND["Landing / Auth (standalone)"]
    APP["App shell<br/>/app"]
    CH["Chatbot"]
    SR["Search"]
    GL["Glucose log"]
    WK["Weekly plan"]
    SD["Sensor demo<br/><i>CSV charts</i>"]
  end

  PUB --> W
  W --> D
  W --> PT
  W --> TR
  W --> IM
  W --> RP
  W --> AL
  W --> EMB

  EMB -.->|"iframe + JWT handoff"| APP
  APP --> CH
  APP --> SR
  APP --> GL
  APP --> WK
  APP --> SD
```

---

## 6. Layered stack (single slide summary)

```mermaid
flowchart TB
  subgraph L4["Presentation"]
    UI1["GlucoSense UI<br/>React · Vite"]
    UI2["Meal Plan UI<br/>React · Vite (iframe-capable)"]
  end

  subgraph L3["APIs"]
    CDS["Clinical API<br/>FastAPI :8000"]
    NUT["Meal Plan API<br/>FastAPI :8001"]
  end

  subgraph L2["Intelligence"]
    INS["Insulin inference<br/>bundle + safety"]
    REC["Meal planning engine<br/>constraints + scoring"]
    RAG["RAG retrieval<br/>Chroma + embeddings"]
  end

  subgraph L1["Data"]
    D1[("SQLite clinical + audit")]
    D2[("SQLite meal (users/foods/logs)")]
  end

  UI1 --> CDS --> D1
  CDS --> INS
  UI2 --> NUT --> D2
  NUT --> REC
  NUT --> RAG
```

