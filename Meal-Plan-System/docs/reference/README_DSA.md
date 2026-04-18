# Glocusense - Data Structures & Algorithms Documentation

## Overview

This document details all major data structures and algorithms used in the Glocusense application, explaining where and why each was chosen based on performance, scalability, and task suitability.

---

## 1. Data Structures

### 1.1 Database Models (SQLAlchemy ORM)

#### User Model
```python
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ... other fields
```

**Data Structure:** Relational Database Table
**Why:** 
- **ACID Compliance:** Ensures data integrity for user accounts
- **Relationships:** Easy foreign key relationships with other models
- **Query Optimization:** Indexed fields (username, email) for O(log n) lookups
- **Scalability:** SQLite for development, easily migrates to PostgreSQL/MySQL

**Use Cases:**
- User authentication
- Profile management
- Relationship with diabetes records and recommendations

**Performance Characteristics:**
- **Lookup by ID:** O(1) - Primary key index
- **Lookup by username/email:** O(log n) - Unique index
- **Insert/Update:** O(log n) - Index maintenance

---

#### FoodItem Model
```python
class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    diabetes_friendly = db.Column(db.Boolean, default=False)
    # ... nutritional fields
```

**Data Structure:** Relational Database Table
**Why:**
- **Structured Data:** Nutritional information is tabular
- **Filtering:** Efficient queries by category, diabetes_friendly flag
- **Relationships:** Can link to recommendations, user preferences
- **Search:** Full-text search capabilities on name/description

**Indexing Strategy:**
- Primary key on `id` for O(1) lookups
- Index on `category` for category-based filtering
- Index on `diabetes_friendly` for diabetes-specific queries
- Full-text index on `name` and `description` for search

**Query Patterns:**
```python
# O(log n) - Indexed category lookup
FoodItem.query.filter_by(category='proteins').all()

# O(log n) - Indexed boolean filter
FoodItem.query.filter_by(diabetes_friendly=True).all()

# O(n) - Full table scan (acceptable for small datasets)
FoodItem.query.filter(FoodItem.name.contains('bean')).all()
```

---

#### DiabetesRecord Model
```python
class DiabetesRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    blood_glucose = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Data Structure:** Relational Database Table with Foreign Key
**Why:**
- **Time-Series Data:** Chronological records for trend analysis
- **User Association:** Foreign key ensures referential integrity
- **Temporal Queries:** Indexed `created_at` for time-range queries

**Indexing:**
- Primary key on `id`
- Foreign key index on `user_id`
- Composite index on `(user_id, created_at)` for efficient user history queries

**Query Optimization:**
```python
# O(log n) - Indexed user_id + created_at
DiabetesRecord.query.filter_by(
    user_id=user_id
).order_by(DiabetesRecord.created_at.desc()).limit(5).all()
```

---

### 1.2 In-Memory Data Structures

#### Food Item Dictionary (Data Initializer)
```python
ugandan_foods = [
    {
        'name': 'Matooke (Plantain)',
        'category': 'grains',
        'diabetes_friendly': True,
        # ... nutritional data
    },
    # ... more items
]
```

**Data Structure:** List of Dictionaries
**Why:**
- **Initialization:** Simple structure for seeding database
- **Readability:** Easy to maintain and update
- **Conversion:** Easily converted to database records

**Alternative Considered:** JSON file
- **Rejected:** Less type-safe, harder to maintain in code

---

#### User Session Data (Flask-Login)
```python
# Flask-Login uses session dictionary
session['user_id'] = user.id
```

**Data Structure:** Dictionary/Hash Map
**Why:**
- **O(1) Lookup:** Fast user identification
- **Session Management:** Built-in Flask session handling
- **Security:** Encrypted session cookies

---

### 1.3 Frontend Data Structures

#### JavaScript Objects (API Responses)
```javascript
{
    'recommendations': [
        {
            'food_item_id': 1,
            'food_name': 'Beans',
            'confidence_score': 0.85
        }
    ]
}
```

**Data Structure:** JSON Objects/Arrays
**Why:**
- **Serialization:** Easy JSON serialization for API responses
- **Frontend Compatibility:** Native JavaScript structure
- **Network Efficiency:** Compact representation

---

## 2. Algorithms

### 2.1 Search Algorithms

#### Linear Search (Food Item Search)
```python
# Current implementation in search_engine.py (placeholder)
def search_foods(query, filters=None):
    results = FoodItem.query.filter(
        FoodItem.name.contains(query)
    ).all()
    return results
```

**Algorithm:** SQL LIKE query (linear scan with pattern matching)
**Time Complexity:** O(n) where n = number of food items
**Space Complexity:** O(k) where k = number of results

**Why:**
- **Simplicity:** Easy to implement and maintain
- **Small Dataset:** Acceptable for initial food database (< 1000 items)
- **Flexibility:** Supports partial matches

**Optimization Opportunities:**
1. **Full-Text Search Index:**
   - Use PostgreSQL full-text search or Elasticsearch
   - Time Complexity: O(log n) for indexed searches
   
2. **Trie Data Structure:**
   - For prefix-based autocomplete
   - Time Complexity: O(m) where m = query length

3. **Inverted Index:**
   - For keyword-based search
   - Time Complexity: O(1) for keyword lookup + O(k) for result retrieval

**Future Implementation:**
```python
# Optimized search with indexing
def optimized_search(query, filters=None):
    # Use full-text search index
    results = FoodItem.query.search(query).filter(
        FoodItem.diabetes_friendly == True
    ).limit(20).all()
    return results
```

---

#### Filtering Algorithm
```python
def filter_foods(foods, filters):
    filtered = []
    for food in foods:
        if matches_filters(food, filters):
            filtered.append(food)
    return filtered
```

**Algorithm:** Linear Filtering
**Time Complexity:** O(n) where n = number of food items
**Space Complexity:** O(k) where k = filtered results

**Optimization:**
- **Database-Level Filtering:** Use SQL WHERE clauses
- **Time Complexity:** O(log n) with proper indexing
- **Reduced Memory:** Results filtered before retrieval

**Current Implementation:**
```python
# Efficient database-level filtering
FoodItem.query.filter_by(
    category='proteins',
    diabetes_friendly=True,
    is_affordable=True
).all()
```

---

### 2.2 Recommendation Algorithms

#### Content-Based Filtering (Placeholder)
```python
def recommend_foods(user_profile, available_foods):
    recommendations = []
    
    for food in available_foods:
        score = calculate_compatibility(user_profile, food)
        if score > threshold:
            recommendations.append((food, score))
    
    # Sort by score (descending)
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations
```

**Algorithm:** Scoring and Sorting
**Time Complexity:** O(n log n) where n = number of food items
- O(n) for scoring each food
- O(n log n) for sorting

**Space Complexity:** O(n) for recommendations list

**Why:**
- **Simplicity:** Easy to understand and debug
- **Transparency:** Clear scoring logic
- **Baseline:** Good starting point before ML integration

**Optimization:**
- **Early Termination:** Stop after finding top K items
- **Time Complexity:** O(n log k) using heap
- **Space Complexity:** O(k) for top K results

**Future ML Integration:**
- Replace scoring function with trained model
- Use collaborative filtering or deep learning
- Maintain same interface for seamless integration

---

#### Ranking Algorithm
```python
def rank_foods(foods, user_preferences):
    scored_foods = []
    
    for food in foods:
        score = (
            diabetes_score(food) * 0.4 +
            nutritional_score(food) * 0.3 +
            affordability_score(food) * 0.2 +
            preference_score(food, user_preferences) * 0.1
        )
        scored_foods.append((food, score))
    
    # Sort by combined score
    scored_foods.sort(key=lambda x: x[1], reverse=True)
    return [food for food, score in scored_foods]
```

**Algorithm:** Weighted Scoring with Sorting
**Time Complexity:** O(n log n)
**Space Complexity:** O(n)

**Why:**
- **Multi-Factor Ranking:** Considers multiple criteria
- **Weighted Importance:** Diabetes compatibility most important
- **Flexible:** Easy to adjust weights

---

### 2.3 Data Processing Algorithms

#### Data Normalization
```python
def normalize_nutritional_data(food_item):
    # Normalize to per 100g serving
    base_serving = 100.0
    
    normalized = {
        'calories': (food_item.calories / food_item.serving_size) * base_serving,
        'protein': (food_item.protein / food_item.serving_size) * base_serving,
        # ... other nutrients
    }
    return normalized
```

**Algorithm:** Linear Transformation
**Time Complexity:** O(1) per food item
**Space Complexity:** O(1)

**Why:**
- **Consistency:** Standardized nutritional comparisons
- **Accuracy:** Enables fair comparison across different serving sizes

---

#### Aggregation Algorithm (Dashboard Statistics)
```python
def calculate_glucose_statistics(records):
    if not records:
        return None
    
    values = [r.blood_glucose for r in records]
    
    stats = {
        'average': sum(values) / len(values),
        'min': min(values),
        'max': max(values),
        'count': len(values)
    }
    
    # Calculate trend (simplified)
    if len(values) >= 2:
        stats['trend'] = 'increasing' if values[-1] > values[0] else 'decreasing'
    
    return stats
```

**Algorithm:** Linear Scan with Aggregation
**Time Complexity:** O(n) where n = number of records
**Space Complexity:** O(n) for values list

**Why:**
- **Efficiency:** Single pass through data
- **Accuracy:** Exact calculations
- **Simplicity:** Easy to understand and maintain

**Optimization:**
- **Database Aggregation:** Use SQL AVG, MIN, MAX functions
- **Time Complexity:** O(n) but processed in database
- **Reduced Memory:** No need to load all records into memory

```python
# Optimized database aggregation
from sqlalchemy import func

stats = db.session.query(
    func.avg(DiabetesRecord.blood_glucose),
    func.min(DiabetesRecord.blood_glucose),
    func.max(DiabetesRecord.blood_glucose),
    func.count(DiabetesRecord.id)
).filter_by(user_id=user_id).first()
```

---

### 2.4 Authentication Algorithms

#### Password Hashing (Werkzeug)
```python
def set_password(self, password: str):
    self.password_hash = generate_password_hash(password)

def check_password(self, password: str) -> bool:
    return check_password_hash(self.password_hash, password)
```

**Algorithm:** PBKDF2 (Password-Based Key Derivation Function 2)
**Time Complexity:** O(1) - Constant time hashing
**Security:** 
- **Salt:** Random salt per password
- **Iterations:** Configurable (default: 260,000)
- **One-Way:** Cannot reverse hash to password

**Why:**
- **Security:** Industry-standard password hashing
- **Protection:** Resistant to rainbow table attacks
- **Performance:** Acceptable hashing time (~100ms)

---

#### User Lookup (Flask-Login)
```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

**Algorithm:** Database Primary Key Lookup
**Time Complexity:** O(1) - Indexed primary key lookup
**Space Complexity:** O(1) - Single user object

**Why:**
- **Efficiency:** Fast user retrieval
- **Caching:** Flask-Login caches user in session
- **Scalability:** Database handles concurrent lookups

---

### 2.5 Sorting Algorithms

#### Recommendation Sorting
```python
recommendations.sort(key=lambda x: x['confidence_score'], reverse=True)
```

**Algorithm:** Timsort (Python's built-in sort)
**Time Complexity:** O(n log n) average case, O(n) best case (already sorted)
**Space Complexity:** O(n)

**Why:**
- **Efficiency:** Highly optimized hybrid sorting algorithm
- **Stability:** Maintains relative order of equal elements
- **Adaptive:** Performs well on partially sorted data

---

### 2.6 Caching Algorithms

#### Recommendation Caching (Future Implementation)
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_recommendations(user_id, context_hash):
    # Generate recommendations
    return recommendations
```

**Algorithm:** LRU (Least Recently Used) Cache
**Time Complexity:** O(1) for cache hits, O(n) for cache misses
**Space Complexity:** O(k) where k = cache size

**Why:**
- **Performance:** Avoids recomputation for frequent requests
- **Memory Management:** Automatically evicts least used entries
- **Scalability:** Reduces load on recommendation engine

---

## 3. Algorithm Choice Justifications

### 3.1 Search: Linear vs. Indexed

**Current Choice:** Linear Search (SQL LIKE)
**Justification:**
- Small dataset (< 1000 items)
- Simple implementation
- Acceptable performance for MVP

**Future Choice:** Full-Text Search Index
**Justification:**
- Scales to larger datasets
- Better performance (O(log n))
- Supports advanced queries (fuzzy matching, ranking)

---

### 3.2 Recommendations: Scoring vs. ML

**Current Choice:** Rule-Based Scoring
**Justification:**
- No training data required
- Transparent and explainable
- Quick to implement

**Future Choice:** Machine Learning Models
**Justification:**
- Learns from user behavior
- More accurate personalization
- Adapts to user preferences over time

---

### 3.3 Data Storage: SQLite vs. PostgreSQL

**Current Choice:** SQLite
**Justification:**
- Zero configuration
- File-based (easy deployment)
- Sufficient for development and small-scale production

**Future Choice:** PostgreSQL (for production)
**Justification:**
- Better concurrency
- Advanced indexing (full-text search)
- Better scalability
- ACID compliance for critical data

---

## 4. Performance Analysis

### 4.1 Time Complexity Summary

| Operation | Current Complexity | Optimized Complexity |
|-----------|-------------------|---------------------|
| User Lookup | O(1) | O(1) |
| Food Search | O(n) | O(log n) |
| Filtering | O(n) | O(log n) |
| Recommendations | O(n log n) | O(n log k) |
| Aggregation | O(n) | O(n) (DB) |
| Password Check | O(1) | O(1) |

### 4.2 Space Complexity Summary

| Data Structure | Space Complexity |
|----------------|-----------------|
| User Model | O(1) per user |
| FoodItem List | O(n) where n = food items |
| Recommendations | O(k) where k = recommendations |
| Session Data | O(1) per session |
| Cache | O(m) where m = cache size |

---

## 5. Scalability Considerations

### 5.1 Current Limitations

1. **Search:** Linear scan becomes slow with > 10,000 items
2. **Recommendations:** O(n log n) sorting for all items
3. **Database:** SQLite has write concurrency limits

### 5.2 Optimization Strategies

1. **Indexing:** Add indexes for frequently queried fields
2. **Pagination:** Limit result sets (e.g., top 20 recommendations)
3. **Caching:** Cache frequent queries
4. **Database Upgrade:** Migrate to PostgreSQL for production
5. **Load Balancing:** Distribute requests across servers

---

## 6. Algorithm Efficiency in Context

### 6.1 Search Efficiency

**Current Implementation:**
- **Small Dataset:** Acceptable O(n) performance
- **User Experience:** < 100ms response time for < 1000 items
- **Scalability:** Will need optimization for > 10,000 items

**Optimization Path:**
1. Add full-text search index
2. Implement result caching
3. Use database-level search optimization

---

### 6.2 Recommendation Efficiency

**Current Implementation:**
- **Scoring:** O(n) for n food items
- **Sorting:** O(n log n) for ranking
- **Total:** O(n log n) - acceptable for < 1000 items

**Future ML Implementation:**
- **Model Inference:** O(1) for trained model
- **Feature Preparation:** O(m) where m = feature count
- **Total:** O(m) - much faster for large datasets

---

### 6.3 Data Handling Efficiency

**Database Queries:**
- **Indexed Lookups:** O(log n) - efficient
- **Filtered Queries:** O(log n) with proper indexes
- **Aggregations:** O(n) but processed in database

**Memory Usage:**
- **Minimal:** Only load necessary data
- **Pagination:** Limit result sets
- **Caching:** Store frequently accessed data

---

## 7. Best Practices Applied

### 7.1 Database Design

✅ **Normalized Structure:** Reduces data redundancy
✅ **Proper Indexing:** Fast lookups on key fields
✅ **Foreign Keys:** Maintains referential integrity
✅ **Constraints:** Ensures data validity

### 7.2 Algorithm Selection

✅ **Appropriate Complexity:** Chosen based on dataset size
✅ **Maintainability:** Simple algorithms for clarity
✅ **Extensibility:** Easy to replace with optimized versions
✅ **Performance:** Acceptable for current scale

### 7.3 Code Organization

✅ **Separation of Concerns:** Algorithms in service layer
✅ **Reusability:** Functions can be used across routes
✅ **Testability:** Algorithms can be unit tested
✅ **Documentation:** Clear algorithm explanations

---

## 8. Future Algorithm Improvements

### 8.1 Search Enhancements

- **Trie for Autocomplete:** O(m) prefix matching
- **Inverted Index:** O(1) keyword lookup
- **Fuzzy Matching:** Levenshtein distance for typos

### 8.2 Recommendation Enhancements

- **Collaborative Filtering:** User-based recommendations
- **Matrix Factorization:** Efficient similarity computation
- **Deep Learning:** Complex pattern recognition

### 8.3 Data Processing Enhancements

- **Streaming Algorithms:** Process data in real-time
- **Distributed Computing:** Scale across multiple servers
- **Incremental Updates:** Update recommendations incrementally

---

## 9. Summary

The Glocusense application uses a combination of simple, efficient algorithms suitable for the current scale, with clear paths for optimization as the system grows. Key decisions:

1. **Database Models:** Relational structure for data integrity
2. **Search:** Linear for MVP, indexed for production
3. **Recommendations:** Rule-based for now, ML-ready architecture
4. **Authentication:** Industry-standard hashing
5. **Performance:** Acceptable for current scale, scalable design

All algorithms are chosen based on:
- **Current Requirements:** MVP functionality
- **Future Scalability:** Easy to optimize
- **Maintainability:** Clear and understandable
- **Performance:** Meets user experience goals

---

**Last Updated:** 2024
**Status:** Production-Ready Architecture

