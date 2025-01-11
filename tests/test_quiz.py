# Unit tests for quiz routes
import unittest
from app import create_app

class QuizTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_get_quiz(self):
        response = self.client.get('/quiz')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
