import os
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from database import get_connection


CHART_FOLDER = os.path.join("static", "charts")
os.makedirs(CHART_FOLDER, exist_ok=True)


def load_accidents():
    connection = get_connection()
    try:
        query = """
            SELECT
                a.accident_id,
                a.accident_datetime,
                l.region,
                l.road_name,
                a.vehicle_type,
                a.severity,
                a.weather,
                a.cause_of_accident
            FROM accidents a
            JOIN locations l
                ON a.location_id = l.location_id
            ORDER BY a.accident_datetime DESC
        """
        return pd.read_sql(query, connection)
    finally:
        connection.close()


def get_accident_summary():
    df = load_accidents()

    if df.empty:
        return {
            "total_accidents": 0,
            "most_affected_region": "No data",
            "most_common_vehicle": "No data",
            "busiest_hour": "No data",
            "severity_counts": {},
            "severity_percentages": {}
        }

    df["accident_datetime"] = pd.to_datetime(
        df["accident_datetime"], errors="coerce"
    )

    total = len(df)

    region_counts = df["region"].dropna().value_counts()
    vehicle_counts = df["vehicle_type"].dropna().value_counts()

    valid_times = df.dropna(subset=["accident_datetime"])
    hour_counts = valid_times["accident_datetime"].dt.hour.value_counts()

    severity_counts = (
        df["severity"].fillna("Unknown").value_counts().to_dict()
    )

    severity_percentages = {
        severity: round(count / total * 100, 1)
        for severity, count in severity_counts.items()
    }

    return {
        "total_accidents": total,
        "most_affected_region": (
            region_counts.idxmax() if not region_counts.empty else "No data"
        ),
        "most_common_vehicle": (
            vehicle_counts.idxmax() if not vehicle_counts.empty else "No data"
        ),
        "busiest_hour": (
            f"{hour_counts.idxmax()}:00"
            if not hour_counts.empty else "No data"
        ),
        "severity_counts": severity_counts,
        "severity_percentages": severity_percentages
    }


def analyze_accidents():
    df = load_accidents()

    if df.empty:
        print("No accident records available for analysis.")
        return

    df["accident_datetime"] = pd.to_datetime(
        df["accident_datetime"], errors="coerce"
    )

    # 1. Accidents by hour
    hourly = (
        df.dropna(subset=["accident_datetime"])
        .groupby(df["accident_datetime"].dt.hour)
        .size()
    )

    plt.figure(figsize=(9, 5))
    hourly.plot(kind="bar")
    plt.title("Accidents by Hour")
    plt.xlabel("Hour of Day")
    plt.ylabel("Number of Accidents")
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_FOLDER, "hourly_accidents.png"))
    plt.close()

    # 2. Accidents by region
    region_counts = df["region"].fillna("Unknown").value_counts()

    plt.figure(figsize=(9, 5))
    region_counts.plot(kind="bar")
    plt.title("Accidents by Location")
    plt.xlabel("Region")
    plt.ylabel("Number of Accidents")
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_FOLDER, "location_accidents.png"))
    plt.close()

    # 3. Accidents by severity
    severity_counts = df["severity"].fillna("Unknown").value_counts()

    plt.figure(figsize=(7, 5))
    severity_counts.plot(kind="bar")
    plt.title("Accidents by Severity")
    plt.xlabel("Severity")
    plt.ylabel("Number of Accidents")
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_FOLDER, "severity_accidents.png"))
    plt.close()

    # 4. Accidents by time period
    valid = df.dropna(subset=["accident_datetime"]).copy()
    hours = valid["accident_datetime"].dt.hour

    valid["time_period"] = np.select(
        [
            (hours >= 6) & (hours < 12),
            (hours >= 12) & (hours < 16),
            (hours >= 16) & (hours < 20)
        ],
        ["Morning", "Afternoon", "Evening"],
        default="Night"
    )

    period_counts = valid["time_period"].value_counts()

    plt.figure(figsize=(8, 5))
    period_counts.reindex(
        ["Morning", "Afternoon", "Evening", "Night"],
        fill_value=0
    ).plot(kind="bar")
    plt.title("Accidents by Time Period")
    plt.xlabel("Time Period")
    plt.ylabel("Number of Accidents")
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_FOLDER, "time_period_accidents.png"))
    plt.close()

    print("Analysis completed.")
    print(f"Total accident records: {len(df)}")
    print("Charts saved in:", CHART_FOLDER)


if __name__ == "__main__":
    analyze_accidents()
    print(get_accident_summary())
