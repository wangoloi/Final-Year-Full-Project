"""Transform the insulin prediction notebook to the 14-step regression pipeline."""
import json
from pathlib import Path

NOTEBOOK_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "notebooks" / "insulin_prediction_development.ipynb"
)

with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb["cells"]

# Pad or trim to 32 cells first
while len(cells) < 32:
    cells.append({"cell_type": "code", "metadata": {}, "source": ["# placeholder\n"], "outputs": [], "execution_count": None})
while len(cells) > 32:
    cells.pop()

# Cell 0: Update title
cells[0]["source"] = [
    "# Insulin Dosage Prediction — Machine Learning Regression Pipeline\n",
    "\n",
    "**GlucoSense** — End-to-end ML pipeline for predicting continuous insulin dosage (units).\n",
    "\n",
    "This notebook implements a structured 14-step regression workflow:\n",
    "1. Load and Understand the Dataset\n",
    "2. Exploratory Data Analysis (EDA)\n",
    "3. Data Cleaning\n",
    "4. Feature Engineering\n",
    "5. Feature Selection\n",
    "6. Feature Scaling\n",
    "7. Data Splitting (80% train, 10% val, 10% test)\n",
    "8. Train Regression Models\n",
    "9. Model Evaluation (MAE, MSE, R²)\n",
    "10. Hyperparameter Tuning\n",
    "11. Model Interpretation (Feature Importance)\n",
    "12. Final Model Selection\n",
    "13. Prediction Pipeline\n",
    "14. Documentation\n",
]

# Cell 1
cells[1]["source"] = [
    "## Step 1: Load and Understand the Dataset\n",
    "\n",
    "Load the dataset, derive the continuous target (Insulin_Dose), and inspect shape, types, missing values, duplicates, and statistical summary.\n",
]

# Cell 2: Add derive_insulin_dose import
cells[2]["source"] = [
    "import sys\n",
    "from pathlib import Path\n",
    "\n",
    "# Resolve project root (works from notebooks/ or project root)\n",
    "_root = Path(\".\").resolve()\n",
    "if not (_root / \"data\" / \"SmartSensor_DiabetesMonitoring.csv\").exists():\n",
    "    _root = Path(\"..\").resolve()\n",
    "sys.path.insert(0, str(_root / \"src\"))\n",
    "\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import warnings\n",
    "warnings.filterwarnings(\"ignore\")\n",
    "\n",
    "from insulin_system.data_processing.load import load_and_validate, derive_insulin_dose\n",
    "from insulin_system.config.schema import DataSchema\n",
    "\n",
    "DATA_PATH = _root / \"data\" / \"SmartSensor_DiabetesMonitoring.csv\"\n",
    "schema = DataSchema()\n",
]

# Cell 3
cells[3]["source"] = [
    "# Load dataset and derive continuous target (Insulin_Dose)\n",
    "df = load_and_validate(DATA_PATH)\n",
    "df = derive_insulin_dose(df, schema)\n",
    "\n",
    "# Display dataset shape\n",
    "print(\"=== Dataset Shape ===\")\n",
    "print(f\"Rows: {df.shape[0]}, Columns: {df.shape[1]}\")\n",
    "\n",
    "# Display column names and data types\n",
    "print(\"\\n=== Column Names & Data Types ===\")\n",
    "print(df.dtypes)\n",
    "\n",
    "# Display dataset info\n",
    "print(\"\\n=== Dataset Info ===\")\n",
    "df.info()\n",
]

# Cell 4
cells[4]["source"] = [
    "# Missing values\n",
    "print(\"=== Missing Values ===\")\n",
    "missing = df.isnull().sum()\n",
    "if missing.sum() > 0:\n",
    "    print(missing[missing > 0])\n",
    "else:\n",
    "    print(\"No missing values.\")\n",
    "\n",
    "# Duplicate rows\n",
    "print(\"\\n=== Duplicate Rows ===\")\n",
    "print(f\"Duplicate rows: {df.duplicated().sum()}\")\n",
    "\n",
    "# Numerical vs categorical features\n",
    "print(\"\\n=== Numerical vs Categorical ===\")\n",
    "num_cols = df.select_dtypes(include=[np.number]).columns.tolist()\n",
    "cat_cols = df.select_dtypes(include=[\"object\", \"category\"]).columns.tolist()\n",
    "print(f\"Numerical: {num_cols}\")\n",
    "print(f\"Categorical: {cat_cols}\")\n",
    "\n",
    "# Statistical summary\n",
    "print(\"\\n=== Statistical Summary ===\")\n",
    "display(df.describe(include=\"all\"))\n",
    "\n",
    "# Target (Insulin_Dose) summary\n",
    "print(\"\\n=== Target (Insulin_Dose) Summary ===\")\n",
    "print(df[schema.TARGET_REGRESSION].describe())\n",
]

# Cell 5: Step 2 EDA
cells[5]["source"] = [
    "## Step 2: Exploratory Data Analysis (EDA)\n",
    "\n",
    "Plot target distribution, correlation matrix, scatter plots of key features vs Insulin_Dose, and identify potential outliers.\n",
]

# Cell 6: EDA plots
cells[6]["source"] = [
    "# Distribution of target variable (Insulin_Dose)\n",
    "plt.figure(figsize=(10, 4))\n",
    "plt.subplot(1, 2, 1)\n",
    "df[schema.TARGET_REGRESSION].hist(bins=50, color=\"steelblue\", edgecolor=\"white\")\n",
    "plt.title(\"Distribution of Insulin_Dose (Target)\")\n",
    "plt.xlabel(\"Insulin Dose (units)\")\n",
    "plt.ylabel(\"Count\")\n",
    "\n",
    "plt.subplot(1, 2, 2)\n",
    "df[schema.TARGET_REGRESSION].plot(kind=\"box\")\n",
    "plt.title(\"Insulin_Dose Box Plot\")\n",
    "plt.ylabel(\"Insulin Dose (units)\")\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
    "\n",
    "# Correlation matrix for all numerical variables\n",
    "num_cols_all = [c for c in df.columns if df[c].dtype in [np.float64, np.int64] and c != schema.PATIENT_ID]\n",
    "corr = df[num_cols_all].corr()\n",
    "plt.figure(figsize=(12, 10))\n",
    "sns.heatmap(corr, annot=True, fmt=\".2f\", cmap=\"coolwarm\", center=0, square=True, linewidths=0.5)\n",
    "plt.title(\"Correlation Matrix (Numerical Variables)\")\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
]

# Cell 7: Scatter plots and outliers
cells[7]["source"] = [
    "# Scatter plots: key features vs Insulin_Dose\n",
    "key_features = [\"glucose_level\", \"HbA1c\", \"weight\", \"BMI\", \"insulin_sensitivity\"]\n",
    "fig, axes = plt.subplots(2, 3, figsize=(14, 8))\n",
    "axes = axes.flatten()\n",
    "for i, col in enumerate(key_features):\n",
    "    if col in df.columns:\n",
    "        axes[i].scatter(df[col], df[schema.TARGET_REGRESSION], alpha=0.3, s=5)\n",
    "        axes[i].set_xlabel(col)\n",
    "        axes[i].set_ylabel(\"Insulin_Dose\")\n",
    "        axes[i].set_title(f\"{col} vs Insulin_Dose\")\n",
    "for j in range(len(key_features), len(axes)):\n",
    "    axes[j].set_visible(False)\n",
    "plt.suptitle(\"Key Features vs Insulin Dose\", y=1.02)\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
    "\n",
    "# Identify potential outliers (IQR method)\n",
    "def detect_outliers_iqr(series):\n",
    "    Q1 = series.quantile(0.25)\n",
    "    Q3 = series.quantile(0.75)\n",
    "    IQR = Q3 - Q1\n",
    "    return (series < (Q1 - 1.5 * IQR)) | (series > (Q3 + 1.5 * IQR))\n",
    "\n",
    "print(\"=== Potential Outliers (IQR method) ===\")\n",
    "outlier_counts = {}\n",
    "for col in schema.NUMERIC:\n",
    "    if col in df.columns:\n",
    "        n_out = detect_outliers_iqr(df[col]).sum()\n",
    "        if n_out > 0:\n",
    "            outlier_counts[col] = n_out\n",
    "for col, cnt in outlier_counts.items():\n",
    "    print(f\"  {col}: {cnt} outliers\")\n",
    "if not outlier_counts:\n",
    "    print(\"  None detected.\")\n",
]

# Cell 8: EDA insights
cells[8]["source"] = [
    "# Key insights from EDA\n",
    "print(\"\"\"\n",
    "Key EDA Insights:\n",
    "- Target (Insulin_Dose) is continuous; distribution shape informs modeling choices.\n",
    "- Correlation matrix reveals which features correlate with Insulin_Dose.\n",
    "- Scatter plots show linear vs non-linear relationships.\n",
    "- Outliers may need clipping to clinical bounds before modeling.\n",
    "\"\"\")\n",
]

# Cell 9: Step 3 header
cells[9]["source"] = [
    "## Step 3: Data Cleaning\n",
    "\n",
    "Handle missing values, remove duplicates, treat outliers, and ensure correct data formats.\n",
]

# Cell 10: Data cleaning (replace old cell 6 content)
cells[10]["source"] = [
    "# Drop patient_id (not a feature)\n",
    "df_clean = df.drop(columns=[schema.PATIENT_ID], errors=\"ignore\")\n",
    "\n",
    "# Handle missing values: median for numeric, mode for categorical\n",
    "print(\"=== Missing Value Handling ===\")\n",
    "for col in schema.NUMERIC:\n",
    "    if col in df_clean.columns and df_clean[col].isnull().sum() > 0:\n",
    "        df_clean[col] = df_clean[col].fillna(df_clean[col].median())\n",
    "        print(f\"  {col}: filled with median\")\n",
    "for col in schema.CATEGORICAL:\n",
    "    if col in df_clean.columns and df_clean[col].isnull().sum() > 0:\n",
    "        df_clean[col] = df_clean[col].fillna(df_clean[col].mode().iloc[0])\n",
    "        print(f\"  {col}: filled with mode\")\n",
    "if schema.TARGET_REGRESSION in df_clean.columns and df_clean[schema.TARGET_REGRESSION].isnull().sum() > 0:\n",
    "    df_clean = df_clean.dropna(subset=[schema.TARGET_REGRESSION])\n",
    "    print(\"  Dropped rows with missing target\")\n",
    "\n",
    "# Remove duplicate rows\n",
    "n_before = len(df_clean)\n",
    "df_clean = df_clean.drop_duplicates()\n",
    "print(f\"\\n=== Duplicates Removed: {n_before - len(df_clean)} ===\")\n",
    "\n",
    "# Treat outliers: clip to clinical bounds\n",
    "from insulin_system.config.schema import ClinicalBounds\n",
    "bounds = ClinicalBounds()\n",
    "for col in schema.NUMERIC:\n",
    "    if col in df_clean.columns:\n",
    "        try:\n",
    "            b = bounds.get_bounds_for_column(col)\n",
    "            df_clean[col] = df_clean[col].clip(lower=b[0], upper=b[1])\n",
    "        except KeyError:\n",
    "            pass\n",
    "print(\"\\n=== Outliers clipped to clinical bounds ===\")\n",
]

# Cell 11: Label encoding (exclude target)
cells[11]["source"] = [
    "# Label encoding for categorical features only (target Insulin_Dose stays continuous)\n",
    "from sklearn.preprocessing import LabelEncoder\n",
    "\n",
    "ENCODING_MAP = {}\n",
    "\n",
    "def fit_label_encoders(df, cols):\n",
    "    encoders = {}\n",
    "    for col in cols:\n",
    "        if col in df.columns:\n",
    "            le = LabelEncoder()\n",
    "            le.fit(df[col].astype(str))\n",
    "            encoders[col] = le\n",
    "    return encoders\n",
    "\n",
    "def transform_with_encoders(df, encoders):\n",
    "    out = df.copy()\n",
    "    for col, le in encoders.items():\n",
    "        if col in out.columns:\n",
    "            out[col] = le.transform(out[col].astype(str))\n",
    "    return out\n",
    "\n",
    "cat_cols = list(schema.CATEGORICAL)\n",
    "label_encoders = fit_label_encoders(df_clean, cat_cols)\n",
    "for col, le in label_encoders.items():\n",
    "    ENCODING_MAP[col] = dict(zip(le.classes_, le.transform(le.classes_)))\n",
    "    print(f\"{col}: {ENCODING_MAP[col]}\")\n",
    "\n",
    "df_encoded = transform_with_encoders(df_clean, label_encoders)\n",
]

# Cell 12: Step 4 header
cells[12]["source"] = [
    "## Step 4: Feature Engineering\n",
    "\n",
    "Create meaningful features (e.g., glucose_HbA1c_ratio, activity_category, metabolic_risk_score).\n",
]

# Cell 13: Feature engineering
cells[13]["source"] = [
    "# Feature engineering\n",
    "df_fe = df_encoded.copy()\n",
    "\n",
    "# glucose_HbA1c_ratio: glycemic control indicator\n",
    "if \"glucose_level\" in df_fe.columns and \"HbA1c\" in df_fe.columns:\n",
    "    df_fe[\"glucose_HbA1c_ratio\"] = df_fe[\"glucose_level\"] / (df_fe[\"HbA1c\"] + 1e-6)\n",
    "    print(\"Added: glucose_HbA1c_ratio (glycemic control)\")\n",
    "\n",
    "# Activity level categories (low/medium/high)\n",
    "if \"physical_activity\" in df_fe.columns:\n",
    "    df_fe[\"activity_category\"] = pd.cut(df_fe[\"physical_activity\"], bins=[-0.1, 3, 6, 15], labels=[0, 1, 2]).astype(float)\n",
    "    df_fe[\"activity_category\"] = df_fe[\"activity_category\"].fillna(1)\n",
    "    print(\"Added: activity_category (0=low, 1=medium, 2=high)\")\n",
    "\n",
    "# Metabolic risk score (weighted combo of glucose, HbA1c, BMI)\n",
    "if all(c in df_fe.columns for c in [\"glucose_level\", \"HbA1c\", \"BMI\"]):\n",
    "    g_norm = (df_fe[\"glucose_level\"] - df_fe[\"glucose_level\"].min()) / (df_fe[\"glucose_level\"].max() - df_fe[\"glucose_level\"].min() + 1e-6)\n",
    "    h_norm = (df_fe[\"HbA1c\"] - df_fe[\"HbA1c\"].min()) / (df_fe[\"HbA1c\"].max() - df_fe[\"HbA1c\"].min() + 1e-6)\n",
    "    b_norm = (df_fe[\"BMI\"] - df_fe[\"BMI\"].min()) / (df_fe[\"BMI\"].max() - df_fe[\"BMI\"].min() + 1e-6)\n",
    "    df_fe[\"metabolic_risk_score\"] = 0.4 * g_norm + 0.35 * h_norm + 0.25 * b_norm\n",
    "    print(\"Added: metabolic_risk_score\")\n",
]

# Cell 14: Step 5 header
cells[14]["source"] = [
    "## Step 5: Feature Selection\n",
    "\n",
    "Use correlation analysis to identify strong predictors. Remove low-correlation and highly collinear features.\n",
]

# Cell 15: Feature selection (regression)
cells[15]["source"] = [
    "# Feature selection for regression\n",
    "feat_cols = [c for c in df_fe.columns if c != schema.TARGET_REGRESSION and c != schema.TARGET]\n",
    "corr_target = df_fe[feat_cols + [schema.TARGET_REGRESSION]].corr()[schema.TARGET_REGRESSION].drop(schema.TARGET_REGRESSION)\n",
    "corr_target_abs = corr_target.abs().sort_values(ascending=False)\n",
    "\n",
    "# Drop features with very low correlation to target (|r| < 0.02)\n",
    "low_corr = corr_target_abs[corr_target_abs < 0.02].index.tolist()\n",
    "feat_cols = [c for c in feat_cols if c not in low_corr]\n",
    "if low_corr:\n",
    "    print(f\"Dropped low-correlation features: {low_corr}\")\n",
    "\n",
    "# Remove highly collinear features (|r| > 0.9 between features)\n",
    "corr_matrix = df_fe[feat_cols].corr()\n",
    "to_drop = set()\n",
    "for i, col1 in enumerate(feat_cols):\n",
    "    for col2 in feat_cols[i+1:]:\n",
    "        if abs(corr_matrix.loc[col1, col2]) > 0.9:\n",
    "            to_drop.add(col2)\n",
    "feat_cols = [c for c in feat_cols if c not in to_drop]\n",
    "if to_drop:\n",
    "    print(f\"Dropped collinear features: {to_drop}\")\n",
    "\n",
    "print(f\"\\nSelected {len(feat_cols)} features: {feat_cols}\")\n",
    "X = df_fe[feat_cols]\n",
    "y = df_fe[schema.TARGET_REGRESSION]\n",
]

# Cell 16: Step 6 & 7 header
cells[16]["source"] = [
    "## Step 6: Feature Scaling & Step 7: Data Splitting\n",
    "\n",
    "Apply StandardScaler. Split 80% train, 10% validation, 10% test.\n",
]

# Cell 17: Scaling and split
cells[17]["source"] = [
    "from sklearn.preprocessing import StandardScaler\n",
    "from sklearn.model_selection import train_test_split\n",
    "\n",
    "RANDOM_STATE = 42\n",
    "\n",
    "# Split: 80% train, 10% val, 10% test\n",
    "X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)\n",
    "X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=RANDOM_STATE)\n",
    "\n",
    "scaler = StandardScaler()\n",
    "X_train_scaled = scaler.fit_transform(X_train)\n",
    "X_val_scaled = scaler.transform(X_val)\n",
    "X_test_scaled = scaler.transform(X_test)\n",
    "\n",
    "print(f\"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}\")\n",
    "print(\"Scaling: StandardScaler (zero mean, unit variance) for models sensitive to feature scale.\")\n",
]

# Cell 18: Step 8 header
cells[18]["source"] = [
    "## Step 8: Train Regression Models\n",
    "\n",
    "Train Linear Regression, Decision Tree, Random Forest, Gradient Boosting regressors.\n",
]

# Cell 19: Train regression models
cells[19]["source"] = [
    "from sklearn.linear_model import LinearRegression\n",
    "from sklearn.tree import DecisionTreeRegressor\n",
    "from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor\n",
    "\n",
    "models = {\n",
    "    \"linear_regression\": LinearRegression(),\n",
    "    \"decision_tree\": DecisionTreeRegressor(random_state=RANDOM_STATE),\n",
    "    \"random_forest\": RandomForestRegressor(random_state=RANDOM_STATE),\n",
    "    \"gradient_boosting\": GradientBoostingRegressor(random_state=RANDOM_STATE),\n",
    "}\n",
    "\n",
    "fitted = {}\n",
    "for name, model in models.items():\n",
    "    model.fit(X_train_scaled, y_train)\n",
    "    fitted[name] = model\n",
    "    print(f\"Trained: {name}\")\n",
]

# Cell 20: Step 9 header
cells[20]["source"] = [
    "## Step 9: Model Evaluation\n",
    "\n",
    "Evaluate with MAE, MSE, R². Compare models.\n",
]

# Cell 21: Evaluation
cells[21]["source"] = [
    "from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score\n",
    "\n",
    "results = []\n",
    "for name, model in fitted.items():\n",
    "    y_pred = model.predict(X_test_scaled)\n",
    "    mae = mean_absolute_error(y_test, y_pred)\n",
    "    mse = mean_squared_error(y_test, y_pred)\n",
    "    r2 = r2_score(y_test, y_pred)\n",
    "    results.append({\"model\": name, \"MAE\": mae, \"MSE\": mse, \"R2\": r2})\n",
    "\n",
    "results_df = pd.DataFrame(results).sort_values(\"R2\", ascending=False)\n",
    "print(\"=== Model Comparison (Test Set) ===\")\n",
    "print(results_df.to_string(index=False))\n",
    "\n",
    "best_model_name = results_df.iloc[0][\"model\"]\n",
    "best_model = fitted[best_model_name]\n",
    "print(f\"\\nBest model (by R²): {best_model_name}\")\n",
]

# Cell 22: Step 10 header
cells[22]["source"] = [
    "## Step 10: Hyperparameter Tuning\n",
    "\n",
    "Improve best model with GridSearchCV or RandomSearchCV.\n",
]

# Cell 23: Hyperparameter tuning
cells[23]["source"] = [
    "from sklearn.model_selection import GridSearchCV\n",
    "\n",
    "# Tune best tree-based model (Random Forest or Gradient Boosting)\n",
    "if best_model_name == \"gradient_boosting\":\n",
    "    param_grid = {\"n_estimators\": [100, 200], \"max_depth\": [3, 5, 7], \"learning_rate\": [0.05, 0.1]}\n",
    "    base = GradientBoostingRegressor(random_state=RANDOM_STATE)\n",
    "else:\n",
    "    param_grid = {\"n_estimators\": [100, 200], \"max_depth\": [5, 10, 15]}\n",
    "    base = RandomForestRegressor(random_state=RANDOM_STATE)\n",
    "\n",
    "grid = GridSearchCV(base, param_grid, cv=3, scoring=\"r2\", n_jobs=-1)\n",
    "grid.fit(X_train_scaled, y_train)\n",
    "best_model = grid.best_estimator_\n",
    "print(f\"Best params: {grid.best_params_}\")\n",
    "print(f\"Best CV R²: {grid.best_score_:.4f}\")\n",
]

# Cell 24: Step 11 header
cells[24]["source"] = [
    "## Step 11: Model Interpretation\n",
    "\n",
    "Identify most important features influencing insulin dose prediction.\n",
]

# Cell 25: Feature importance
cells[25]["source"] = [
    "# Feature importance (tree-based models)\n",
    "if hasattr(best_model, \"feature_importances_\"):\n",
    "    imp = pd.Series(best_model.feature_importances_, index=feat_cols).sort_values(ascending=False)\n",
    "    imp.plot(kind=\"barh\", figsize=(10, 6))\n",
    "    plt.title(\"Feature Importance (Best Model)\")\n",
    "    plt.tight_layout()\n",
    "    plt.show()\n",
    "    print(\"Top features:\", imp.head(5).to_dict())\n",
    "else:\n",
    "    # Linear regression coefficients\n",
    "    coef = pd.Series(best_model.coef_, index=feat_cols).abs().sort_values(ascending=False)\n",
    "    coef.plot(kind=\"barh\", figsize=(10, 6))\n",
    "    plt.title(\"Feature Importance (|Coefficients|)\")\n",
    "    plt.tight_layout()\n",
    "    plt.show()\n",
]

# Cell 26: Step 12 header
cells[26]["source"] = [
    "## Step 12: Final Model Selection\n",
    "\n",
    "Select best model based on evaluation metrics and stability.\n",
]

# Cell 27: Final selection
cells[27]["source"] = [
    "print(f\"Final model: {best_model_name}\")\n",
    "print(\"Selection rationale: Best R² on test set; tree-based models capture non-linear relationships.\")\n",
    "selected_features = feat_cols\n",
]

# Cell 28: Step 13 header
cells[28]["source"] = [
    "## Step 13: Prediction Pipeline\n",
    "\n",
    "Reusable pipeline: accept new patient input, preprocess, predict insulin dose.\n",
]

# Cell 29: Prediction pipeline
cells[29]["source"] = [
    "def predict_insulin_dose(patient_dict, encoders, scaler, model, feature_names):\n",
    "    \"\"\"Accept new patient input, preprocess, and predict insulin dose (units).\"\"\"\n",
    "    row = pd.DataFrame([patient_dict])\n",
    "    for col in schema.CATEGORICAL:\n",
    "        if col in encoders and col in row.columns:\n",
    "            row[col] = encoders[col].transform(row[col].astype(str))\n",
    "    # Add engineered features\n",
    "    if \"glucose_HbA1c_ratio\" in feature_names and \"glucose_level\" in row.columns and \"HbA1c\" in row.columns:\n",
    "        row[\"glucose_HbA1c_ratio\"] = row[\"glucose_level\"] / (row[\"HbA1c\"] + 1e-6)\n",
    "    if \"activity_category\" in feature_names and \"physical_activity\" in row.columns:\n",
    "        row[\"activity_category\"] = pd.cut(row[\"physical_activity\"], bins=[-0.1, 3, 6, 15], labels=[0, 1, 2]).astype(float).fillna(1)\n",
    "    if \"metabolic_risk_score\" in feature_names:\n",
    "        g = row[\"glucose_level\"]; h = row[\"HbA1c\"]; b = row[\"BMI\"]\n",
    "        row[\"metabolic_risk_score\"] = 0.4 * (g - g.min()) / (g.max() - g.min() + 1e-6) + 0.35 * (h - h.min()) / (h.max() - h.min() + 1e-6) + 0.25 * (b - b.min()) / (b.max() - b.min() + 1e-6)\n",
    "    X_new = row[feature_names].values\n",
    "    X_scaled = scaler.transform(X_new)\n",
    "    dose = model.predict(X_scaled)[0]\n",
    "    return float(np.clip(dose, 2, 120))\n",
    "\n",
    "# Example\n",
    "new_patient = {\"gender\": \"male\", \"family_history\": \"yes\", \"food_intake\": \"high\", \"previous_medications\": \"oral\",\n",
    "               \"age\": 45, \"glucose_level\": 140, \"physical_activity\": 5, \"BMI\": 28, \"HbA1c\": 7.5,\n",
    "               \"weight\": 80, \"insulin_sensitivity\": 1.0, \"sleep_hours\": 7, \"creatinine\": 1.0}\n",
    "pred_dose = predict_insulin_dose(new_patient, label_encoders, scaler, best_model, selected_features)\n",
    "print(f\"Predicted insulin dose: {pred_dose:.1f} units\")\n",
    "print(\"\\nClinical disclaimer: Decision-support only. Review by healthcare professional required.\")\n",
]

# Cell 30: Step 14 header
cells[30]["source"] = [
    "## Step 14: Documentation\n",
    "\n",
    "Document preprocessing, feature engineering, evaluation, and model justification.\n",
]

# Cell 31: Documentation + save
cells[31]["source"] = [
    "import joblib\n",
    "import json\n",
    "\n",
    "OUTPUT_DIR = _root / \"outputs\" / \"best_model\"\n",
    "OUTPUT_DIR.mkdir(parents=True, exist_ok=True)\n",
    "\n",
    "bundle = {\n",
    "    \"model\": best_model,\n",
    "    \"scaler\": scaler,\n",
    "    \"label_encoders\": label_encoders,\n",
    "    \"encoding_map\": ENCODING_MAP,\n",
    "    \"selected_features\": selected_features,\n",
    "    \"model_name\": best_model_name,\n",
    "}\n",
    "joblib.dump(bundle, OUTPUT_DIR / \"inference_bundle.joblib\")\n",
    "\n",
    "metadata = {\n",
    "    \"model_name\": best_model_name,\n",
    "    \"target\": schema.TARGET_REGRESSION,\n",
    "    \"feature_names\": selected_features,\n",
    "    \"preprocessing\": \"StandardScaler, label encoding for categoricals\",\n",
    "    \"feature_engineering\": \"glucose_HbA1c_ratio, activity_category, metabolic_risk_score\",\n",
    "}\n",
    "with open(OUTPUT_DIR / \"metadata.json\", \"w\") as f:\n",
    "    json.dump(metadata, f, indent=2)\n",
    "\n",
    "print(f\"Saved to {OUTPUT_DIR}\")\n",
    "print(\"\"\"\n",
    "Documentation Summary:\n",
    "- Preprocessing: Missing values (median/mode), duplicates removed, outliers clipped to clinical bounds.\n",
    "- Feature engineering: glucose_HbA1c_ratio, activity_category, metabolic_risk_score.\n",
    "- Feature selection: Correlation-based; dropped low-correlation and collinear features.\n",
    "- Scaling: StandardScaler for regression models.\n",
    "- Split: 80/10/10 train/val/test.\n",
    "- Best model: Selected by R² on test set.\n",
    "\"\"\")\n",
]

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=2)

print("Notebook transformed successfully.")
