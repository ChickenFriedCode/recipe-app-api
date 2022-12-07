"""
Tests for the user api
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


def payload_helper(
        email='test@example.com',
        password='testpass1234',
        name='Testing_Name_Person'):
    """Payload helper so I don't have to copy-pasta
        every time it's needed.
    """
    return {
        'email': email,
        'password': password,
        'name': name,
    }


class PublicUserApiTests(TestCase):
    """Test the public user api features"""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test User Create Success"""
        payload = payload_helper()
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """test error if user with email exists"""
        payload = payload_helper()
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_to_short(self):
        """Test if password is to short"""
        payload = payload_helper('pw')
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """ Test Generates token for valid credentials """
        user_details = payload_helper(
            password='test_password-1234',
            name='Test Name'
        )
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password']
        }
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """ Test returns error if credentials are incorrect """
        create_user(email='test@example', password='GoodPass')

        payload = payload_helper()
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """ Test if get Error when posting blank password """
        payload = payload_helper(password='')
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """ Test authentication is required for users. """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test API requests that require authentication."""

    def setUp(self):
        """ Create Test User """
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='Test Person Name',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """ Test retrieving pofile for logged in user. """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,
        })

    def test_post_me_not_allowed(self):
        """ Test POST is not allowed for the me endpoint. """
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """ Test updating the user profile for the authenticated user. """
        new_payload = {'name': 'New Name', 'password': 'NewPass12345'}

        res = self.client.patch(ME_URL, new_payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, new_payload['name'])
        self.assertTrue(self.user.check_password(new_payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
