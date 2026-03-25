from json import dumps
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.web import Application

import bcrypt
import urllib.parse

from api.handlers.registration import RegistrationHandler

from .base import BaseTest

class RegistrationHandlerTest(BaseTest):

    @classmethod
    def setUpClass(self):
        self.my_app = Application([(r'/registration', RegistrationHandler)])
        super().setUpClass()

    def test_registration(self):
        email = 'test@test.com'
        display_name = 'testDisplayName'

        body = {
          'email': email,
          'password': 'testPassword',
          'displayName': display_name
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        body_2 = json_decode(response.body)
        self.assertEqual(email, body_2['email'])
        self.assertEqual(display_name, body_2['displayName'])

    def test_registration_without_display_name(self):
        email = 'test@test.com'

        body = {
          'email': email,
          'password': 'testPassword'
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        body_2 = json_decode(response.body)
        self.assertEqual(email, body_2['email'])
        self.assertEqual(email, body_2['displayName'])

    def test_registration_twice(self):
        body = {
          'email': 'test@test.com',
          'password': 'testPassword',
          'displayName': 'testDisplayName'
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        response_2 = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(409, response_2.code)

    def test_password_not_stored_as_plaintext(self):
        email = 'test@test.com'
        body = {
            'email': email,
            'password': 'testPassword',
            'displayName': 'testDisplayName'
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        doc = IOLoop.current().run_sync(lambda: self.get_app().db.users.find_one({'email': email}))
        self.assertNotEqual(doc['password'], 'testPassword')

    def test_password_stored_as_bcrypt_hash(self):
        email = 'test@test.com'
        body = {
            'email': email,
            'password': 'testPassword',
            'displayName': 'testDisplayName'
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        doc = IOLoop.current().run_sync(lambda: self.get_app().db.users.find_one({'email': email}))
        self.assertTrue(bcrypt.checkpw('testPassword'.encode(), doc['password'].encode()))

    def test_personal_data_not_stored_as_plaintext(self):
        email = 'test@test.com'
        personal_data = {
            'fullName': 'John Doe',
            'address': '123 Main St',
            'dateOfBirth': '1990-01-01',
            'phoneNumber': '555-1234',
            'disabilities': 'none'
        }
        body = {
            'email': email,
            'password': 'testPassword',
            'displayName': 'testDisplayName',
            **personal_data
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        doc = IOLoop.current().run_sync(lambda: self.get_app().db.users.find_one({'email': email}))
        for field, plaintext_value in personal_data.items():
            self.assertNotEqual(doc[field], plaintext_value)

    def test_personal_data_iv_keys_present(self):
        email = 'test@test.com'
        body = {
            'email': email,
            'password': 'testPassword',
            'displayName': 'testDisplayName',
            'fullName': 'John Doe',
            'address': '123 Main St',
            'dateOfBirth': '1990-01-01',
            'phoneNumber': '555-1234',
            'disabilities': 'none'
        }

        response = self.fetch('/registration', method='POST', body=dumps(body))
        self.assertEqual(200, response.code)

        doc = IOLoop.current().run_sync(lambda: self.get_app().db.users.find_one({'email': email}))
        for field in ['fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities']:
            self.assertIn(f'{field}_iv', doc)
