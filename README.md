 🍯 HoneyChain

# AI & Blockchain-Based Honey Traceability and Smart Beekeeping System

HoneyChain is a smart system that helps track honey from the beekeeper to the customer. It combines **Blockchain, AI/ML, QR Code Verification, SQLite, and Streamlit**.

# 🎯 Problem

Customers may not know where their honey came from or what happened to it before reaching them.
Beekeepers and honey businesses also need a simple way to manage and track honey batches.

# 💡 Solution

HoneyChain gives every honey batch a unique ID and records its journey:

**Harvest → Processing → Quality Check → Packaging → Distribution**

Customers can scan a QR code to view the batch information and verify its recorded journey.

## Features

- 👨‍🌾 Beekeeper Management
- 🐝 Hive Monitoring
- 🍯 Honey Batch Management
- 🔗 Blockchain-Based Traceability
- 📱 QR Code Verification
- 🤖 Honey Production Prediction
- 🐝 Hive Health Prediction
- 📊 Streamlit Dashboard
- 🗄️ SQLite Database

##  How It Works

text
Beekeeper
   ↓
Hive
   ↓
Honey Batch
   ↓
Unique Batch ID
   ↓
Blockchain Record
   ↓
QR Code
   ↓
Customer Verification

## 🔗 Blockchain
The honey journey is recorded through:

Genesis Block
     ↓
Harvest
     ↓
Processing
     ↓
Quality Check
     ↓
Packaging
     ↓
Distribution
The blockchain uses hashes to make changes to the recorded chain detectable.


## 📱 QR Verification
Each honey batch gets a QR code containing a verification link.
When the customer scans it, the system displays:

Batch ID
Honey Type
Quantity
Harvest Date
Origin
Status
Supply Chain Journey
Blockchain Integrity Status


## 🤖 AI/ML
HoneyChain uses Machine Learning for:
Honey Production Prediction

Uses factors such as:
Temperature
Humidity
Rainfall
Hive Weight
Colony Strength
Flower Availability

## Hive Health Prediction
Uses factors such as:

Temperature
Humidity
Colony Strength
Varroa Level
Food Availability
Bee Population

The output identifies the hive as Healthy or At Risk.

Note: The current ML models use synthetic/generated data for prototype demonstration.

## 🛠️ Technologies Used
Python
Streamlit
Machine Learning
Scikit-learn
Blockchain
SQLite
Pandas
NumPy
Joblib
QR Code
Plotly

📁 Project Structure
HoneyChain-Traceability/
│
├── app/
│   ├── app.py
│   └── app_backup.py
│
├── data/
│   └── honeychain.db
│
├── models/
│   ├── production_model.pkl
│   └── hive_health_model.pkl
│
├── qr_codes/
│
└── README.md

## 👥 Who Can Use It?
👨‍🌾 Beekeepers – manage hives and honey batches
🏭 Honey Businesses – track honey through the supply chain
🚚 Distributors – track batch movement
👤 Customers – verify honey information using QR codes

## 🎯 Project Goal
To make honey traceability easier by giving every honey batch a digital identity, tracking its journey, enabling QR-based verification, and providing AI-powered insights.
