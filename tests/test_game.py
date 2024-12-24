import pytest
import threading
from flask import Flask
from redis import Redis
import json
from app import create_app  # Replace with the correct path to your Flask app factory

@pytest.fixture
def client():
    """Set up Flask test client with Redis connection."""
    app = create_app()
    app.redis_client = Redis(host='localhost', port=6379, decode_responses=True)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def setup_quiz_data(redis_client):
    """Set up initial quiz data in Redis."""
    redis_client.set('quiz:1', json.dumps({
        "questions": [
            {"id": "q1", "text": "What is 2+2?", "choices": ["2", "3", "4", "5"]},
            {"id": "q2", "text": "What is 3+3?", "choices": ["5", "6", "7", "8"]}
        ]
    }))
    redis_client.delete('quiz:1:players', 'quiz:1:answers', 'quiz:1:current_question')
    redis_client.set('quiz:1:current_question', 0)


def simulate_player(client, quiz_id, username, answers):
    """Simulate a single player joining and submitting answers."""
    # Join the quiz
    response = client.post(f'/quiz/{quiz_id}/join', json={"username": username})
    assert response.status_code == 200, f"Player {username} failed to join"

    # Submit answers
    for answer in answers:
        response = client.post(f'/quiz/{quiz_id}/submit_answer', json={"username": username, "answer_id": answer})
        assert response.status_code == 200, f"Player {username} failed to submit answer"


def test_simultaneous_players(client):
    """Test multiple players joining and submitting answers concurrently."""
    redis_client = client.application.redis_client

    # Setup quiz data in Redis
    setup_quiz_data(redis_client)

    # Start the quiz dynamics
    response = client.post('/quiz/1/start_dynamics')
    assert response.status_code == 200, "Failed to start quiz dynamics"

    # Simulate multiple players
    players = [
        {"username": "player1", "answers": ["4", "6"]},
        {"username": "player2", "answers": ["4", "5"]},
        {"username": "player3", "answers": ["3", "6"]}
    ]

    threads = []
    for player in players:
        t = threading.Thread(target=simulate_player, args=(client, 1, player["username"], player["answers"]))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check if all players were registered
    registered_players = redis_client.smembers('quiz:1:players')
    assert registered_players == {"player1", "player2", "player3"}, "Not all players registered correctly"

    # Check if answers were recorded
    answers_key = 'quiz:1:answers'
    answers = redis_client.hgetall(answers_key)
    expected_answers = {
        "0:player1": "4",
        "1:player1": "6",
        "0:player2": "4",
        "1:player2": "5",
        "0:player3": "3",
        "1:player3": "6"
    }
    assert answers == expected_answers, "Answers were not recorded correctly"
