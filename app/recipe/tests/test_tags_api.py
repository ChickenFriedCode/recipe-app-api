"""
Test Tags API.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
)

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])


# Helper functions:

def create_user_helper(email='user@example.com', password='testpassword123'):
    """Helper function to create a user."""
    return get_user_model().objects.create_user(email=email, password=password)


def create_recipe_helper(user, title='testing title', time=10, price='4.50'):
    """Helper function to create a recipe."""
    return Recipe.objects.create(
        user=user,
        title=title,
        time_minutes=time,
        price=Decimal(price)
    )


# Test classes:
class PublicTagsApiTests(TestCase):
    """Tests for the public tags API."""

    def setUp(self):
        """Create test user."""
        self.client = APIClient()

    def test_auth_required(self):
        """Test authentication required."""
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Tests for the Authenticated private tags API."""

    def setUp(self):
        """Create test user."""
        self.user = create_user_helper()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """ Test for retrieving list of tags """

        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Desert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags limited to Authenticated user"""
        user2 = create_user_helper(email='user2@example.com')
        Tag.objects.create(user=user2, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_updating_tag(self):
        """Test updating a tag"""
        tag = Tag.objects.create(user=self.user, name='More Food')

        payload = {'name': 'Less food'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_deleting_tag(self):
        """Test deleting a tag"""
        tag = Tag.objects.create(user=self.user, name='Breakfast')

        url = detail_url(tag.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test filtering tags assigned to recipes"""
        tag1 = Tag.objects.create(user=self.user, name='Diet-Dr')
        tag2 = Tag.objects.create(user=self.user, name='Keto-Salad')

        recipe = create_recipe_helper(user=self.user)
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """Test filtering tags unique"""
        tag1 = Tag.objects.create(user=self.user, name='Diet')
        Tag.objects.create(user=self.user, name='Low-Sugar')

        recipe1 = create_recipe_helper(user=self.user, title='Keto-Pancakes')
        recipe2 = create_recipe_helper(user=self.user, title='air waffles')

        recipe1.tags.add(tag1)
        recipe2.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
