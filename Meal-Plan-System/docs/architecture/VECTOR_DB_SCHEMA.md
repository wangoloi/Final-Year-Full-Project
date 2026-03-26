# Vector Database Schema (FAISS)

## Embedding Model

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension**: 384
- **Similarity**: Cosine (IndexFlatIP with normalized vectors)

## Namespace Structure

| Namespace | Purpose | Metadata Fields |
|-----------|---------|-----------------|
| `foods` | Food item embeddings | food_id, category, glycemic_category, tags, nutritional_summary |
| `knowledge_base` | Diabetes knowledge chunks | doc_id, chunk_index, source, topic |
| `user_preferences` | User preference vectors | user_id, preference_type, updated_at |

## Metadata Structure

### Foods Namespace

```json
{
  "food_id": "uuid",
  "category": "string",
  "glycemic_category": "low|medium|high",
  "tags": ["tag1", "tag2"],
  "nutritional_summary": "calories: X, protein: Y, carbs: Z, GI: N"
}
```

### Knowledge Base Namespace

```json
{
  "doc_id": "string",
  "chunk_index": 0,
  "source": "string",
  "topic": "string"
}
```

### User Preferences Namespace

```json
{
  "user_id": "uuid",
  "preference_type": "dietary|cuisine|allergy",
  "updated_at": "timestamp"
}
```

## Index Configuration

- **Index Type**: FAISS IndexFlatIP (Inner Product = Cosine when vectors normalized)
- **Persistence**: `data/faiss/foods.index`, `data/faiss/knowledge.index`
- **Backup**: Versioned snapshots in `data/faiss/backups/`

## Glycemic Category Mapping

| GI Range | Category |
|----------|----------|
| 0-55 | low |
| 56-69 | medium |
| 70-100 | high |
