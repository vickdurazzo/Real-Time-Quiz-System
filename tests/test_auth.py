# Unit tests for authentication routes
import unittest
from app import create_app

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_login(self):
        response = self.client.post('/login', data={'username': 'test', 'password': 'test'})
        self.assertEqual(response.status_code, 200)

    def test_register(self):
        response = self.client.post('/register', data={'username': 'test', 'password': 'test'})
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
