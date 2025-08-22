import pymongo
from faker import Faker
from datetime import datetime, timedelta
import random

# --- Configuration ---
MONGO_URI = "mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/" # <-- Replace with your MongoDB URI if different
DB_NAME = "aqua_management_db"

NUM_FARMS = 5
AVG_PONDS_PER_FARM = 4
NUM_TECHNICIANS = 4
NUM_HATCHERIES = 3
NUM_CROPS = 15 # Total active/harvested crops across all farms
NUM_LOGS_PER_CROP = 200 # Average number of log entries per crop cycle

# --- Predefined Data for Realism (Andhra Pradesh Context) ---
FARM_NAMES = ["Sri Venkateswara Aqua", "Godavari Prawns", "Coastal Aqua Tech", "Krishna Delta Farms", "Royal Marine Exports"]
SPECIES = ["L. vannamei", "P. monodon"]
HATCHERY_NAMES = ["BMR Hatcheries", "Devi Sea Foods Hatchery", "CP Aqua Hatchery"]
FEED_BRANDS = ["Avanti Feeds", "CP Aqua", "Growel Feeds", "Nexus Feeds"]
COMMON_SYMPTOMS = ["None", "White Spot (WSSV)", "Loose Shell", "White Gut", "EHP", "Reduced Feeding"]
COMMON_TREATMENTS = ["None", "Probiotic Application", "Zeolite Application", "Mineral Mix Dosing", "Reduce Feeding"]

# --- Helper Functions ---
def generate_id(prefix, num, length=4):
    """Generates a formatted ID string, e.g., FARM0001."""
    return f"{prefix}{num:0{length}d}"

def main():
    """Main function to generate and insert mock aqua farm data."""
    # --- 1. Setup MongoDB Connection ---
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    fake = Faker('en_IN') # Use Indian locale for names/phones

    # Get collection objects
    collections = {
        "farms": db["farms"],
        "ponds": db["ponds"],
        "technicians": db["technicians"],
        "hatcheries": db["hatcheries"],
        "crops": db["crops"],
        "stocking_details": db["stocking_details"],
        "water_quality_logs": db["water_quality_logs"],
        "feed_logs": db["feed_logs"],
        "health_checks": db["health_checks"],
        "harvests": db["harvests"],
    }

    # Clear all existing data
    print("Clearing existing data from collections...")
    for name, col in collections.items():
        col.delete_many({})
        print(f"  - Cleared '{name}' collection.")

    # --- 2. Generate Data in Memory ---
    print("\nGenerating mock data in memory...")

    # Independent Data: Technicians & Hatcheries
    technicians_data = [{
        "technician_id": generate_id("TECH", i),
        "name": fake.name(),
        "email": fake.email(),
        "phone": f"+91 {random.randint(6000000000, 9999999999)}", # <-- CHANGED
    } for i in range(1, NUM_TECHNICIANS + 1)]
    all_tech_ids = [t["technician_id"] for t in technicians_data]

    hatcheries_data = [{
        "hatchery_id": generate_id("HATCH", i),
        "hatchery_name": random.choice(HATCHERY_NAMES),
        "location": fake.city() + ", AP",
        "certification_details": "Coastal Aquaculture Authority (CAA) Certified"
    } for i in range(1, NUM_HATCHERIES + 1)]
    all_hatchery_ids = [h["hatchery_id"] for h in hatcheries_data]

    # Farms and Ponds
    farms_data, ponds_data = [], []
    all_pond_ids = []
    pond_counter = 1
    for i in range(1, NUM_FARMS + 1):
        farm_id = generate_id("FARM", i)
        farms_data.append({
            "farm_id": farm_id,
            "farm_name": random.choice(FARM_NAMES),
            "owner_name": fake.name(),
            "location": "Near " + fake.city() + ", West Godavari, AP",
            "phone_number": f"+91 {random.randint(6000000000, 9999999999)}", # <-- CHANGED
            "total_area_hectares": round(random.uniform(5.0, 20.0), 2)
        })
        for _ in range(random.randint(2, AVG_PONDS_PER_FARM + 2)):
            pond_id = generate_id("POND", pond_counter)
            ponds_data.append({
                "pond_id": pond_id,
                "farm_id": farm_id,
                "pond_number": f"P{pond_counter}",
                "area_hectares": round(random.uniform(0.8, 1.2), 2),
                "pond_type": random.choice(["earthen", "lined"]),
                "max_depth_meters": round(random.uniform(1.5, 1.8), 2)
            })
            all_pond_ids.append(pond_id)
            pond_counter += 1

    # Crops and their associated details
    crops_data, stocking_data, harvests_data = [], [], []
    water_logs_data, feed_logs_data, health_checks_data = [], [], []
    log_id_counter = 1
    
    for i in range(1, NUM_CROPS + 1):
        crop_id = generate_id("CROP", i)
        stocking_date = fake.date_time_between(start_date='-1y', end_date='-4M')
        status = random.choices(["harvested", "active", "failed"], [0.7, 0.2, 0.1])[0]
        
        crops_data.append({
            "crop_id": crop_id,
            "pond_id": random.choice(all_pond_ids),
            "technician_id": random.choice(all_tech_ids),
            "species": random.choice(SPECIES),
            "stocking_date": stocking_date,
            "status": status,
            "created_at": stocking_date - timedelta(days=2)
        })

        seed_count = random.randint(80000, 150000)
        stocking_data.append({
            "crop_id": crop_id,
            "hatchery_id": random.choice(all_hatchery_ids),
            "seed_count": seed_count,
            "seed_size_pl": random.randint(12, 18),
            "seed_cost_per_pl": round(random.uniform(0.40, 0.60), 2)
        })

        # Generate logs for this crop
        current_timestamp = stocking_date
        doc = 0 # Days of Culture
        while current_timestamp < datetime.now() and doc < 120 : # Max 120 days of culture
            current_timestamp += timedelta(hours=random.randint(10, 14)) # Approx 2 logs per day
            if status == "active" and current_timestamp > datetime.now(): break
                
            # Water Quality Logs
            water_logs_data.append({
                "log_id": log_id_counter, "crop_id": crop_id, "timestamp": current_timestamp,
                "dissolved_oxygen_mg_l": round(random.uniform(4.5, 7.0), 2),
                "ph": round(random.uniform(7.8, 8.5), 2),
                "temperature_c": round(random.uniform(28.5, 31.5), 2),
                "ammonia_ppm": round(random.uniform(0.1, 0.8), 2),
                "nitrite_ppm": round(random.uniform(0.01, 0.05), 2),
                "salinity_ppt": round(random.uniform(12.0, 20.0), 1),
                "secchi_disk_cm": random.randint(30, 45),
                "water_level_percent": random.randint(90, 100),
                "remarks": "Parameters normal."
            })
            log_id_counter += 1

            # Feed Logs (once per day)
            if current_timestamp.day != (current_timestamp - timedelta(hours=12)).day:
                doc += 1
                estimated_biomass = (seed_count * 0.85) * (doc * 0.25) / 1000 # Rough estimation in kg
                feed_logs_data.append({
                    "feed_log_id": len(feed_logs_data) + 1, "crop_id": crop_id, "timestamp": current_timestamp,
                    "feed_brand": random.choice(FEED_BRANDS), "feed_type": "Grower",
                    "quantity_kg": round(estimated_biomass * random.uniform(0.03, 0.05), 2), # 3-5% of biomass
                    "estimated_biomass_kg": round(estimated_biomass, 2)
                })

            # Health Checks (every 2-3 days)
            if doc > 0 and doc % 3 == 0 and current_timestamp.day != (current_timestamp - timedelta(hours=12)).day:
                 health_checks_data.append({
                    "check_id": len(health_checks_data) + 1,
                    "crop_id": crop_id,
                    "check_date": current_timestamp,
                    "observation": "Check tray clear, good activity.",
                    "symptoms_noted": random.choices(COMMON_SYMPTOMS, [0.9, 0.02, 0.02, 0.02, 0.02, 0.02])[0],
                    "treatment_applied": "None",
                    "mortality_count_est": random.randint(10, 50)
                })

        # Harvest Data for harvested/failed crops
        if status in ["harvested", "failed"]:
            harvest_date = stocking_date + timedelta(days=random.randint(80, 120))
            is_success = status == "harvested"
            survival_rate = round(random.uniform(0.75, 0.95), 2) if is_success else round(random.uniform(0.10, 0.50), 2)
            total_yield = (seed_count * survival_rate * random.uniform(20, 30)) / 1000 # in kgs
            abw = (total_yield / (seed_count * survival_rate)) * 1000 if (seed_count * survival_rate) > 0 else 0 # in grams
            total_cost = (seed_count * 0.50) + (total_yield * 150) # Seed cost + rough feed/elec cost
            total_revenue = total_yield * random.uniform(250, 400) if is_success else 0

            harvests_data.append({
                "crop_id": crop_id, "harvest_date": harvest_date,
                "total_yield_kg": round(total_yield, 2),
                "average_body_weight_g": round(abw, 2),
                "survival_rate_percent": survival_rate * 100,
                "final_fcr": round(random.uniform(1.3, 1.8), 2),
                "sale_price_per_kg": round(total_revenue / total_yield, 2) if total_yield > 0 else 0,
                "total_revenue": round(total_revenue, 2),
                "total_cost": round(total_cost, 2),
                "profit_or_loss": round(total_revenue - total_cost, 2)
            })
    
    print("Data generation complete.")

    # --- 3. Insert Data into MongoDB ---
    print("\nInserting data into MongoDB collections...")
    
    data_to_insert = {
        "technicians": technicians_data,
        "hatcheries": hatcheries_data,
        "farms": farms_data,
        "ponds": ponds_data,
        "crops": crops_data,
        "stocking_details": stocking_data,
        "water_quality_logs": water_logs_data,
        "feed_logs": feed_logs_data,
        "health_checks": health_checks_data,
        "harvests": harvests_data,
    }

    for name, data in data_to_insert.items():
        if data:
            collections[name].insert_many(data)
            print(f"  - Inserted {len(data)} documents into '{name}'.")
        else:
            print(f"  - No data to insert for '{name}'.")
            
    print("\n✅ Mock data insertion for Aqua Farms complete!")
    client.close()

if __name__ == "__main__":
    main()