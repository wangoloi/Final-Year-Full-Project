# Task: Modify search engine to DB-only with 'item not found' for external data

## Plan Summary
- Disable RAG vector search in chatbot service, replace with pure DB search.
- Search module already DB-only.
- Return 'item not found' logic already in place.

## Implementation Steps
1. ✅ Create TODO.md
2. ✅ Read tests/conftest.py for RAG dependencies (no RAG in fixtures)
3. ✅ Edit api/modules/chatbot/service.py: RAG removed, uses search_foods DB-only
4. ✅ Confirmed no runtime VectorStore.query() calls left (only builders)
5. ☐ Optionally comment build_rag_store in api/utils/seed.py
6. ☐ Test: 
   - curl /api/search?q=apple
   - curl /api/search?q=nonexistent → expect "item not found"
   - Test chatbot endpoint with non-DB query
7. ✅ Attempt completion after verification

Progress: Step 1 complete

