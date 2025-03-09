import json
import random
from datetime import datetime, timedelta

# Sample data for generation
services = ["payment-service", "auth-service", "order-service", "user-service"]
error_codes = {
    "payment-service": ["PAY_001", "PAY_002", "PAY_003"],
    "auth-service": ["AUTH_001", "AUTH_002"],
    "order-service": ["ORD_001", "ORD_002", "ORD_003"],
    "user-service": ["USR_001", "USR_002"]
}
error_messages = {
    "PAY_001": "Failed to process payment transaction",
    "PAY_002": "Invalid payment method",
    "PAY_003": "Payment timeout",
    "AUTH_001": "Invalid credentials",
    "AUTH_002": "Session expired",
    "ORD_001": "Order validation failed",
    "ORD_002": "Inventory not available",
    "ORD_003": "Order processing timeout",
    "USR_001": "User not found",
    "USR_002": "Invalid user data"
}

def generate_error_log(timestamp):
    service = random.choice(services)
    error_code = random.choice(error_codes[service])
    return {
        "timestamp": timestamp.isoformat() + "Z",
        "level": "ERROR",
        "service": service,
        "error_code": error_code,
        "message": error_messages[error_code],
        "stack_trace": f"Exception in thread main at {service}.java:${random.randint(100,999)}",
        "correlation_id": f"txn-{random.randint(1000,9999)}",
        "user_id": f"user-{random.randint(100,999)}",
        "metadata": {
            "environment": "production",
            "region": "us-west-2",
            "version": f"1.{random.randint(0,9)}.{random.randint(0,9)}"
        }
    }

def main():
    logs = []
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    current_time = start_time

    print("Generating error logs...")
    while current_time < end_time:
        if random.random() < 0.1:  # 10% chance of error in each minute
            logs.append(generate_error_log(current_time))
        current_time += timedelta(minutes=1)

    print(f"Generated {len(logs)} error logs")
    
    with open('error_logs.json', 'w') as f:
        json.dump(logs, f, indent=2)
    print("Logs saved to error_logs.json")

if __name__ == "__main__":
    main()
