# Glocusense - Model Development & Integration Guide

## Overview

This document outlines the strategy for developing and integrating machine learning models into the Glocusense application. The system is designed with clear separation between frontend, backend, and model logic to facilitate seamless ML integration.

---

## 1. Model Architecture Overview

### 1.1 System Components

```
┌─────────────────┐
│   Frontend      │  (Templates, CSS, JS)
│   (User UI)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend API   │  (Flask Routes)
│   (app/routes)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Service Layer  │  (Business Logic)
│ (app/services)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ML Models      │  (Recommendation Engine)
│  (Placeholder)  │
└─────────────────┘
```

### 1.2 Data Flow

1. **User Input** → Frontend collects user data (profile, preferences, glucose levels)
2. **API Request** → Backend routes receive requests
3. **Service Processing** → Services prepare data for models
4. **Model Inference** → ML models generate recommendations
5. **Response** → Results formatted and returned to frontend

---

## 2. Required Models

### 2.1 Meal Recommendation Model

#### Purpose
Generate personalized meal recommendations based on:
- User diabetes type
- Blood glucose history
- Dietary preferences
- Budget constraints
- Nutritional requirements

#### Input Features:
```python
{
    'user_id': int,
    'diabetes_type': str,  # Type 1, Type 2, Gestational, Prediabetes
    'age': int,
    'gender': str,
    'height': float,  # cm
    'weight': float,  # kg
    'activity_level': str,
    'recent_glucose_levels': list[float],
    'glucose_trend': str,  # 'stable', 'high', 'low', 'fluctuating'
    'budget_range': str,  # 'low', 'medium', 'high'
    'monthly_budget': float,
    'preferred_categories': list[str],  # ['proteins', 'vegetables', ...]
    'allergies': list[str],
    'time_of_day': str,  # 'breakfast', 'lunch', 'dinner', 'snack'
}
```

#### Output Format:
```python
{
    'recommendations': [
        {
            'food_item_id': int,
            'food_name': str,
            'local_name': str,
            'category': str,
            'serving_size': float,
            'estimated_glucose_impact': float,  # mg/dL
            'nutritional_info': {
                'calories': float,
                'carbohydrates': float,
                'protein': float,
                'fiber': float,
                'glycemic_index': int
            },
            'price': float,
            'confidence_score': float,  # 0.0 - 1.0
            'reasoning': str  # Why this was recommended
        }
    ],
    'meal_plan': {
        'breakfast': list[dict],
        'lunch': list[dict],
        'dinner': list[dict],
        'snacks': list[dict]
    },
    'total_daily_calories': float,
    'total_carbohydrates': float,
    'estimated_glucose_impact': float
}
```

### 2.2 Blood Glucose Prediction Model

#### Purpose
Predict blood glucose levels based on:
- Meal composition
- Time of day
- User's historical patterns
- Activity level

#### Input Features:
```python
{
    'user_id': int,
    'meal_composition': {
        'total_carbohydrates': float,
        'total_fiber': float,
        'total_protein': float,
        'glycemic_index_avg': float,
        'meal_size': str  # 'small', 'medium', 'large'
    },
    'time_of_day': str,
    'time_since_last_meal': float,  # hours
    'recent_glucose': float,  # current level
    'activity_level': str,
    'medications': list[str]
}
```

#### Output Format:
```python
{
    'predicted_glucose_1h': float,  # mg/dL after 1 hour
    'predicted_glucose_2h': float,  # mg/dL after 2 hours
    'predicted_glucose_peak': float,  # mg/dL peak value
    'peak_time': float,  # hours from now
    'risk_level': str,  # 'low', 'moderate', 'high'
    'recommendations': list[str]  # Action items
}
```

### 2.3 Food Search & Ranking Model

#### Purpose
Rank and filter food items based on:
- Diabetes compatibility
- User preferences
- Nutritional value
- Price constraints

#### Input Features:
```python
{
    'query': str,  # Search query
    'user_id': int,
    'filters': {
        'category': list[str],
        'max_price': float,
        'min_protein': float,
        'max_carbohydrates': float,
        'max_glycemic_index': int
    },
    'user_preferences': {
        'preferred_categories': list[str],
        'budget_range': str
    }
}
```

#### Output Format:
```python
{
    'results': [
        {
            'food_item_id': int,
            'relevance_score': float,  # 0.0 - 1.0
            'diabetes_compatibility_score': float,
            'nutritional_score': float,
            'affordability_score': float,
            'overall_score': float
        }
    ],
    'total_results': int
}
```

---

## 3. Dataset Requirements

### 3.1 Food Database

#### Required Fields:
- Food name and local name
- Category (proteins, vegetables, grains, fruits, etc.)
- Nutritional information (calories, carbs, protein, fiber, fat, sugar)
- Glycemic index
- Diabetes-friendly flag
- Price information
- Cultural context (Ugandan foods)

#### Data Sources:
1. **Existing Data:** `app/utils/data_initializer.py` contains initial food items
2. **External Sources:**
   - USDA Food Database
   - Local food databases
   - Nutrition labels
   - Market price data

#### Preprocessing Steps:
```python
# Example preprocessing pipeline
def preprocess_food_data(raw_data):
    # 1. Normalize nutritional values
    # 2. Calculate diabetes compatibility score
    # 3. Encode categorical features
    # 4. Handle missing values
    # 5. Feature engineering (e.g., carb-to-fiber ratio)
    return processed_data
```

### 3.2 User Data

#### Required Data:
- User profiles (age, gender, height, weight, activity level)
- Diabetes type and history
- Blood glucose records
- Meal consumption history
- Preferences and allergies

#### Data Collection:
- User onboarding forms
- Diabetes record tracking
- Meal logging (future feature)
- Feedback on recommendations

### 3.3 Training Data Structure

```python
# Example training data format
training_data = {
    'features': [
        # User features
        'age', 'gender', 'height', 'weight', 'activity_level',
        'diabetes_type', 'avg_glucose', 'glucose_variance',
        # Meal features
        'meal_carbs', 'meal_fiber', 'meal_protein', 'meal_gi',
        # Context features
        'time_of_day', 'budget_range', 'preferred_categories'
    ],
    'targets': [
        'glucose_response',  # For prediction model
        'user_satisfaction',  # For recommendation model
        'meal_acceptance'    # For ranking model
    ]
}
```

---

## 4. Model Development Process

### 4.1 Recommendation Model Development

#### Step 1: Data Collection
```python
# Collect user interaction data
# Track which recommendations users accept/reject
# Monitor glucose responses to meals
```

#### Step 2: Feature Engineering
```python
def engineer_features(user_data, food_data):
    features = {
        # User characteristics
        'bmi': calculate_bmi(user_data['height'], user_data['weight']),
        'calorie_needs': calculate_calorie_needs(user_data),
        'carb_ratio': calculate_carb_ratio(user_data),
        
        # Food characteristics
        'diabetes_score': calculate_diabetes_score(food_data),
        'nutritional_density': calculate_nutritional_density(food_data),
        'affordability_score': calculate_affordability(food_data),
        
        # Compatibility
        'user_food_compatibility': calculate_compatibility(user_data, food_data)
    }
    return features
```

#### Step 3: Model Selection
**Recommended Approaches:**
- **Collaborative Filtering:** User-based and item-based recommendations
- **Content-Based Filtering:** Feature-based recommendations
- **Hybrid Approach:** Combine collaborative and content-based
- **Deep Learning:** Neural networks for complex pattern recognition

#### Step 4: Model Training
```python
# Example training pipeline
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import joblib

# Prepare data
X_train, X_test, y_train, y_test = train_test_split(
    features, targets, test_size=0.2, random_state=42
)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
score = model.score(X_test, y_test)

# Save model
joblib.dump(model, 'models/recommendation_model.pkl')
```

### 4.2 Blood Glucose Prediction Model

#### Approach:
- **Time Series Analysis:** LSTM or GRU for sequential glucose data
- **Regression Models:** Random Forest, XGBoost for meal-to-glucose mapping
- **Hybrid:** Combine time series and meal features

#### Training Pipeline:
```python
# Prepare sequential data
def prepare_sequences(glucose_data, meal_data, window_size=24):
    sequences = []
    targets = []
    
    for i in range(len(glucose_data) - window_size):
        seq = glucose_data[i:i+window_size]
        meal = meal_data[i]
        target = glucose_data[i+window_size]
        
        sequences.append(np.concatenate([seq, meal]))
        targets.append(target)
    
    return np.array(sequences), np.array(targets)
```

### 4.3 Model Evaluation Metrics

#### Recommendation Model:
- **Precision@K:** Top-K recommendation accuracy
- **Recall@K:** Coverage of relevant items
- **NDCG (Normalized Discounted Cumulative Gain):** Ranking quality
- **User Satisfaction:** Feedback-based metrics

#### Prediction Model:
- **MAE (Mean Absolute Error):** Average prediction error
- **RMSE (Root Mean Squared Error):** Penalizes large errors
- **R² Score:** Model fit quality
- **Clinical Accuracy:** Within acceptable glucose range

---

## 5. Model Integration

### 5.1 Service Layer Integration

#### Current Structure:
```python
# app/services/recommendation_engine.py (Placeholder)
class RecommendationEngine:
    def __init__(self):
        # Initialize models here
        self.recommendation_model = None
        self.prediction_model = None
    
    def load_models(self):
        """Load trained models"""
        import joblib
        self.recommendation_model = joblib.load('models/recommendation_model.pkl')
        self.prediction_model = joblib.load('models/prediction_model.pkl')
    
    def generate_recommendations(self, user_data, context):
        """Generate meal recommendations"""
        # Prepare features
        features = self.prepare_features(user_data, context)
        
        # Get predictions
        recommendations = self.recommendation_model.predict(features)
        
        # Post-process and format
        return self.format_recommendations(recommendations)
    
    def predict_glucose(self, meal_data, user_data):
        """Predict blood glucose response"""
        features = self.prepare_prediction_features(meal_data, user_data)
        prediction = self.prediction_model.predict(features)
        return self.format_prediction(prediction)
```

### 5.2 Route Integration

#### Example Route:
```python
# app/routes/recommendations.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services.recommendation_engine import RecommendationEngine

recommendations_bp = Blueprint('recommendations', __name__)
engine = RecommendationEngine()

@recommendations_bp.route('/recommendations', methods=['GET'])
@login_required
def get_recommendations():
    # Get user data
    user_data = current_user.to_dict()
    
    # Get context (time of day, etc.)
    context = {
        'time_of_day': request.args.get('time', 'lunch'),
        'glucose_level': request.args.get('glucose', None)
    }
    
    # Generate recommendations
    recommendations = engine.generate_recommendations(user_data, context)
    
    return jsonify(recommendations)
```

### 5.3 Frontend Integration

#### JavaScript Example:
```javascript
// Fetch recommendations
async function loadRecommendations() {
    const response = await fetch('/api/recommendations?time=lunch');
    const data = await response.json();
    
    // Display recommendations in UI
    displayRecommendations(data.recommendations);
}
```

---

## 6. Model Deployment

### 6.1 Model Storage

#### Recommended Structure:
```
models/
├── recommendation_model.pkl
├── prediction_model.pkl
├── search_ranking_model.pkl
├── model_metadata.json
└── version_info.txt
```

### 6.2 Model Versioning

```python
# model_metadata.json
{
    "recommendation_model": {
        "version": "1.0.0",
        "trained_date": "2024-01-15",
        "accuracy": 0.85,
        "features": ["age", "diabetes_type", ...],
        "algorithm": "RandomForest"
    }
}
```

### 6.3 Model Updates

#### Strategy:
1. **A/B Testing:** Test new models alongside existing ones
2. **Gradual Rollout:** Deploy to subset of users first
3. **Monitoring:** Track model performance in production
4. **Rollback:** Ability to revert to previous model version

---

## 7. Data Flow Between Components

### 7.1 Recommendation Flow

```
User Request
    ↓
Route Handler (app/routes/recommendations.py)
    ↓
Service Layer (app/services/recommendation_engine.py)
    ↓
Data Preparation
    ↓
Model Inference
    ↓
Post-processing
    ↓
Format Response
    ↓
Return to Frontend
```

### 7.2 Prediction Flow

```
Meal Selection
    ↓
Route Handler (app/routes/diabetes.py)
    ↓
Service Layer (app/services/recommendation_engine.py)
    ↓
Feature Extraction
    ↓
Model Prediction
    ↓
Format Prediction
    ↓
Display to User
```

---

## 8. Performance Considerations

### 8.1 Model Optimization

- **Caching:** Cache frequent recommendations
- **Batch Processing:** Process multiple requests together
- **Model Compression:** Reduce model size for faster inference
- **Async Processing:** Use background tasks for heavy computations

### 8.2 Scalability

- **Model Serving:** Consider TensorFlow Serving or similar
- **Database Optimization:** Index frequently queried fields
- **API Rate Limiting:** Prevent abuse
- **Load Balancing:** Distribute requests across instances

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
def test_recommendation_engine():
    engine = RecommendationEngine()
    engine.load_models()
    
    user_data = {
        'diabetes_type': 'Type 2',
        'age': 45,
        # ... other fields
    }
    
    recommendations = engine.generate_recommendations(user_data, {})
    assert len(recommendations) > 0
    assert all(r['diabetes_friendly'] for r in recommendations)
```

### 9.2 Integration Tests

- Test full request-response cycle
- Verify data format consistency
- Test error handling
- Validate model outputs

---

## 10. Next Steps

### 10.1 Immediate Actions

1. **Data Collection:**
   - Set up data logging for user interactions
   - Collect glucose response data
   - Build training dataset

2. **Model Development:**
   - Start with simple baseline models
   - Iterate and improve
   - Evaluate on test data

3. **Integration:**
   - Integrate models into service layer
   - Connect to routes
   - Update frontend to display results

### 10.2 Future Enhancements

- Real-time model updates
- Personalized model fine-tuning
- Multi-modal recommendations (text, images)
- Explainable AI for recommendation reasoning

---

## 11. Resources & Tools

### 11.1 Recommended Libraries

- **scikit-learn:** Traditional ML models
- **TensorFlow/PyTorch:** Deep learning models
- **pandas:** Data manipulation
- **numpy:** Numerical computations
- **joblib:** Model serialization

### 11.2 Development Tools

- **Jupyter Notebooks:** Model experimentation
- **MLflow:** Model tracking and versioning
- **TensorBoard:** Visualization (for deep learning)

---

**Last Updated:** 2024
**Status:** Ready for Model Development

