"""
Tests for models.
"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models


def create_user_helper(email="test@example.com", password="testpass123"):
    """
    A helper that creates a temp user
    So I don't have to repeat code.
    """
    return get_user_model().objects.create_user(
        email=email,
        password=password,
    )


class ModelTests(TestCase):
    """Test Models."""

    # --
    # General User management tests most apps will have.
    # -
    # User Creation and Authentication Model Tests:

    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful."""
        email = 'test@example.com'
        password = 'testpass123'
        user = create_user_helper(email=email, password=password)
        # user = get_user_model().objects.create_user(
        #    email=email,
        #    password=password,
        # )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalize(self):
        """Test email is normalized for new users."""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test when creating a user without an email it raises a ValueError"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'pass123')

    def test_create_superuser(self):
        """Test creating super user"""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test1234',
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    # --
    # Models based on the app being made:
    # -
    # Recipe Model Tests:

    def test_create_recipe(self):
        """ Test for create recipe is successful """
        user = create_user_helper()
        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample Recipe Title: Cookies for all~!',
            time_minutes=5,
            price=Decimal('5.50'),
            description=('Sample Description: '
                         'These cookies are tasty~! '
                         'Here is how you make them!')
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tags(self):
        """ Test for create tags"""
        user = create_user_helper()
        tag = models.Tag.objects.create(
            user=user,
            name='tag1',
        )

        self.assertEqual(str(tag), tag.name)
