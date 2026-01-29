# Flight Delay Prediction (Brazil – ANAC VRA)

This project builds an end-to-end data pipeline to **predict whether a flight will be delayed by 15 minutes or more before departure**, using real operational data from Brazil’s civil aviation authority (ANAC).

The focus is on **reproducible analytics and decision-ready modeling**, not Kaggle-style notebooks.

---

## Problem Statement

Given information available **before departure** (schedule, airport, airline, historical behavior), predict:

> Will this flight depart **≥ 15 minutes late**?

This mirrors real operational and planning use cases (staffing, gate allocation, risk monitoring).

---

## Data Source

**ANAC – Voo Regular Ativo (VRA)**  
Monthly open datasets containing scheduled vs actual flight times and cancellations.

- Granularity: one row per flight leg
- Scale: appendable to millions of rows
- Region: Brazil (domestic + international)

---

## Target Definition

Binary classification:

- `y_delayed_15 = 1` if departure delay ≥ 15 minutes
- `y_delayed_15 = 0` otherwise

Cancellations are excluded from the first model.

## Project Structure

```text
flight-delay/
├── sql/
│   ├── 10_stages.sql        # Cleaning, typing, delay calculation
│   └── 20_features.sql     # Feature engineering + model-ready view
├── src/
│   ├── ingest_local_vra.py # Load monthly CSV into DuckDB
│   └── train_delay_model.py# Train & evaluate logistic regression
├── data/                   # Raw VRA files (ignored)
├── models/                 # Saved pipelines & metrics (ignored)
├── exports/                # BI-ready outputs (ignored)
└── flight_delay.duckdb     # Local DuckDB database (ignored)


---

## Feature Engineering (SQL-first)

Features are built entirely in SQL and exposed via a single model-ready view:

**`v_feature_model`**

Feature groups:
- Time features: hour, day of week, month
- Categorical: airline, origin, destination
- Historical aggregates:
  - airport delay rate
  - route delay rate
  - airline delay rate
  - airport × hour delay rate
- Frequency signals (counts per group)

All features are available **before departure**.

---

## Modeling Approach

- Model: **Logistic Regression**
- Pipeline:
  - Imputation (median / most-frequent)
  - One-hot encoding for categorical variables
  - Class-balanced loss
- Train/test split: **time-based** (no leakage)
- Metrics:
  - **PR-AUC** (primary, due to class imbalance)
  - ROC-AUC
  - F1-optimized decision threshold

---

## Results (Baseline)

On a test set with ~20% delayed flights:

- ROC-AUC ≈ **0.69**
- PR-AUC ≈ **0.41**
- Recall ≈ **0.63** at best F1 threshold

This shows meaningful predictive signal using schedule + historical behavior only.

---

## How to Run

```bash
# 1. Load one month of VRA data
python src/ingest_local_vra.py --csv data/raw/VRA_YYYYMM.csv

# 2. Build feature views
python src/build_sql.py

# 3. Train the model
python src/train_delay_model.py
