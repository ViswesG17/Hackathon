import pymongo
from faker import Faker
from datetime import datetime, timedelta, timezone
import random
import time
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import sys

# --- 1. Configuration ---
MONGO_URI = "mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/"
MAIN_DB_NAME = "aqua_management_db"
LOG_DB_NAME = "aqua_model_prediction"
LOG_COLLECTION_NAME = "realtime_water_logs"
REPORT_COLLECTION_NAME = "consolidated_health_reports"
MODEL_FILE = 'realtime_health_model.pkl'
SIMULATION_INTERVAL_SECONDS = 300  # 5 minutes

REALTIME_HEALTH_FEATURES = [
    'dissolved_oxygen_mg_l', 'ph', 'temperature_c', 
    'ammonia_ppm', 'nitrite_ppm', 'salinity_ppt'
]

# --- Flask App Initialization ---
app = Flask(_name_)
CORS(app)

# --- Global Variables ---
client = None
main_db = None
log_db = None
model_pipeline = None

# --- 2. Core Application Logic (Model, DB, Simulation) ---

def connect_to_db():
    """Establishes connections to both MongoDB databases."""
    global client, main_db, log_db
    try:
        client = pymongo.MongoClient(MONGO_URI)
        main_db = client[MAIN_DB_NAME]
        log_db = client[LOG_DB_NAME]
        client.admin.command('ping')
        print("✅ Database connection successful.")
        return True
    except Exception as e:
        print(f"❌ FATAL: Could not connect to MongoDB. Error: {e}")
        return False

def seed_database():
    """Generates and inserts a complete mock dataset into the main DB."""
    print("\n--- Starting Database Seeding (from aquamock.py logic) ---")
    
    fake = Faker('en_IN')
    collections = { name: main_db[name] for name in ["farms", "ponds", "technicians", "hatcheries", "crops", "stocking_details", "water_quality_logs", "feed_logs", "health_checks", "harvests"] }

    print("Clearing existing data...")
    for name, col in collections.items():
        col.delete_many({})

    technicians_data = [{"technician_id": f"TECH{i:04d}", "name": fake.name()} for i in range(1, 5)]
    hatcheries_data = [{"hatchery_id": f"HATCH{i:04d}", "hatchery_name": f"Hatchery {fake.company()}"} for i in range(1, 4)]
    
    farms_data, ponds_data, crops_data = [], [], []
    all_pond_ids = []
    for i in range(1, 4):
        farm_id = f"FARM{i:04d}"
        farms_data.append({"farm_id": farm_id, "farm_name": f"{fake.city()} Aqua Farm"})
        for j in range(1, 6):
            pond_id = f"POND{(i-1)*5+j:04d}"
            ponds_data.append({"pond_id": pond_id, "farm_id": farm_id, "pond_type": random.choice(["earthen", "lined"])})
            all_pond_ids.append(pond_id)

    for i in range(1, 16):
        crops_data.append({
            "crop_id": f"CROP{i:04d}",
            "pond_id": random.choice(all_pond_ids),
            "status": "active" if i % 3 == 0 else "harvested",
            "stocking_date": datetime.now() - timedelta(days=random.randint(30, 90))
        })

    collections["technicians"].insert_many(technicians_data)
    collections["hatcheries"].insert_many(hatcheries_data)
    collections["farms"].insert_many(farms_data)
    collections["ponds"].insert_many(ponds_data)
    collections["crops"].insert_many(crops_data)
    
    print("✅ Database seeding complete.")


def create_and_load_model():
    """Creates and loads the real-time health prediction model."""
    global model_pipeline
    if not os.path.exists(MODEL_FILE):
        print(f"--- Model '{MODEL_FILE}' not found. Creating a new one. ---")
        dummy_records = []
        for _ in range(400):
            is_warning = random.random() < 0.5
            dummy_records.append({
                "status": "Warning" if is_warning else "Healthy",
                "dissolved_oxygen_mg_l": round(random.uniform(3.5, 4.5) if is_warning else random.uniform(5.5, 7.5), 2),
                "ph": round(random.uniform(8.8, 9.5) if is_warning else random.uniform(7.8, 8.5), 2),
                "temperature_c": round(random.uniform(28, 32), 2),
                "ammonia_ppm": round(random.uniform(0.5, 1.0) if is_warning else random.uniform(0.01, 0.25), 3),
                "nitrite_ppm": round(random.uniform(0.1, 0.3) if is_warning else random.uniform(0.01, 0.15), 3),
                "salinity_ppt": random.randint(15, 25)
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
        joblib.dump(model_data, MODEL_FILE)
        print(f"💾 New health model saved to '{MODEL_FILE}'.\n")

    print(f"[INFO] Loading model '{MODEL_FILE}'...")
    model_data = joblib.load(MODEL_FILE)
    model_pipeline = model_data['pipeline']
    print("✅ Model loaded successfully.")


def run_realtime_monitoring():
    """Background thread function to continuously generate and store logs."""
    log_counter = int(time.time())
    while True:
        try:
            active_crops = list(main_db["crops"].find({"status": "active"}, {"crop_id": 1, "_id": 0}))
            crop_ids = [doc['crop_id'] for doc in active_crops]
            
            if not crop_ids:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] No active crops found. Waiting...")
            else:
                print(f"\n--- Generating logs for {len(crop_ids)} active crops ---")
                logs_to_insert = []
                for crop_id in crop_ids:
                    log_counter += 1
                    new_log = {
                        "log_id": f"WQ_LOG{log_counter:06d}", "crop_id": crop_id, "timestamp": datetime.now(),
                        "dissolved_oxygen_mg_l": round(random.uniform(4.0, 7.5), 2),
                        "ph": round(random.uniform(7.5, 8.8), 2),
                        "temperature_c": round(random.uniform(28.0, 32.0), 2),
                        "ammonia_ppm": round(random.uniform(0.01, 0.7), 3),
                        "nitrite_ppm": round(random.uniform(0.01, 0.2), 3),
                        "salinity_ppt": random.randint(15, 25),
                        "remarks": "Simulated real-time sensor log."
                    }
                    logs_to_insert.append(new_log)
                    print(f"✔  Generated log for {crop_id}")
                
                if logs_to_insert:
                    log_db[LOG_COLLECTION_NAME].insert_many(logs_to_insert)
                    print(f"✅ Stored {len(logs_to_insert)} new logs in '{LOG_DB_NAME}'")

        except Exception as e:
            print(f"❌ Error during simulation cycle: {e}")
        
        time.sleep(SIMULATION_INTERVAL_SECONDS)

# --- 3. Prediction and Report Generation ---

def get_warning_details(record):
    """Generates a reason and action for a warning prediction."""
    if record.get('dissolved_oxygen_mg_l', 7) < 4.5: return "Low Dissolved Oxygen", "Start all aerators immediately."
    if record.get('ammonia_ppm', 0) > 0.5: return "High Ammonia Levels", "Reduce feed and prepare for water exchange."
    if record.get('ph', 8) < 7.5: return "Low pH (Acidic)", "Prepare to add agricultural lime."
    if record.get('ph', 8) > 8.8: return "High pH (Alkaline)", "Prepare for a partial water exchange."
    return "Multiple parameters out of range", "Perform a full diagnostic check."

def generate_health_report(log_record):
    """Uses the ML model to predict status and generate a full report."""
    df = pd.DataFrame([log_record])
    X_new = df[REALTIME_HEALTH_FEATURES]
    
    prediction = model_pipeline.predict(X_new)[0]
    
    report = { "predicted_status": prediction, "reason": "N/A", "recommended_action": "No action required." }
    
    if prediction == "Warning":
        reason, action = get_warning_details(log_record)
        report["reason"] = reason
        report["recommended_action"] = action

    return report

# --- 4. Flask API Endpoints ---

@app.route('/')
def home():
    """A simple welcome message for the root URL."""
    return "<h1>AquaKranthi Backend is Running</h1>"

@app.route('/api/active_crops')
def get_active_crops_endpoint():
    """Returns a list of all active crop IDs from the main database."""
    try:
        active_crops = list(main_db["crops"].find({"status": "active"}, {"crop_id": 1, "_id": 0}))
        return jsonify([doc['crop_id'] for doc in active_crops])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<crop_id>')
def get_crop_status(crop_id):
    """Fetches the latest log for a crop, predicts its health, and returns a report."""
    try:
        latest_log = log_db[LOG_COLLECTION_NAME].find_one(
            {"crop_id": crop_id},
            sort=[("timestamp", -1)]
        )
        if not latest_log:
            return jsonify({"error": "No recent logs found for this crop."}), 404
            
        health_report = generate_health_report(latest_log)
        
        # Add harvest data if available
        harvest_data = main_db["harvests"].find_one({"crop_id": crop_id})
        if harvest_data:
            health_report["total_yield_kg"] = harvest_data.get("total_yield_kg", "N/A")
            health_report["avg_body_weight_g"] = harvest_data.get("average_body_weight_g", "N/A")
            health_report["survival_rate_percent"] = harvest_data.get("survival_rate_percent", "N/A")
        
        health_report["report_timestamp"] = datetime.now(timezone.utc).isoformat()
        return jsonify(health_report)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 5. Main Execution Block ---
if _name_ == '_main_':
    if not MONGO_URI or "viswesg51" not in MONGO_URI: # Basic check
       raise ValueError("FATAL: MONGO_URI is not set or is incorrect. Please update the script.")
       
    if connect_to_db():
        # Check for command-line arguments
        if len(sys.argv) > 1 and sys.argv[1] == '--seed':
            seed_database()
        
        create_and_load_model()
        
        simulation_thread = threading.Thread(target=run_realtime_monitoring, daemon=True)
        simulation_thread.start()
        
        print("\n🚀 Starting Flask Server...")
        # use_reloader=False is important to prevent the background thread from running twice
        app.run(debug=True, port=5000, use_reloader=False)