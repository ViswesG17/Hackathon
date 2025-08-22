from flask import Flask, jsonify
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timedelta, timezone
import os
from flask_cors import CORS

# Initialize the Flask app
app = Flask(__name__)
# Enable CORS to allow the HTML file to make requests to this API
CORS(app)

# --- MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/")

# Connect to your databases
client = MongoClient(MONGO_URI)
main_db = client["aqua_management_db"]
prediction_db = client["aqua_model_prediction"]


# --- API Endpoint 1: Get a list of all ponds ---
@app.route("/api/ponds")
def get_all_ponds():
    """Fetches all ponds with their farm names to populate the dropdown."""
    try:
        # This is an aggregation pipeline to join ponds with their farms
        pipeline = [
            {
                "$lookup": {
                    "from": "farms",
                    "localField": "farm_id",
                    "foreignField": "farm_id",
                    "as": "farm_info"
                }
            },
            {
                "$unwind": "$farm_info"
            },
            {
                "$project": {
                    "_id": 0,
                    "pond_id": 1,
                    "farm_name": "$farm_info.farm_name"
                }
            }
        ]
        ponds = list(main_db.ponds.aggregate(pipeline))
        return jsonify(ponds)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- API Endpoint 2: Get dashboard data for a specific pond ---
@app.route("/api/dashboard/<string:pond_id>")
def get_dashboard_data(pond_id):
    """Gathers all data needed for the dashboard for a specific pond."""
    try:
        # Find the current "Ongoing" crop for the requested pond
        active_crop = main_db.crops.find_one({"pond_id": pond_id, "status": "Ongoing"})
        if not active_crop:
            return jsonify({"error": f"No active crop found for {pond_id}"}), 404
        
        active_crop_id = active_crop['crop_id']

        # Get the latest health report for this crop
        health_report = prediction_db.consolidated_health_reports.find_one(
            {"crop_id": active_crop_id}, 
            sort=[('report_timestamp', DESCENDING)]
        )

        # Get pond and farm details
        pond_details = main_db.ponds.find_one({"pond_id": pond_id})
        farm_details = main_db.farms.find_one({"farm_id": pond_details['farm_id']})

        # Get the latest harvest data for this pond (for historical context)
        latest_harvest = main_db.harvests.find_one(
            {"crop_id": {"$in": [c['crop_id'] for c in main_db.crops.find({"pond_id": pond_id})]}},
            sort=[('harvest_date', DESCENDING)]
        )

        # Get water quality data for the charts (last 30 minutes for the active crop)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=30)
        water_logs = list(prediction_db.realtime_water_logs.find(
            {"crop_id": active_crop_id, "timestamp": {"$gte": start_time}},
            {"_id": 0, "timestamp": 1, "dissolved_oxygen_mg_l": 1, "ph": 1, "temperature_c": 1, "ammonia_ppm": 1},
            sort=[('timestamp', DESCENDING)]
        ))

        # Assemble all data into a single, clean JSON response
        dashboard_data = {
            "pond_id": pond_id,
            "farm_name": farm_details.get('farm_name', 'N/A'),
            "pond_status": health_report.get('status', 'Unknown') if health_report else 'Awaiting Report',
            "recommended_action": health_report.get('recommended_action', 'N/A') if health_report else 'N/A',
            "report_timestamp": health_report.get('report_timestamp', 'N/A') if health_report else 'N/A',
            "latest_harvest": {
                "total_yield_kg": latest_harvest.get('total_yield_kg', 0) if latest_harvest else 0,
                "average_body_weight_g": latest_harvest.get('average_body_weight_g', 0) if latest_harvest else 0,
                "survival_rate_percent": latest_harvest.get('survival_rate_percent', 0) if latest_harvest else 0
            },
            "water_quality_logs": water_logs
        }
        
        return jsonify(dashboard_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Main Execution Block ---
if __name__ == '__main__':
    app.run(debug=True, port=5001) # Run on a different port to avoid conflicts
