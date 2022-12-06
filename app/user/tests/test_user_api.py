"""
Tests for the user api
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.Create_user(**params)


def payload():
    """Payload helper so I don't have to copy-pasta
        every time it's needed.
    """
    return {
        'email': 'test@example.com',
        'password': 'testpass1234',
        'name': 'Testing Nammmel',
    }


class PublicUserApiTests(TestCase):
    """Test the public user api features"""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test User Create Success"""
        # payload = {
        #     'email': 'test@example.com',
        #     'password': 'testpass1234',
        #     'name': 'Testing Nammmel',
        # }
        res = self.client.post(CREATE_USER_URL, payload())

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload()['email'])
        self.assertTrue(user.check_password(payload()['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """test error if user with email exists"""
        create_user(**payload())
