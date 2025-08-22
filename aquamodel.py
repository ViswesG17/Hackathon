import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import numpy as np

# --- IMPORTANT: Your MongoDB connection string ---
MONGO_CONNECTION_STRING = "mongodb+srv://ViswesG:31606021@cluster0.y4ghrvc.mongodb.net/"

# --- MongoDB Connection ---
print("[INFO] Connecting to MongoDB Atlas...")
client = MongoClient(MONGO_CONNECTION_STRING)
# Connect to your specific database
db = client["aqua_management_db"] 
print("✅ Connected to MongoDB Atlas")

# --- Helper function to load collections safely ---
def load_collection(name):
    """Loads a MongoDB collection into a pandas DataFrame."""
    df = pd.DataFrame(list(db[name].find()))
    if df.empty:
        print(f"⚠️ [WARN] Collection '{name}' is empty — skipping.")
        return df
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    print(f"✅ [INFO] Loaded '{name}': {df.shape}")
    return df

# --- 1. Load Base and Static Data ---
# 'crops' is our central table, representing each farming cycle.
df_crops = load_collection("crops")
if df_crops.empty:
    raise SystemExit("🛑 [ERROR] 'crops' collection is empty. Cannot proceed without data.")

# Load related data
df_ponds = load_collection("ponds")
df_stocking = load_collection("stocking_details")
df_harvests = load_collection("harvests")

# --- 2. Aggregate Time-Series Data ---
# We must aggregate logs to create summary features for each crop.

# Aggregate Water Quality Logs
df_water_quality = load_collection("water_quality_logs")
if not df_water_quality.empty:
    # Convert timestamp to datetime if it's not already
    df_water_quality['timestamp'] = pd.to_datetime(df_water_quality['timestamp'])
    numeric_cols = df_water_quality.select_dtypes(include=np.number).columns.tolist()
    
    df_water_agg = df_water_quality.groupby("crop_id")[numeric_cols].agg(['mean', 'std', 'min', 'max']).reset_index()
    # Flatten multi-level column names (e.g., from ('ph', 'mean') to 'ph_mean')
    df_water_agg.columns = ['_'.join(col).strip() for col in df_water_agg.columns.values]
    df_water_agg = df_water_agg.rename(columns={"crop_id_": "crop_id"})
    print("✅ [INFO] Aggregated water quality logs.")

# Aggregate Feed Logs
df_feed = load_collection("feed_logs")
if not df_feed.empty:
    df_feed['timestamp'] = pd.to_datetime(df_feed['timestamp'])
    df_feed_agg = df_feed.groupby("crop_id").agg(
        total_feed_kg=('quantity_kg', 'sum'),
        avg_feed_kg=('quantity_kg', 'mean'),
        feed_days=('timestamp', 'nunique')
    ).reset_index()
    print("✅ [INFO] Aggregated feed logs.")

# Aggregate Health Checks
df_health = load_collection("health_checks")
if not df_health.empty:
    df_health_agg = df_health.groupby("crop_id").agg(
        total_mortality=('mortality_count_est', 'sum')
    ).reset_index()
    print("✅ [INFO] Aggregated health checks.")

# --- 3. Merge All DataFrames ---
print("🔄 [INFO] Merging all data sources...")
df = df_crops

# Merge static data
if not df_ponds.empty:
    df = pd.merge(df, df_ponds, on="pond_id", how="left")
if not df_stocking.empty:
    df = pd.merge(df, df_stocking, on="crop_id", how="left")
if not df_harvests.empty:
    # Only include features that would be known before the final status is determined
    harvest_features = ['crop_id', 'survival_rate_percent']
    if all(col in df_harvests.columns for col in harvest_features):
        df = pd.merge(df, df_harvests[harvest_features], on="crop_id", how="left")

# Merge aggregated time-series data
if 'df_water_agg' in locals() and not df_water_agg.empty:
    df = pd.merge(df, df_water_agg, on="crop_id", how="left")
if 'df_feed_agg' in locals() and not df_feed_agg.empty:
    df = pd.merge(df, df_feed_agg, on="crop_id", how="left")
if 'df_health_agg' in locals() and not df_health_agg.empty:
    df = pd.merge(df, df_health_agg, on="crop_id", how="left")

print(f"✅ Final merged DataFrame shape: {df.shape}")
df.to_csv("merged_aquaculture_data.csv", index=False)
print("💾 Data saved to merged_aquaculture_data.csv")

# --- 4. Feature Engineering and Preparation ---
print("⚙️ [INFO] Preparing data for model training...")

# Define the target variable we want to predict
target_col = "status"
# For a predictive model, it's best to predict a state like 'Diseased' vs. 'Healthy'.
# We filter out 'Harvested' as it's typically an outcome, not a state to predict during the cycle.
df = df[df[target_col].isin(['Healthy', 'Diseased'])].copy()

if df.empty or df[target_col].nunique() < 2:
    raise SystemExit("🛑 [ERROR] Not enough data or classes to train. Need at least two statuses ('Healthy', 'Diseased').")

# Convert the categorical target ('Healthy', 'Diseased') into numbers (0, 1)
df['target'] = pd.factorize(df[target_col])[0]
y = df['target']

# Select features for the model
# Drop IDs, dates, text, and the original target column
features_to_drop = [
    'crop_id', 'pond_id', 'farm_id', 'technician_id', 'hatchery_id',
    'stocking_date', 'created_at', 'status', 'target', 'observation', 
    'symptoms_noted', 'treatment_applied'
]
existing_cols_to_drop = [col for col in features_to_drop if col in df.columns]
df_features = df.drop(columns=existing_cols_to_drop)

# One-hot encode categorical features (like 'species', 'pond_type')
df_features = pd.get_dummies(df_features, columns=df_features.select_dtypes(include=['object']).columns, dummy_na=True)

# Impute missing values with the mean of their column
df_features = df_features.fillna(df_features.mean())

X = df_features
print(f"✅ [INFO] Features for training: {X.shape}")
print(f"📊 [INFO] Target distribution:\n{df[target_col].value_counts(normalize=True)}")

# --- 5. Model Training ---
print("🚀 [INFO] Training model...")

# Split data into training and testing sets for reliable evaluation
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Initialize and train the RandomForestClassifier
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
model.fit(X_train, y_train)

# Evaluate the model on unseen test data
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"🎯 Model Accuracy on Test Set: {accuracy:.2f}")

# Save the trained model for future use
joblib.dump(model, "aquaculture_model.pkl")
print("✅ Model trained and saved as aquaculture_model.pkl")

# --- Feature Importance ---
# See which factors were most influential in the model's predictions
feature_importances = pd.DataFrame(model.feature_importances_,
                                   index = X_train.columns,
                                   columns=['importance']).sort_values('importance', ascending=False)
print("\n--- Top 10 Most Important Features ---")
print(feature_importances.head(10))