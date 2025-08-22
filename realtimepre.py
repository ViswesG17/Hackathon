import pandas as pd
from pymongo import MongoClient
import joblib
from datetime import datetime, timezone
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# --- Configuration ---
MODEL_METADATA_FILE = 'aqua_model.pkl'

# --- MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/")
LOG_DB_NAME = "aqua_model_prediction"
LOG_COLLECTION_NAME = "realtime_water_logs"
REPORT_COLLECTION_NAME = "consolidated_health_reports"

# --- Features for the REAL-TIME HEALTH model ---
REALTIME_HEALTH_FEATURES = [
    'dissolved_oxygen_mg_l', 'ph', 'temperature_c',
    'ammonia_ppm', 'nitrite_ppm', 'salinity_ppt'
]

# --- PART 1: MODEL CREATION (if needed) ---
def create_health_prediction_model():
    """
    Checks if a valid health prediction model exists. If not, it creates one.
    """
    if os.path.exists(MODEL_METADATA_FILE):
        try:
            model_data = joblib.load(MODEL_METADATA_FILE)
            if 'pipeline' in model_data and 'features' in model_data and model_data['features'] == REALTIME_HEALTH_FEATURES:
                print(f"[INFO] Correct model '{MODEL_METADATA_FILE}' already exists. Skipping creation.")
                return
            else:
                print(f"[WARN] Existing model file is for a different purpose. Deleting and recreating.")
                os.remove(MODEL_METADATA_FILE)
        except Exception:
            print(f"[WARN] Existing model file is corrupted. Deleting and recreating.")
            os.remove(MODEL_METADATA_FILE)

    print(f"--- Creating a new, correct health prediction model: '{MODEL_METADATA_FILE}' ---")

    dummy_records = []
    for i in range(200):
        is_warning = i % 10 == 0
        dummy_records.append({
            "status": "Warning" if is_warning else "Healthy",
            "dissolved_oxygen_mg_l": 4.1 if is_warning else 5.5,
            "ph": 8.9 if is_warning else 8.1, "temperature_c": 30.0,
            "ammonia_ppm": 0.6 if is_warning else 0.1, "nitrite_ppm": 0.1, "salinity_ppt": 20
        })
    dummy_df = pd.DataFrame(dummy_records)

    X = dummy_df[REALTIME_HEALTH_FEATURES]
    y = dummy_df['status']

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    pipeline.fit(X, y)

    model_data = {'pipeline': pipeline, 'features': REALTIME_HEALTH_FEATURES}
    joblib.dump(model_data, MODEL_METADATA_FILE)
    print(f"💾 New health model saved to '{MODEL_METADATA_FILE}'.\n")

# --- PART 2: REPORT GENERATION ---
def get_warning_reason(record):
    """Generates a plausible reason for a warning prediction."""
    if record.get('dissolved_oxygen_mg_l', 7) < 4.5:
        return "Low Dissolved Oxygen", "Increase aeration immediately."
    elif record.get('ammonia_ppm', 0) > 0.5:
        return "High Ammonia Levels", "Perform partial water exchange and reduce feeding."
    else:
        return "Multiple Parameters Sub-Optimal", "Perform a full water quality panel test."

def generate_health_report():
    """
    Fetches the last 60 logs, predicts their health, and saves a consolidated report.
    """
    print("[INFO] Connecting to MongoDB...")
    client = MongoClient(MONGO_URI)
    log_db = client[LOG_DB_NAME]
    log_collection = log_db[LOG_COLLECTION_NAME]

    print(f"[INFO] Loading model from '{MODEL_METADATA_FILE}'...")
    model_data = joblib.load(MODEL_METADATA_FILE)
    pipeline = model_data['pipeline']
    features = model_data['features']

    # --- NEW LOGIC: Fetch the absolute last 60 records from the collection ---
    print("\n[INFO] Fetching the last 60 log records from the database...")
    recent_records = list(log_collection.find().sort("timestamp", -1).limit(60))

    if not recent_records:
        print("[WARN] No log records found in the collection. Exiting.")
        return

    print(f"✅ Found {len(recent_records)} records to analyze.")
    df = pd.DataFrame(recent_records)

    X_predict = df.reindex(columns=features).fillna(0)
    predictions = pipeline.predict(X_predict)
    df['prediction'] = predictions

    final_reports = []
    print("[INFO] Aggregating predictions for each crop found in the recent data...")
    for crop_id, group in df.groupby('crop_id'):
        status = 'Warning' if 'Warning' in group['prediction'].unique() else 'Healthy'
        reason, action = ("N/A", "No action required.")
        if status == 'Warning':
            warning_record = group[group['prediction'] == 'Warning'].iloc[0]
            reason, action = get_warning_reason(warning_record)

        final_reports.append({
            "crop_id": crop_id, "report_timestamp": datetime.now(timezone.utc),
            "status": status,
            "reason": reason, "recommended_action": action
        })

    if final_reports:
        report_collection = log_db["consolidated_health_reports"]
        for report in final_reports:
            report_collection.update_one({'crop_id': report['crop_id']}, {'$set': report}, upsert=True)
        print(f"\n✅ Successfully saved/updated {len(final_reports)} consolidated reports.")

    client.close()

    print("\n--- Consolidated Aquaculture Health Report (from last 60 records) ---")
    if final_reports:
        report_df = pd.DataFrame(final_reports)
        print(report_df[['crop_id', 'status', 'reason']].to_string(index=False))
    print("--- End of Report ---\n")

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    # Step 1: Ensure the correct model exists before doing anything else.
    create_health_prediction_model()

    # Step 2: Now, generate the report using the guaranteed correct model.
    generate_health_report()