import pymongo
from datetime import datetime
import random
import time
import os

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/")
SIMULATION_INTERVAL_SECONDS = 300  # 5 minutes
MAIN_DB_NAME = "aqua_management_db"
LOG_DB_NAME = "aqua_model_prediction"
LOG_COLLECTION_NAME = "realtime_water_logs"

# The name of the file that will trigger an abnormal event
TRIGGER_FILE = "trigger_abnormal.txt"

# --- Real-Time Data Generation ---
def generate_single_log(crop_id, log_counter, timestamp):
    """
    Generates a single, realistic water quality log,
    with a chance of creating varied abnormal data.
    """
    force_abnormal = False
    if os.path.exists(TRIGGER_FILE):
        force_abnormal = True
        print(f"    -> 🔥 Trigger file detected! Forcing abnormal event for {crop_id}...")
        try:
            os.remove(TRIGGER_FILE)
        except Exception as e:
            print(f"    -> [WARN] Could not remove trigger file: {e}")

    is_abnormal = force_abnormal or (random.random() < 0.20) # Increased chance to 20%
    
    log_data = {
        "log_id": f"WQ_LOG{log_counter:06d}", "crop_id": crop_id, "timestamp": timestamp,
        "dissolved_oxygen_mg_l": round(random.uniform(5.0, 7.0), 2),
        "ph": round(random.uniform(7.8, 8.5), 2),
        "temperature_c": round(random.uniform(28.0, 32.0), 2),
        "ammonia_ppm": round(random.uniform(0.01, 0.25), 3),
        "nitrite_ppm": round(random.uniform(0.01, 0.15), 3),
        "salinity_ppt": random.randint(15, 25),
        "remarks": "Simulated real-time sensor log."
    }

    if is_abnormal:
        # NEW: Expanded list of possible unhealthy scenarios
        abnormal_type = random.choice(['low_do', 'high_ammonia', 'ph_imbalance', 'high_nitrite', 'temp_stress'])
        print(f"    -> 🚨 Generating ABNORMAL data for {crop_id}: ", end="")
        
        if abnormal_type == 'low_do':
            log_data['dissolved_oxygen_mg_l'] = round(random.uniform(2.5, 4.0), 2)
            log_data['remarks'] = "Unhealthy State: Low Dissolved Oxygen Detected."
            print("Low DO")
            
        elif abnormal_type == 'high_ammonia':
            log_data['ammonia_ppm'] = round(random.uniform(0.6, 1.2), 3)
            log_data['remarks'] = "Unhealthy State: High Ammonia Detected."
            print("High Ammonia")

        elif abnormal_type == 'ph_imbalance':
            log_data['ph'] = random.choice([round(random.uniform(6.5, 7.2), 2), round(random.uniform(9.0, 9.8), 2)])
            log_data['remarks'] = "Unhealthy State: pH Imbalance Detected."
            print("pH Imbalance")
            
        elif abnormal_type == 'high_nitrite':
            log_data['nitrite_ppm'] = round(random.uniform(0.5, 1.5), 3)
            log_data['remarks'] = "Unhealthy State: High Nitrite Detected."
            print("High Nitrite")

        elif abnormal_type == 'temp_stress':
            log_data['temperature_c'] = random.choice([round(random.uniform(24.0, 26.0), 2), round(random.uniform(34.0, 36.0), 2)])
            log_data['remarks'] = "Unhealthy State: Temperature Stress Detected."
            print("Temperature Stress")
            
    return log_data

def run_realtime_monitoring(client):
    """
    Reads active crops from the main DB and writes new logs to the log DB.
    """
    main_db = client[MAIN_DB_NAME]
    log_db = client[LOG_DB_NAME]
    
    print(f"\n[INFO] Reading active crops from: '{MAIN_DB_NAME}'")
    print(f"[INFO] Writing new logs to: '{LOG_DB_NAME}.{LOG_COLLECTION_NAME}'")
    print(f"[INFO] To force an unhealthy event, create a file named '{TRIGGER_FILE}' in this folder.")
    print(f"Will generate new data every {SIMULATION_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    log_counter = int(time.time())
    while True:
        try:
            active_crops = list(main_db["crops"].find({"status": "Ongoing"}, {"crop_id": 1, "_id": 0}))
            crop_ids = [doc['crop_id'] for doc in active_crops]
        except Exception as e:
            print(f"❌ Error reading from '{MAIN_DB_NAME}': {e}")
            time.sleep(60)
            continue
        
        if not crop_ids:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] No active crops found. Waiting...")
            time.sleep(SIMULATION_INTERVAL_SECONDS)
            continue
            
        print(f"\n--- Starting data generation cycle at {datetime.now().strftime('%H:%M:%S')} for {len(crop_ids)} crops ---")
        
        logs_to_insert = []
        for crop_id in crop_ids:
            log_counter += 1
            timestamp = datetime.now()
            new_log = generate_single_log(crop_id, log_counter, timestamp)
            logs_to_insert.append(new_log)
            print(f"✔️  Generated log for {crop_id}")

        if logs_to_insert:
            try:
                log_db[LOG_COLLECTION_NAME].insert_many(logs_to_insert)
                print(f"✅ Stored {len(logs_to_insert)} new logs in '{LOG_DB_NAME}'")
            except Exception as e:
                print(f"❌ Error writing to '{LOG_DB_NAME}': {e}")
        
        print(f"\n-- Cycle complete. Waiting for {SIMULATION_INTERVAL_SECONDS} seconds... --")
        time.sleep(SIMULATION_INTERVAL_SECONDS)

# --- Main Execution Block ---
if __name__ == "__main__":
    if not MONGO_URI:
        raise ValueError("FATAL: MONGO_URI environment variable not set.")
        
    try:
        client = pymongo.MongoClient(MONGO_URI)
        client.admin.command('ping')
        print("✅ Database connection successful.")
    except Exception as e:
        print(f"❌ FATAL: Could not connect to MongoDB. Error: {e}")
        exit()

    try:
        run_realtime_monitoring(client)
    except KeyboardInterrupt:
        print("\n\n🛑 Simulation stopped by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        client.close()
        print("🔌 MongoDB connection closed.")