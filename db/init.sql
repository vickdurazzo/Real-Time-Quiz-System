-- Enable the pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drop and recreate Users table
DROP TABLE IF EXISTS Users CASCADE;
CREATE TABLE IF NOT EXISTS Users (
    user_id uuid DEFAULT gen_random_uuid(),
    nm_user VARCHAR NOT NULL UNIQUE,
    des_user_passwd VARCHAR NOT NULL,
    PRIMARY KEY (user_id)

);

-- Drop and recreate Quizzes table
DROP TABLE IF EXISTS Quizzes CASCADE;
CREATE TABLE IF NOT EXISTS Quizzes (
    quiz_id uuid  DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    title VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL,
    PRIMARY KEY (quiz_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Drop and recreate Questions table
DROP TABLE IF EXISTS Questions CASCADE;
CREATE TABLE IF NOT EXISTS Questions (
    question_id SERIAL,
    quiz_id uuid NOT NULL,
    question_text VARCHAR NOT NULL,
    PRIMARY KEY (question_id),
    FOREIGN KEY (quiz_id) REFERENCES Quizzes(quiz_id)
);

-- Drop and recreate Answers table
DROP TABLE IF EXISTS Answers CASCADE;
CREATE TABLE IF NOT EXISTS Answers (
    answer_id SERIAL ,
    question_id INT NOT NULL,
    answer_text VARCHAR NOT NULL,
    is_correct BOOLEAN NOT NULL,
    nm_answer_option CHAR(1),
    PRIMARY KEY (answer_id),
    FOREIGN KEY (question_id) REFERENCES Questions(question_id)
);

-- Test inserts
--INSERT INTO Users (nm_user, des_user_passwd)
--VALUES ('test_user', 'test_password2');

--SELECT * FROM Users; -- Verify UUIDs are generated
