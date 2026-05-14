import asyncio
import random
import time
from core.event_bus import event_bus
from core.config import settings

async def start_simulator():
    """Continuously emit simulated IoT sensor readings onto the event bus."""
    print("[Simulator] Starting city sensor simulation...")
    while True:
        ts = time.time()

        await event_bus.publish("sensor.traffic", {
            "timestamp": ts,
            "zone": random.choice(["zone_A", "zone_B", "zone_C"]),
            "vehicle_density": round(random.uniform(0.1, 1.0), 2),   # 0=empty 1=jam
            "avg_speed_kmh": round(random.uniform(5, 80), 1),
            "incident": random.random() < 0.05,                        # 5% chance
        })

        await event_bus.publish("sensor.energy", {
            "timestamp": ts,
            "grid_load_pct": round(random.uniform(30, 98), 1),
            "voltage_v": round(random.uniform(218, 242), 1),
            "kwh_consumed": round(random.uniform(200, 800), 1),
            "renewable_pct": round(random.uniform(10, 60), 1),
        })

        await event_bus.publish("sensor.safety", {
            "timestamp": ts,
            "location": random.choice(["park", "market", "station", "highway"]),
            "crowd_density": round(random.uniform(0, 1), 2),
            "anomaly_detected": random.random() < 0.03,                # 3% chance
            "camera_id": f"cam_{random.randint(1, 50):02d}",
        })

        await event_bus.publish("sensor.environment", {
            "timestamp": ts,
            "aqi": round(random.uniform(20, 180), 1),                  # >100 is unhealthy
            "noise_db": round(random.uniform(40, 95), 1),
            "temp_c": round(random.uniform(18, 42), 1),
            "humidity_pct": round(random.uniform(30, 90), 1),
        })

        await event_bus.publish("sensor.waste", {
            "timestamp": ts,
            "bin_id": f"bin_{random.randint(1, 200):03d}",
            "fill_pct": round(random.uniform(0, 100), 1),
            "last_collected_hrs": round(random.uniform(0, 72), 1),
        })

        await asyncio.sleep(settings.SENSOR_INTERVAL)
