# Glocusense — Project Explanation Guide

> **Note:** Later sections mix **historical Flask** wording with concepts that still apply. The **implemented** web API is **FastAPI** in **`backend/`** (see [../ARCHITECTURE.md](../ARCHITECTURE.md)).

A comprehensive guide to explain your diabetes-focused meal planning application to developers, stakeholders, investors, and non-technical audiences.

---

## STEP 1 — System Understanding

### The Problem the System Solves

People with diabetes (Type 1, Type 2, Gestational, Prediabetes) struggle to:
- Find foods that won’t spike their blood sugar
- Understand how carbohydrates, glycemic index (GI), and fiber affect glucose
- Get personalized meal suggestions based on their health profile
- Track blood glucose and relate it to meals
- Ask quick nutrition questions without reading long articles

### Target Users

- **Primary:** People with diabetes or prediabetes who want to manage their diet
- **Secondary:** Caregivers, family members, or health workers supporting someone with diabetes
- **Geographic focus:** Uganda (local foods like matooke, posho, cassava) with potential for broader use

### Main Objectives

1. Provide diabetes-friendly food search and recommendations
2. Offer an AI chatbot for nutrition and glucose-related questions
3. Enable blood glucose tracking (before/after meals)
4. Deliver personalized meal plans and low-GI food suggestions

### Key Features

| Feature | Description |
|--------|-------------|
| **User Auth** | Register, login, multi-step onboarding with diabetes info |
| **Food Search** | Hybrid search: exact, fuzzy, semantic, nutrition similarity |
| **AI Chatbot** | RAG-based nutrition assistant (rule-based responses) |
| **Diabetes Tracking** | Record blood glucose (before/after breakfast, before lunch) |
| **Recommendations** | Low-GI, diabetes-friendly foods and meal plans |
| **Meal Logging** | Log meals with foods and macros (API) |
| **REST API** | JWT-protected API for the web app and future integrations |

### Technologies Used

| Category | Technology |
|----------|-------------|
| **Backend** | Python 3.10+, Flask 3.x |
| **Database** | SQLite (default), PostgreSQL via `DATABASE_URL` |
| **ORM** | Flask-SQLAlchemy, Flask-Migrate |
| **Auth** | Flask-Login (web), PyJWT (API), bcrypt |
| **Vector DB** | ChromaDB (optional), in-memory fallback |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2), TF-IDF fallback |
| **Search** | rapidfuzz (fuzzy), ChromaDB (semantic), scikit-learn |
| **Frontend** | React (new) or Jinja2 templates (legacy), Font Awesome |
| **Server** | Waitress (production), Flask dev server |

### Overall Architecture

**New (React + Node.js microservices):** See [ARCHITECTURE.md](ARCHITECTURE.md).

**Legacy (Flask + Jinja2):**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Jinja2 + Vanilla JS)                        │
│  Landing, Dashboard, Chatbot, Diabetes Tracking, Search, Recommendations │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FLASK ROUTES (Blueprints)                             │
│  auth, main, diabetes, search, recommendations, chatbot, goals, api     │
│  + api_v1_controller (JWT-protected REST API)                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│    SERVICES       │    │   REPOSITORIES    │    │   RAG PIPELINE    │
│ AdvancedSearch    │    │ User, Food, Meal  │    │ EmbeddingService  │
│ Recommendation    │    │ Glucose, Goal     │    │ VectorStore       │
│ RAGChatbot        │    │                   │    │ Retriever         │
│ NutritionSimilarity│   │                   │    │ ResponseGenerator │
└──────────────────┘    └──────────────────┘    └──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              SQLite/PostgreSQL + ChromaDB (vector store)                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Three Levels of Explanation

#### 1. One-Sentence Explanation

**Glocusense is a diabetes-focused meal planning app that helps users find low-GI foods, track blood glucose, and get nutrition advice through an AI chatbot.**

---

#### 2. 30-Second Explanation

Glocusense is a web app for people with diabetes. Users register with their diabetes type and targets, then can search for diabetes-friendly foods (including Ugandan staples like matooke and posho), chat with an AI assistant about nutrition and blood sugar, track their glucose readings, and get personalized meal recommendations. The system uses a hybrid search (exact, fuzzy, and semantic) and a RAG-based chatbot that answers from a curated nutrition knowledge base.

---

#### 3. 2-Minute Explanation

Glocusense is a diabetes management platform built around meal planning and nutrition. It targets people with Type 1, Type 2, Gestational, or Prediabetes.

**User flow:** After registration and onboarding (diabetes type, targets), users land on a dashboard where they can search foods, use the chatbot, record blood glucose, and get recommendations.

**Food search** uses several strategies: exact match, fuzzy match for typos, keyword search, semantic search (e.g. “low sugar fruit” → apple, berries), and nutrition similarity (e.g. foods similar to a reference food). Results are ranked by relevance.

**AI chatbot** uses RAG (Retrieval Augmented Generation): it embeds the user’s question, retrieves relevant nutrition content from a vector store, and generates structured answers (Insight → Explanation → Recommendation). It’s rule-based today, with hooks for future LLM integration.

**Recommendations** are based on low glycemic index (GI ≤ 55), diabetes-friendly foods from the database and meal plan datasets.

**Data:** Food data comes from Uganda nutrition datasets and diabetic meal plans. Blood glucose and meal logs are stored per user for tracking and future analytics.

---

## STEP 2 — System Architecture Breakdown

### Sequential Workflow: From User Action to Output

#### Flow 1: User Searches for Food

```
1. User types "matooke" in search box (dashboard or search page)
2. Frontend: JS sends GET /search?q=matooke (or POST with query)
3. Backend: search_bp route receives request
4. AdvancedSearchEngine.search() runs:
   a. Exact match: FoodItem.name or local_name = "matooke" → high score
   b. Fuzzy match: rapidfuzz for typos (e.g. "matoke")
   c. Keyword match: ILIKE %matooke% in name, description, category
   d. Semantic search: EmbeddingService embeds query → VectorStore.query() → similar docs
   e. Nutrition similarity: If a match exists, find foods with similar macros
5. Results are deduplicated, ranked by score, limited to 20
6. Response: HTML (search/results.html) or JSON (API)
7. Frontend: Renders food cards with name, calories, GI, diabetes_friendly
```

#### Flow 2: User Asks Chatbot a Question

```
1. User types "What is the GI of matooke?" in chat
2. Frontend: POST /api/chatbot/message { message: "..." }
3. Backend: chatbot_bp or api_v1_controller receives request
4. RAGChatbotService.respond():
   a. Save user message to ChatMessage table
   b. Retriever.retrieve(query, top_k=5): embed query → VectorStore.query() → top 5 docs
   c. ContextBuilder.build(retrieved): format docs into context string
   d. ResponseGenerator.generate(query, context): rule-based logic
      - Match keywords (carb, glucose, GI, matooke, breakfast, etc.)
      - Return structured response: Insight → Explanation → Recommendation
      - Inject retrieved context when relevant
   e. Save assistant reply to ChatMessage
5. Response: JSON { reply: "..." }
6. Frontend: Appends assistant message to chat UI
```

#### Flow 3: User Records Blood Glucose

```
1. User fills form: before_breakfast, after_breakfast, before_lunch, meal_description
2. Frontend: POST /diabetes/record
3. Backend: diabetes_bp creates DiabetesRecord
4. DiabetesRecord saved to SQLite with user_id, readings, record_date
5. Redirect to /diabetes/progress or /diabetes/dashboard
6. Frontend: Shows history and charts (if implemented)
```

#### Flow 4: User Gets Recommendations

```
1. User clicks "Get Food Recommendations" or visits /recommendations/generate
2. Frontend: POST /recommendations/generate (or GET)
3. Backend: RecommendationService.get_recommendations(user, limit=12, max_gi=55)
4. FoodRepository.list_(category=None, max_gi=55) → diabetes-friendly foods
5. Order: diabetes_friendly first, then others; limit to 12
6. Optionally: get_meal_plans_from_dataset() from diabetic_diet_meal_plans CSV
7. Response: Rendered list or JSON
8. Frontend: Displays food cards or meal plan table
```

#### Flow 5: App Startup (Data Initialization)

```
1. run.py → create_app()
2. First request triggers before_request: _ensure_data_initialized()
3. initialize_default_data(): load uganda_food_nutrition_dataset CSV → FoodItem
4. build_rag_knowledge_base(): FoodItem + nutrition facts → EmbeddingService.embed_documents()
   → VectorStore.add() (ChromaDB or in-memory)
5. Subsequent requests use pre-built food DB and vector store
```

---

## STEP 3 — Component Explanation

### 1. Frontend (Templates + Static)

**What it does:** Renders pages (landing, dashboard, chat, diabetes, search, recommendations) and handles user interactions.

**Why it exists:** Provides the user interface for the app.

**Connections:** Calls backend routes via form submissions and fetch/XHR. Uses Jinja2 for server-rendered HTML and vanilla JS for modals, chat, and search.

**Technologies:** Jinja2, HTML5, CSS3, JavaScript, Font Awesome.

---

### 2. Flask Routes (Blueprints)

**What it does:** Maps URLs to view functions, handles request/response, and delegates to services.

**Why it exists:** Separates HTTP handling from business logic.

**Connections:** Receives requests from frontend, calls services/repositories, returns HTML or JSON.

**Technologies:** Flask, Flask-Login, Flask-WTF.

---

### 3. AdvancedSearchEngine

**What it does:** Runs a multi-strategy search pipeline (exact → fuzzy → keyword → semantic → nutrition similarity).

**Why it exists:** Users search in different ways (exact names, typos, concepts like “low sugar fruit”). A single strategy would miss many relevant results.

**Connections:** Uses FoodItem (DB), EmbeddingService, VectorStore, NutritionSimilarityEngine. Called by search routes and home.

**Technologies:** SQLAlchemy, rapidfuzz, ChromaDB, sentence-transformers.

---

### 4. RAG Pipeline (EmbeddingService, VectorStore, Retriever, ContextBuilder, ResponseGenerator)

**What it does:**
- **EmbeddingService:** Converts text to vectors (sentence-transformers or TF-IDF).
- **VectorStore:** Stores and queries document embeddings (ChromaDB or in-memory).
- **Retriever:** Embeds query, fetches top-k similar documents.
- **ContextBuilder:** Formats retrieved docs for the generator.
- **ResponseGenerator:** Produces rule-based answers using context and keyword logic.

**Why it exists:** RAG grounds answers in a nutrition knowledge base instead of generic text. Rule-based generation avoids LLM costs and keeps responses predictable.

**Connections:** RAGChatbotService orchestrates the pipeline. Data comes from FoodItem and nutrition datasets.

**Technologies:** sentence-transformers, ChromaDB, scikit-learn (TF-IDF).

---

### 5. RecommendationService

**What it does:** Returns low-GI, diabetes-friendly foods and meal plans from the database and CSV datasets.

**Why it exists:** Users need quick, personalized suggestions without browsing the full catalog.

**Connections:** Uses FoodRepository, User. Called by recommendations routes and API v1.

**Technologies:** Python, CSV, SQLAlchemy.

---

### 6. Repositories (User, Food, Meal, Glucose, Goal)

**What it does:** Encapsulates database access for each entity (CRUD).

**Why it exists:** Keeps business logic independent of storage details and simplifies testing.

**Connections:** Used by services and API controller. Implement data access for models.

**Technologies:** SQLAlchemy, Flask-SQLAlchemy.

---

### 7. API v1 Controller

**What it does:** Exposes REST endpoints (auth, foods, meals, glucose, goals, recommendations, chatbot) with JWT authentication.

**Why it exists:** Powers the React web client and allows integrations or programmatic access.

**Connections:** Uses container (DI) for services/repositories. Protected by `@token_required`.

**Technologies:** Flask, PyJWT.

---

### 8. Data Initializer

**What it does:** Loads food data from CSV into FoodItem and builds the RAG vector store on first request.

**Why it exists:** Ensures the app has food data and embeddings without manual setup.

**Connections:** Runs in `before_request`. Writes to FoodItem and VectorStore.

**Technologies:** CSV, pandas (optional), SQLAlchemy.

---

## STEP 4 — Technical Concepts Simplification

### Concept 1: RAG (Retrieval Augmented Generation)

| Audience | Explanation |
|----------|-------------|
| **Developer** | RAG embeds the user query and documents, retrieves the top-k most similar documents from a vector store, and uses them as context for generation. This reduces hallucination and grounds answers in your data. |
| **Stakeholder** | The chatbot doesn’t invent answers. It first looks up relevant nutrition facts in our database, then answers using that information. |
| **Simple** | Like a librarian: you ask a question, they find the right books, then answer using what’s in those books. |

---

### Concept 2: Embeddings / Vector Search

| Audience | Explanation |
|----------|-------------|
| **Developer** | Text is converted to dense vectors (e.g. 384-dim) via sentence-transformers. Similarity is computed with cosine similarity. ChromaDB stores vectors and supports approximate nearest-neighbor search. |
| **Stakeholder** | We turn words into numbers so the system can find similar meanings. “Low sugar fruit” and “apple” end up close in this number space. |
| **Simple** | Like a map: similar ideas are placed close together. When you ask “low sugar fruit,” the system finds the ideas nearest to that on the map. |

---

### Concept 3: Glycemic Index (GI)

| Audience | Explanation |
|----------|-------------|
| **Developer** | GI measures how quickly 50g of carbs from a food raises blood glucose vs. pure glucose (100). Low ≤55, medium 56–69, high ≥70. Used for ranking and filtering. |
| **Stakeholder** | GI tells us how fast a food raises blood sugar. Low-GI foods are preferred for diabetes management. |
| **Simple** | A speedometer for blood sugar: low GI = slow rise, high GI = fast spike. |

---

### Concept 4: Hybrid Search

| Audience | Explanation |
|----------|-------------|
| **Developer** | Combines exact match, fuzzy (Levenshtein), keyword (ILIKE), semantic (embedding similarity), and nutrition similarity. Results are merged, deduplicated, and ranked by a combined score. |
| **Stakeholder** | We use several search methods at once so users get results whether they type exactly, make typos, or describe what they want in words. |
| **Simple** | Like searching with multiple tools: spell-check, keyword search, and “find similar” all work together. |

---

## STEP 5 — Results and Output Interpretation

### 1. Search Results (FoodItem list)

| Metric | Meaning | Good vs Bad | Decision |
|--------|---------|-------------|----------|
| **Number of results** | How many foods matched | More relevant results = good | If zero, broaden query or check data |
| **Relevance order** | Exact > fuzzy > keyword > semantic | Top results match intent = good | Adjust scoring or add synonyms |
| **diabetes_friendly** | Flag on each food | True for diabetes users = good | Filter or highlight in UI |

---

### 2. Chatbot Response

| Metric | Meaning | Good vs Bad | Decision |
|--------|---------|-------------|----------|
| **Context used** | Retrieved docs injected into reply | Context present and relevant = good | Improve retrieval or knowledge base |
| **Structure** | Insight → Explanation → Recommendation | Clear structure = good | Refine ResponseGenerator rules |
| **Accuracy** | Facts match database | Correct GI, macros = good | Validate data and rules |

---

### 3. Blood Glucose Readings

| Metric | Meaning | Good vs Bad | Decision |
|--------|---------|-------------|----------|
| **before_breakfast** | Fasting glucose (mg/dL) | 70–100 typical target | Flag if outside range |
| **after_breakfast** | Post-meal spike | <180 (1–2 hr) typical | Correlate with meal choices |
| **before_lunch** | Pre-lunch reading | Stable = good | Track trends over time |

---

### 4. Recommendations

| Metric | Meaning | Good vs Bad | Decision |
|--------|---------|-------------|----------|
| **max_gi** | Upper GI filter (default 55) | Lower = stricter | Adjust per user |
| **diabetes_friendly count** | How many recommended foods are diabetes-friendly | Higher = better | Prioritize in ordering |
| **Meal plan match** | Match to user group (e.g. Diabetic_NotActive) | Correct group = good | Map user profile to group |

---

## STEP 6 — Step-by-Step Guided Pitch

### 1. Hook

> “What if people with diabetes could ask ‘What can I eat?’ and get instant, personalized answers—without reading long articles or guessing?”

---

### 2. Problem Statement

> “Over 500 million people live with diabetes. Managing blood sugar through diet is hard: they need to know which foods are safe, understand glycemic index, and track how meals affect their glucose. Most tools are either too generic or too complex.”

---

### 3. Current Challenges

> “Existing solutions often offer generic meal plans, require manual tracking in spreadsheets, or lack local foods. In Uganda, staples like matooke and posho aren’t in many international apps. People also want quick answers—‘Is banana okay?’—without digging through articles.”

---

### 4. Proposed Solution

> “Glocusense is a diabetes-focused meal planning app that combines smart food search, an AI nutrition assistant, blood glucose tracking, and personalized recommendations—with support for local Ugandan foods.”

---

### 5. How the System Works

> “Users register with their diabetes type and targets. They can search our food database with flexible search—exact names, typos, or concepts like ‘low sugar fruit.’ Our AI chatbot answers nutrition questions using a curated knowledge base. They can log blood glucose and get low-GI meal recommendations tailored to their profile.”

---

### 6. Key Technologies

> “We use Flask for the backend, a hybrid search engine (exact, fuzzy, semantic), and a RAG-based chatbot that retrieves relevant nutrition facts before answering. Food data comes from Uganda nutrition datasets. We ship a web UI backed by this REST API.”

---

### 7. System Workflow

> “From search to answer: the user types a query, our engine tries exact match, fuzzy match for typos, keyword search, and semantic search. For the chatbot, we embed the question, find similar documents in our vector store, and generate a structured answer. Recommendations are filtered by low GI and diabetes-friendly foods.”

---

### 8. Results and Impact

> “Users get fast, relevant food results, clear nutrition answers, and recommendations that respect their diabetes profile. Blood glucose tracking helps them see patterns. The system is designed to scale with more foods and optional LLM integration.”

---

### 9. Real-World Benefits

> “For users: less guesswork, support for local foods, and a single place for search, chat, tracking, and recommendations. For health workers: a tool to recommend to patients. For partners: an API to integrate into existing systems.”

---

### 10. Future Improvements

> “We plan to add LLM integration for more natural chatbot responses, glucose trend analytics, meal–glucose correlation, API integrations, and expansion to more regional food databases.”

---

## STEP 7 — Audience Adaptation

### 1. Developer Explanation

Glocusense is a Flask app with a service-oriented backend. The stack includes SQLAlchemy (SQLite/PostgreSQL), ChromaDB for vector search, and sentence-transformers (all-MiniLM-L6-v2) for embeddings. The RAG pipeline uses EmbeddingService → VectorStore → Retriever → ContextBuilder → ResponseGenerator; the generator is rule-based with keyword matching, ready for LLM integration. Search uses a multi-strategy pipeline: exact, rapidfuzz fuzzy, keyword ILIKE, semantic (embedding similarity), and nutrition similarity (cosine on macro vectors). Repositories abstract data access; the API v1 controller uses JWT and a DI container. Data initialization loads CSV into FoodItem and builds the vector store on first request.

---

### 2. Stakeholder Explanation

Glocusense helps people with diabetes manage their diet. Users search for diabetes-friendly foods (including Ugandan staples), ask nutrition questions to an AI chatbot, track blood glucose, and get personalized meal recommendations. The system uses smart search (handles typos and natural language) and a chatbot that answers from a nutrition knowledge base. We focus on low-GI foods and local data. The product is a web app; the same API can support partner integrations.

---

### 3. Friend / Non-Technical Explanation

Imagine an app that helps someone with diabetes figure out what to eat. They can search for foods (even with typos), ask things like “Is matooke okay for me?” and get clear answers. They can log their blood sugar and get meal suggestions that won’t spike it. The app “reads” our food database and nutrition info to give answers—like a nutritionist that’s always available. It’s built especially with Ugandan foods in mind.

---

## STEP 8 — Visual Explanation Guidance

### 1. System Architecture Diagram

**Purpose:** Show main components and data flow.

**Content:**
- **Top:** User (browser)
- **Middle:** Flask app (routes, services, RAG pipeline)
- **Bottom:** SQLite, ChromaDB, CSV datasets
- **Arrows:** Request → Route → Service → DB; Response back to user
- **Callouts:** Auth (JWT/session), RAG (Embed → Retrieve → Generate), Search (5 strategies)

---

### 2. Data Flow Diagram

**Purpose:** Show how data moves for a single user action.

**Content:**
- **Swimlanes:** User, Frontend, Backend, Database
- **Sequence:** User types → Frontend sends → Route receives → Service processes → Repository queries → Response returned → UI updates
- **Example flow:** Chat message → RAG pipeline → VectorStore + ResponseGenerator → Reply

---

### 3. RAG Pipeline Diagram

**Purpose:** Explain how the chatbot produces answers.

**Content:**
- **Steps:** User Query → Embedding → Vector Search → Top-K Docs → Context Builder → Response Generator → Reply
- **Components:** EmbeddingService, VectorStore, Retriever, ContextBuilder, ResponseGenerator
- **Data:** Query text → 384-dim vector → Similar docs → Formatted context → Rule-based + context → Final text

---

### 4. User Interaction Flow

**Purpose:** Show user journeys.

**Content:**
- **Flow 1:** Register → Onboarding → Dashboard → Search / Chat / Track / Recommendations
- **Flow 2:** Search: type query → see results → click food → view details
- **Flow 3:** Chat: type question → get reply → follow-up
- **Flow 4:** Diabetes: fill form → submit → view history

---

## STEP 9 — Q&A Preparation

### From Developers

**Q: Why rule-based response generation instead of an LLM?**  
A: To avoid API costs, latency, and hallucination for a first version. The structure (Insight, Explanation, Recommendation) is consistent, and we can plug in an LLM later while keeping the same RAG retrieval.

**Q: How do you handle ChromaDB failures?**  
A: We fall back to an in-memory vector store. Embeddings can also fall back to TF-IDF if sentence-transformers isn’t available.

**Q: What’s the embedding model and dimension?**  
A: all-MiniLM-L6-v2, 384 dimensions. TF-IDF is truncated to 384 for compatibility.

**Q: How is the search pipeline ordered?**  
A: Exact (1.0) > Fuzzy (0.7–0.9) > Keyword (0.6) > Semantic (0.65) > Nutrition similarity (0.5–0.6). Results are merged, deduplicated, and sorted by score.

---

### From Stakeholders

**Q: How is this different from other diabetes apps?**  
A: We combine search, AI chat, tracking, and recommendations in one place, with a focus on Ugandan foods and local datasets. The chatbot answers from our own nutrition knowledge base.

**Q: Can it integrate with hospitals or clinics?**  
A: Yes. The REST API supports integration. We’d need to define data sharing and privacy policies for each partner.

**Q: What’s the business model?**  
A: That’s for product/business to define. Possible options: freemium, B2B licensing, or partnerships with health providers.

---

### From Investors

**Q: What’s the scalability plan?**  
A: The backend is stateless; we can scale with more Flask workers. The database can move to PostgreSQL. ChromaDB can be replaced with a scalable vector DB (e.g. Pinecone, Weaviate). The API supports third-party integrations.

**Q: What’s the data moat?**  
A: Uganda food nutrition data, diabetic meal plans, and user interaction data (search, chat, glucose) that can improve personalization and analytics.

**Q: What are the main technical risks?**  
A: Embedding model size and cost, vector store scalability, and data quality in CSV sources. We mitigate with fallbacks and incremental improvements.

---

### From Curious Friends

**Q: Can I use it if I don’t have diabetes?**  
A: Yes, for general nutrition and low-GI eating, but it’s optimized for people with diabetes.

**Q: Does it work offline?**  
A: The web app needs internet. A future PWA or native client could add offline caching separately.

**Q: Is the chatbot a real AI?**  
A: It uses AI for understanding and finding similar questions, but the answers are generated by rules we wrote, using our nutrition database. So it’s “smart search + structured answers,” not a general-purpose chatbot.

---

## STEP 10 — Final Speaking Script

### Structured Script for Presentation (3–5 minutes)

---

**[Opening – 15 sec]**

> “I’m going to walk you through Glocusense—a diabetes-focused meal planning app that helps people find safe foods, get nutrition advice, and track their blood sugar.”

---

**[Problem – 30 sec]**

> “Managing diabetes through diet is hard. People need to know which foods raise blood sugar, understand terms like glycemic index, and track how meals affect them. Many tools are generic or don’t include local foods like matooke or posho. And when someone asks ‘Can I eat banana?,’ they often have to search through long articles. We built Glocusense to solve that.”

---

**[Solution – 30 sec]**

> “Glocusense is a web app where users register with their diabetes type and targets. They can search our food database—with support for typos and natural language—chat with an AI assistant about nutrition, log blood glucose, and get personalized meal recommendations. We focus on low-GI, diabetes-friendly foods and use Ugandan nutrition data.”

---

**[How It Works – 60 sec]**

> “Here’s how it works. For search, we use several strategies: exact match, fuzzy match for typos, keyword search, and semantic search—so ‘low sugar fruit’ can return apple and berries. We also find nutritionally similar foods.
>
> For the chatbot, we use a technique called RAG. When you ask a question, we first search our nutrition knowledge base for relevant facts, then generate an answer from that. So the answers are grounded in our data, not made up.
>
> Recommendations are filtered by low glycemic index and diabetes-friendly foods. Blood glucose tracking stores readings so users can see patterns over time.”

---

**[Tech Snapshot – 20 sec]**

> “On the technical side: Flask backend, SQLite database, and a vector database for semantic search. We use sentence-transformers for embeddings and a rule-based response generator. There’s a REST API consumed by the web frontend.”

---

**[Impact & Next Steps – 25 sec]**

> “The result: users get faster, more relevant food search, clear nutrition answers, and recommendations tailored to their profile. We’re exploring LLM integration for more natural chat and glucose analytics. That’s Glocusense in a nutshell. I’m happy to take questions.”

---

**[Transition to Q&A]**

> “Any questions about the system, the technology, or how it could be used?”

---

*End of Project Explanation Guide*
