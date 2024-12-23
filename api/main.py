from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import redis
import time
import uuid

app = FastAPI()

# Redis connection
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)



# Models
class Quiz(BaseModel):
    id: str
    title: str
    questions: List[Dict]

class Vote(BaseModel):
    quiz_id: str
    question_id: str
    choice: str
    user_id: str
    timestamp: float

class Ranking(BaseModel):
    quiz_id: str
    rankings: Dict[str, List]

# Utility functions
def generate_id() -> str:
    return str(uuid.uuid4())

def store_quiz(quiz: Quiz):
    """
    Store a quiz and its questions in Redis.
    
    Args:
    - quiz (Quiz): The Quiz object to store. The quiz contains an id, title, and a list of questions.
    """
    
    # Storing the quiz in Redis
    redis_client.hset(f"quiz:{quiz.id}", 
                      mapping={
                          "title": quiz.title,  # Store the quiz title
                          "questions": str(quiz.questions)  # Store the questions as a string (can be serialized)
                      })

    # Storing each question in Redis
    question_id = 0
    for question in quiz.questions:
        question_id += 1  # Increment the question_id for each question
        
        # Storing each question with its corresponding details in Redis
        redis_client.hset(
            f"quiz:{quiz.id}:question:{question_id}",  # Key for storing individual question
            mapping={
                "text": question['text'],  # The question text
                "choices": str(question['choices']),  # The choices for the question (converted to string)
                "answer": question['answer']  # The correct answer for the question
            }
        )

      
def record_vote(vote: Vote):
    """
    Record a user's vote for a specific question in a quiz.
    
    Args:
    - vote (Vote): The Vote object containing the quiz_id, question_id, user_id, choice, and timestamp.
    """
    
    # Constructing the Redis key for storing the user's vote in the specific quiz
    user_votes_key = f"quiz:{vote.quiz_id}:user:{vote.user_id}:votes"
    
    # Check if the specified question exists in the Redis database
    # If not, raise a 404 error indicating the question is not found
    if not redis_client.exists(f"quiz:{vote.quiz_id}:question:{vote.question_id}"):
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Create a dictionary representing the vote entry
    vote_entry = {
        "question_id": vote.question_id,  # The ID of the question being voted on
        "choice": vote.choice,  # The user's selected choice for the question
        "user_id": vote.user_id,  # The ID of the user who cast the vote
        "timestamp": vote.timestamp  # The timestamp when the vote was cast
    }
    
    # Append the vote entry to the list of votes for this user in the quiz
    # This stores the vote in Redis under the user's key in the specified quiz
    redis_client.rpush(user_votes_key, str(vote_entry))






# Routes
@app.post("/create_quiz")
def create_quiz(quiz: Quiz):
    quiz.id = generate_id()
    store_quiz(quiz)
    return {"message": "Quiz created successfully", "quiz_id": quiz.id}

@app.post("/vote")
def vote(vote: Vote):
    vote.timestamp = time.time()
    record_vote(vote)
    return {"message": "Vote recorded successfully"}

@app.get("/quiz_stats/{quiz_id}/votes")
def get_quiz_stats(quiz_id: str):
    """
    Retrieve statistics for a given quiz, including:
    - Most voted alternatives per question
    - Most correct questions
    - Least voted questions
    - Users with the most correct answers
    
    Args:
    - quiz_id (str): The ID of the quiz.
    
    Returns:
    - A dictionary with various statistics about the quiz.
    """
    
    # Initialize containers to hold the results
    most_voted_per_question = {}
    most_correct_questions = {}
    least_voted_questions = {}
    users_correct_answers = {}
    
    # Container to store all votes
    votes_by_users = []
    # Get the list of questions for the quiz
    questions_keys = redis_client.keys(f"quiz:{quiz_id}:user:*")
    
    for key in questions_keys:
        # Retrieve all elements from the list
        elements = redis_client.lrange(key, 0, -1)

        # Parse each element from string to dictionary
        #parsed_elements = [eval(element) for element in elements]  # Use `json.loads` if the data is in JSON format

        # Extract user ID from the Redis key
        user_id = key.split(":")[-2]  # Assuming the key format `quiz:{quiz_id}:user:{user_id}:votes`

        # Add parsed elements to the list with user context
        votes_by_users.append({
            "user_id": user_id,
            "votes": elements
        })

    # Construct the JSON response
    return {
        "quiz_id": quiz_id,
        "total_users": len(questions_keys),
        "votes": votes_by_users
    }
    

   
    """
    # Loop through each question to gather statistics
    for question_key in questions_keys:
        question_id = question_key.split(":")[3]
        
        # Most voted alternative for this question
        votes_key = f"quiz:{quiz_id}:question:{question_id}:votes"
        if redis_client.exists(votes_key):
            votes = redis_client.hgetall(votes_key)  # Get all votes for this question
            most_voted_choice = max(votes, key=votes.get)  # Find the choice with the highest number of votes
            most_voted_per_question[question_id] = most_voted_choice
        
        # Most correct answers for this question
        correct_answers_key = f"quiz:{quiz_id}:question:{question_id}:correct_answer"
        correct_answer = redis_client.get(correct_answers_key)  # Retrieve the correct answer for the question
        
        # Track users who selected the correct answer
        for user_id, timestamp in redis_client.hgetall(votes_key).items():
            if user_id not in users_correct_answers:
                users_correct_answers[user_id] = 0
            if correct_answer == votes.get(user_id):  # Check if the user's choice was correct
                users_correct_answers[user_id] += 1
        
        # Least voted questions (just counting the number of votes)
        vote_count = len(votes)  # The number of users who voted for this question
        least_voted_questions[question_id] = vote_count
    
    # Most correct questions (questions with the highest number of correct answers)
    for question_id, correct_answer in most_correct_questions.items():
        correct_answer_count = sum(1 for user_votes in users_correct_answers.values() if user_votes.get(question_id) == correct_answer)
        most_correct_questions[question_id] = correct_answer_count
    
    # Sort questions by least voted and most correct
    least_voted_questions = dict(sorted(least_voted_questions.items(), key=lambda item: item[1]))
    most_correct_questions = dict(sorted(most_correct_questions.items(), key=lambda item: item[1], reverse=True))
    
    """
    
    # Return the results
    return {
        "questions_keys": questions_keys
    }


