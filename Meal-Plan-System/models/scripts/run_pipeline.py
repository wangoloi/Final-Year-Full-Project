#!/usr/bin/env python3
"""
Meal Recommendation Model - Full Pipeline
Runs from repo root: python models/scripts/run_pipeline.py
"""

import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

# Repository root (contains backend/, models/, …)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for CLI
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

np.random.seed(42)

# Paths (CSVs live under backend/datasets)
DATASETS_DIR = PROJECT_ROOT / 'backend' / 'datasets'
OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("MEAL RECOMMENDATION PIPELINE")
print("=" * 60)


def step1_load_data():
    """Step 1: Load datasets"""
    print("\n[STEP 1] Loading datasets...")
    df_diet = pd.read_csv(DATASETS_DIR / 'diet_recommendations_dataset.csv')
    df_meals = pd.read_csv(DATASETS_DIR / 'diabetic_diet_meal_plans_with_macros_GI.csv')
    print(f"  - diet_recommendations: {df_diet.shape}")
    print(f"  - diabetic_meal_plans: {df_meals.shape}")
    return df_diet, df_meals


def step2_eda(df_diet, df_meals):
    """Step 2: EDA - Save visual insights to output/"""
    print("\n[STEP 2] Exploratory Data Analysis - Saving to output/...")

    # --- Diet Recommendations EDA ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Disease Type distribution
    df_diet['Disease_Type'].value_counts().plot(kind='bar', ax=axes[0, 0], color='steelblue')
    axes[0, 0].set_title('Disease Type Distribution')
    axes[0, 0].set_xlabel('Disease Type')
    axes[0, 0].tick_params(axis='x', rotation=45)

    # 2. Diet Recommendation distribution
    df_diet['Diet_Recommendation'].value_counts().plot(kind='bar', ax=axes[0, 1], color='seagreen')
    axes[0, 1].set_title('Diet Recommendation Distribution')
    axes[0, 1].set_xlabel('Recommendation')
    axes[0, 1].tick_params(axis='x', rotation=45)

    # 3. BMI distribution
    df_diet['BMI'].hist(bins=30, ax=axes[1, 0], edgecolor='black', color='coral', alpha=0.7)
    axes[1, 0].set_title('BMI Distribution')
    axes[1, 0].set_xlabel('BMI')

    # 4. Glucose distribution
    df_diet['Glucose_mg/dL'].hist(bins=30, ax=axes[1, 1], edgecolor='black', color='mediumpurple', alpha=0.7)
    axes[1, 1].set_title('Glucose (mg/dL) Distribution')
    axes[1, 1].set_xlabel('Glucose')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'eda_diet_overview.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  - Saved: output/eda_diet_overview.png")

    # --- Correlation heatmap ---
    num_cols = ['Age', 'Weight_kg', 'Height_cm', 'BMI', 'Daily_Caloric_Intake', 'Cholesterol_mg/dL', 'Blood_Pressure_mmHg', 'Glucose_mg/dL']
    num_cols = [c for c in num_cols if c in df_diet.columns]
    if len(num_cols) > 1:
        corr = df_diet[num_cols].corr()
        plt.figure(figsize=(10, 8))
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, square=True)
        plt.title('Correlation Matrix - Diet Recommendations')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'eda_correlation_heatmap.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - Saved: output/eda_correlation_heatmap.png")

    # --- Meal Plans EDA ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Meal type distribution
    df_meals['Meal'].value_counts().plot(kind='bar', ax=axes[0, 0], color='teal')
    axes[0, 0].set_title('Meal Type Distribution')
    axes[0, 0].tick_params(axis='x', rotation=45)

    # 2. Group distribution
    df_meals['Group'].value_counts().plot(kind='bar', ax=axes[0, 1], color='darkorange')
    axes[0, 1].set_title('Patient Group Distribution')
    axes[0, 1].tick_params(axis='x', rotation=45)

    # 3. Calories distribution
    df_meals['Calories'].hist(bins=25, ax=axes[1, 0], edgecolor='black', color='skyblue')
    axes[1, 0].set_title('Calories per Meal Distribution')
    axes[1, 0].set_xlabel('Calories')

    # 4. Glycemic Index distribution
    df_meals['Glycemic Index'].hist(bins=20, ax=axes[1, 1], edgecolor='black', color='lightgreen')
    axes[1, 1].set_title('Glycemic Index Distribution')
    axes[1, 1].set_xlabel('Glycemic Index')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'eda_meal_plans_overview.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  - Saved: output/eda_meal_plans_overview.png")

    # --- Target variable (Diet_Recommendation) by Disease ---
    if 'Disease_Type' in df_diet.columns and 'Diet_Recommendation' in df_diet.columns:
        cross = pd.crosstab(df_diet['Disease_Type'], df_diet['Diet_Recommendation'])
        plt.figure(figsize=(12, 6))
        cross.plot(kind='bar', stacked=False, ax=plt.gca(), colormap='Set3')
        plt.title('Diet Recommendation by Disease Type')
        plt.xlabel('Disease Type')
        plt.ylabel('Count')
        plt.legend(title='Recommendation', bbox_to_anchor=(1.02, 1))
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'eda_recommendation_by_disease.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  - Saved: output/eda_recommendation_by_disease.png")

    print("  [SUCCESS] EDA complete. All figures saved to output/")


def step3_clean_and_prepare(df_diet):
    """Step 3: Data cleaning and preparation"""
    print("\n[STEP 3] Data cleaning and preprocessing...")
    df = df_diet.copy()

    # Fill missing
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isnull().any():
            df[col].fillna(df[col].median(), inplace=True)
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].isnull().any():
            df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown', inplace=True)

    # Encode categorical
    le_disease = LabelEncoder()
    le_recommendation = LabelEncoder()
    if 'Disease_Type' in df.columns:
        df['Disease_Type_enc'] = le_disease.fit_transform(df['Disease_Type'].astype(str))
    if 'Diet_Recommendation' in df.columns:
        df['Diet_Recommendation_enc'] = le_recommendation.fit_transform(df['Diet_Recommendation'].astype(str))

    print(f"  - Rows: {len(df)}, Columns: {len(df.columns)}")
    return df, le_recommendation


def step4_train_model(df):
    """Step 4: Train recommendation model"""
    print("\n[STEP 4] Training model...")

    feature_cols = [c for c in df.columns if c not in ['Patient_ID', 'Diet_Recommendation', 'Diet_Recommendation_enc',
                  'Disease_Type', 'Severity', 'Physical_Activity_Level', 'Dietary_Restrictions', 'Allergies', 'Preferred_Cuisine']]
    feature_cols = [c for c in feature_cols if df[c].dtype in [np.int64, np.float64]]

    if 'Diet_Recommendation_enc' not in df.columns:
        print("  [ERROR] Target column not found.")
        return None, None, None

    X = df[feature_cols].fillna(0)
    y = df['Diet_Recommendation_enc']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)

    print(f"  - Accuracy: {acc:.4f}")
    print("\n  Classification Report:")
    print(classification_report(y_test, y_pred))
    return model, scaler, feature_cols


def step5_save_model(model, scaler, feature_cols, le_recommendation):
    """Step 5: Save model and artifacts"""
    print("\n[STEP 5] Saving model...")
    artifacts = {
        'model': model,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'label_encoder': le_recommendation,
    }
    joblib.dump(artifacts, OUTPUT_DIR / 'meal_recommendation_model.joblib')
    print(f"  - Saved: output/meal_recommendation_model.joblib")


def main():
    try:
        df_diet, df_meals = step1_load_data()
        step2_eda(df_diet, df_meals)
        df_clean, le_rec = step3_clean_and_prepare(df_diet)
        model, scaler, feat_cols = step4_train_model(df_clean)
        if model is not None:
            step5_save_model(model, scaler, feat_cols, le_rec)
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
