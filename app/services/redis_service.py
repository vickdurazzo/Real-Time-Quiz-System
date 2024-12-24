import json

def load_quiz_to_redis(redis_client, quiz_id, quiz_data):
    """Load quiz data into Redis."""
    redis_key = f"quiz:{str(quiz_id)}"  # Convert UUID to string
    redis_client.set(redis_key, json.dumps(quiz_data))

def get_quiz_from_redis(redis_client, quiz_id):
    """Retrieve quiz data from Redis."""
    redis_key = f"quiz:{quiz_id}"
    quiz_data = redis_client.get(redis_key)
    if quiz_data:
        return json.loads(quiz_data)
    return None
