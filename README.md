Aqua-Sense: AI-Powered Aquaculture Health Monitoring System
<!-- Replace with a URL to your dashboard screenshot -->
📖 Overview
Aqua-Sense is a full-stack web application designed to transform aquaculture farm management from a reactive, manual process into a proactive, data-driven operation. By simulating real-time sensor data and leveraging a machine learning model, this system predicts the health status of aquaculture ponds, identifies potential issues before they become critical, and provides actionable recommendations to farm managers.
The core mission of this project is to reduce financial risk, improve operational efficiency, and increase profitability in the high-stakes aquaculture industry.
✨ Key Features
Real-Time Data Simulation: A Python script (5minsdata.py) continuously generates realistic water quality data every 5 minutes, simulating a live IoT sensor network.
Machine Learning Predictions: A pre-trained Random Forest model (aqua_model.pkl) analyzes the live data stream to predict pond health status ("Healthy" or "Warning").
Automated Health Reports: A script (realtimepre.py) runs on-demand to analyze the latest data, aggregate results, and save a consolidated health summary to the database.
Backend API: A secure Flask API (app.py or dashboard.py) acts as the bridge between the database and the user interface, providing clean data endpoints.
Interactive Web Dashboard: A user-friendly frontend (dashboard.html) that visualizes all critical information, including live charts, pond metrics, and the final health prediction with recommended actions.
🛠️ Technology Stack
Backend: Python, Flask, Flask-Cors
Database: MongoDB Atlas
Machine Learning: Scikit-learn, Pandas
Frontend: HTML, Tailwind CSS, Chart.js
Data Simulation: Faker
📁 File Structure
Based on your project directory, here is an explanation of the key files:
/
├── 5minsdata.py              # Runs continuously to generate and store real-time sensor data.
├── app.py / dashboard.py     # The Flask Backend API server.
├── aqua_model.pkl            # The pre-trained machine learning model for health prediction.
├── aquamock.py               # Script to generate the initial mock database.
├── aquamodel.py              # Script to train the machine learning model.
├── dashboard.html            # The main user interface file.
├── realtimepre.py            # Script to generate the consolidated health report on demand.
└── README.md                 # This file.


🚀 Getting Started
Follow these steps to set up and run the project on your local machine.
1. Prerequisites
Python 3.8+
MongoDB Atlas account and a connection string
2. Installation & Setup
a. Clone the repository (if applicable) or ensure all files are in one folder.
b. Install Python dependencies:
pip install pandas pymongo scikit-learn Flask Flask-Cors joblib faker


c. Set the Environment Variable:
The application requires your MongoDB connection string to be set as an environment variable for security.
In Windows PowerShell:
$env:MONGO_URI="mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/"


In macOS or Linux:
export MONGO_URI="mongodb+srv://viswesg51:31606021@cluster0.eglpin3.mongodb.net/"


3. Populate the Initial Database
If your database is empty, you need to populate it with the initial farm and crop data.
Run the mock data script one time:
python aquamock.py

This will create the necessary farms, ponds, and crops, including some with an "Ongoing" status.
▶️ How to Run the Full Application
To see the complete end-to-end system in action, you need to run three components simultaneously in three separate terminal windows.
Terminal 1: Start the Real-Time Data Simulation
This script will continuously feed your database with new sensor data.
python 5minsdata.py


Terminal 2: Start the Backend API Server
This script provides the data to your dashboard.
# Make sure your MONGO_URI is set in this terminal
python app.py  # Or python dashboard.py


Terminal 3: Generate a Health Report (Optional but Recommended)
This script analyzes the latest data and creates the summary that the dashboard displays. Run this script once after the data simulation has been running for a minute.
# Make sure your MONGO_URI is set in this terminal
python realtimepre.py


Finally: Open the User Interface
Open the dashboard.html file in your web browser. It will connect to the running API and display the live data from your MongoDB collections. The dashboard will automatically refresh every 30 seconds.
