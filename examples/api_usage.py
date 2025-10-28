"""
Memoric REST API Example

Demonstrates how to use the Memoric REST API for memory management.

Start the server first:
    uvicorn api.server:app --reload

Then run this script in another terminal.
"""
import requests
import json

API_BASE = "http://localhost:8000"

def main():
    print("=== Memoric API Usage Example ===\n")

    # 1. Health check
    print("1. Checking API health...")
    response = requests.get(f"{API_BASE}/health")
    print(f"   Status: {response.json()['status']}")
    print(f"   Database: {response.json().get('database', 'unknown')}\n")

    # 2. Save a memory
    print("2. Saving a memory...")
    save_payload = {
        "user_id": "api_user_123",
        "content": "Customer inquired about shipping times for international orders",
        "thread_id": "support_chat_789",
        "metadata": {
            "topic": "shipping",
            "category": "support",
            "priority": "medium"
        }
    }
    response = requests.post(f"{API_BASE}/memories", json=save_payload)
    memory_id = response.json()["id"]
    print(f"   Created memory ID: {memory_id}\n")

    # 3. Retrieve memories
    print("3. Retrieving memories...")
    retrieve_payload = {
        "user_id": "api_user_123",
        "thread_id": "support_chat_789",
        "top_k": 10
    }
    response = requests.post(f"{API_BASE}/memories/retrieve", json=retrieve_payload)
    result = response.json()
    print(f"   Found {result['count']} memories")
    for mem in result['memories'][:3]:
        print(f"   - {mem['content'][:60]}...\n")

    # 4. Retrieve with metadata filter
    print("4. Retrieving with metadata filter...")
    retrieve_payload = {
        "user_id": "api_user_123",
        "metadata_filter": {"topic": "shipping"},
        "top_k": 5
    }
    response = requests.post(f"{API_BASE}/memories/retrieve", json=retrieve_payload)
    result = response.json()
    print(f"   Found {result['count']} shipping-related memories\n")

    # 5. Get statistics
    print("5. Getting statistics...")
    response = requests.get(f"{API_BASE}/stats", params={"user_id": "api_user_123"})
    stats = response.json()
    print(f"   Tier statistics:")
    for tier, count in stats.get('count_by_tier', {}).items():
        print(f"     {tier}: {count} memories\n")

    # 6. Get clusters
    print("6. Retrieving clusters...")
    response = requests.get(f"{API_BASE}/clusters", params={"limit": 5})
    clusters = response.json()
    print(f"   Found {clusters['count']} clusters")
    for cluster in clusters['clusters'][:3]:
        print(f"   - {cluster.get('topic')} / {cluster.get('category')}: {cluster.get('memory_count', 0)} memories\n")

    # 7. Run policies
    print("7. Running memory policies...")
    response = requests.post(f"{API_BASE}/policies/run")
    policy_results = response.json()
    print(f"   Migrated: {policy_results.get('migrated', 0)}")
    print(f"   Trimmed: {policy_results.get('trimmed', 0)}")
    print(f"   Summarized: {policy_results.get('summarized', 0)}")
    print(f"   Clusters rebuilt: {policy_results.get('clusters_rebuilt', 0)}\n")

    # 8. Promote memories to different tier
    print("8. Promoting memory to long_term tier...")
    promote_payload = {
        "memory_ids": [memory_id],
        "target_tier": "long_term"
    }
    response = requests.post(f"{API_BASE}/memories/promote", json=promote_payload)
    result = response.json()
    print(f"   Promoted {result['promoted']} memories to {result['target_tier']}\n")

    print("=== API Usage Complete ===")
    print("\nAPI Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API server.")
        print("Please start the server first: uvicorn api.server:app --reload")
    except Exception as e:
        print(f"Error: {e}")
