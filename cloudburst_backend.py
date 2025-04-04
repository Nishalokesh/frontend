from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import joblib
import numpy as np
import os
import traceback
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app,origins=["https://frontdeployment.netlify.app"])

# Load trained model and scaler
rf_model = joblib.load("cloudburst_rf_model.pkl")
scaler = joblib.load("scaler.pkl")

# Database Configuration (Using Render DB Credentials)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cloudburst_db_user:MWzRywc74qezZFfvbOdvViBn2ytb6MXV@dpg-cvj5vnuuk2gs73b26sv0-a/cloudburst_db")

# Parse the database URL
db_url = urlparse(DATABASE_URL)

DB_CONFIG = {
    "dbname": db_url.path[1:],  # Extract database name
    "user": db_url.username,
    "password": db_url.password,
    "host": db_url.hostname,
    "port": db_url.port,
    "sslmode": "require"  # Important for Render DB
}

def connect_db():
   try:
       conn = psycopg2.connect(**DB_CONFIG)
       return conn
   except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

def test_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(" Database connected successfully!")
        conn.close()
    except Exception as e:
        print(f" Database Connection Error: {e}")

@app.route("/")
def home():
    return "Cloudburst Prediction API is running!"

@app.route("/predict", methods=["GET"])
def predict():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "City parameter is required"}), 400
    
    try:
        conn = connect_db()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cur = conn.cursor()
        cur.execute("SELECT temperature, humidity, pressure, wind_speed FROM weather WHERE city = %s", (city,))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "City data not found"}), 404
        
        # Debugging: Print the extracted data
        print(f"Extracted Data for {city}: {row}")

        # Prepare data for prediction
        input_data = np.array([row])
        input_scaled = scaler.transform(input_data)

        # Debugging: Print scaled data
        print(f"Scaled Features: {input_scaled}")

        # Make prediction
        prediction = rf_model.predict(input_scaled)[0]
        risk_level = "High Risk" if prediction == 1 else "Low Risk"

        # Debugging: Print prediction output
        print(f"Prediction for {city}: Risk Level = {risk_level}, Probability = {prediction}")

        return jsonify({"city": city, "risk_level": risk_level, "probability": int(prediction)})
    except Exception as e:
        error_message = traceback.format_exc()  # Get full error
        print(f"Error: {error_message}")  # Logs error in Render
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
