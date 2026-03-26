# Nutrition Chatbot Architecture

## Overview

The Glocusense AI Nutrition Chatbot is a **context-aware reasoning assistant** that helps users understand how nutrition affects blood glucose and diabetes management. It uses retrieval-augmented reasoning, intent classification, and conversation memory.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER MESSAGE                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONVERSATION MEMORY (last N messages)                     │
│  Retrieves recent assistant reply for follow-up context                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTENT CLASSIFIER                                      │
│  specific_food | meal_suggestion | alternatives | stability_foods |          │
│  general_nutrition | follow_up | greeting                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NUTRITION RETRIEVER                                       │
│  • Semantic search (vector store)                                             │
│  • Nutrition-filtered DB (low GI, high fiber)                                 │
│  • Keyword search (specific food names)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NUTRITION REASONING ENGINE                                │
│  • Assess glucose impact (low/moderate/high)                                  │
│  • Apply rules: carbs, fiber, GI → blood sugar                                 │
│  • Suggest alternatives                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RESPONSE GENERATOR                                       │
│  Structured output: Answer → Nutrition Insight → Blood Sugar Impact → Rec    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Intent Classifier (`app/rag/intent_classifier.py`)

Interprets user questions and infers intent:

| Intent | Example Questions |
|--------|-------------------|
| `specific_food` | "Is matooke good for diabetes?", "What is the GI of beans?" |
| `meal_suggestion` | "What's a good breakfast?", "What can I eat for lunch?" |
| `alternatives` | "What can I eat instead of rice?", "Lower GI alternatives?" |
| `stability_foods` | "Which foods keep blood sugar stable?", "Good for diabetes?" |
| `general_nutrition` | "How do carbs affect blood sugar?", "What is glycemic index?" |
| `follow_up` | "Should a diabetic eat it?", "Can I have it?" (uses context) |
| `greeting` | "Hello", "Hi" |

### 2. Nutrition Retriever (`app/rag/nutrition_retriever.py`)

- **Semantic search**: Embeds query, retrieves similar food documents from vector store
- **Nutrition-filtered**: For stability/meal intents, queries DB for low-GI (≤55), high-fiber, diabetes-friendly foods
- **Keyword search**: For specific food queries, searches name, local_name, description

### 3. Nutrition Reasoning Engine (`app/rag/nutrition_reasoning_engine.py`)

**Rules:**
- Blood glucose **rises** when: high carbs, high GI, low fiber
- Blood glucose **stabilizes** when: high fiber, moderate protein, low GI
- Balanced meals: complex carbs + protein + fiber-rich vegetables

**Output:** `GlucoseImpact` with level (low/moderate/high), explanation, factors, recommendation

### 4. Response Generator (`app/rag/response_generator.py`)

**Structured format:**
1. **Answer** – Direct, clear response
2. **Nutrition Insight** – Explanation based on carbs, fiber, GI
3. **Blood Sugar Impact** – How the food affects glucose
4. **Recommendation** – Alternatives or meal ideas
5. **Safety disclaimer** – Nutrition guidance only, consult professionals

---

## Example Prompts and Responses

### Example 1: Specific Food

**User:** "Is matooke good for someone with diabetes?"

**Bot:**
> **Answer**
> Yes, Matooke (Steamed Green Banana) can be part of a diabetes-friendly diet when eaten in moderation.
>
> **Nutrition Insight**
> Matooke (Steamed Green Banana) has 31g carbs, 2.6g fiber, and a GI of 45. Matooke has a low glycemic index (45), meaning it raises blood sugar slowly. With 2.6g of fiber, it slows down glucose absorption.
>
> **Blood Sugar Impact**
> Blood sugar impact: low. Factors: low GI (45), moderate fiber (2.6g), high carbs (31g).
>
> **Recommendation**
> Matooke can fit in a balanced diet. Pair with vegetables and protein for better glucose control.
>
> *This is nutrition guidance only, not medical advice...*

---

### Example 2: Stability Foods

**User:** "Which foods keep blood sugar stable?"

**Bot:**
> **Answer**
> Foods with low glycemic index (≤55), high fiber, and moderate protein help keep blood sugar stable.
>
> **Nutrition Insight**
> Blood glucose stabilizes when fiber is high, protein is moderate, and glycemic index is low. Balanced meals include complex carbohydrates (whole grains, legumes), protein sources (beans, fish, eggs), and fiber-rich vegetables.
>
> **Blood Sugar Impact**
> Low-GI foods cause slower, steadier glucose rises. Fiber and protein slow digestion.
>
> **Recommendation**
> Good choices from our database: Beans, Lentils, Avocado, Cabbage, Oatmeal...

---

### Example 3: Follow-up

**User:** "What is the GI of matooke?"

**Bot:** [Provides GI info for matooke]

**User:** "Should a diabetic eat it?"

**Bot:** [Uses context – knows we discussed matooke – answers "Yes, Matooke can fit..."]

---

## Dataset Usage

The chatbot uses `FoodItem` with:
- `food_name`, `local_name`, `category`
- `calories`, `carbohydrates`, `protein`, `fat`, `fiber`, `glycemic_index`
- `description`, `diabetes_friendly`, `serving_size`

The RAG knowledge base embeds each food as:
```
{name} ({local_name}): {category}. Calories: X, Carbs: Xg, Protein: Xg, Fiber: Xg, GI: X. {description} Diabetes-friendly: X.
```

---

## Optional Enhancements

1. **Explainable AI**: Add a "reasoning trace" showing which rules were applied
2. **LLM integration**: Replace rule-based generator with LLM (OpenAI, etc.) using same retrieval + reasoning as context
3. **Personalization**: Use user's diabetes type, targets, and history to tailor responses
4. **Confidence scores**: Return confidence with each response for uncertain cases
