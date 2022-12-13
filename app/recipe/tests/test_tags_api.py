"""
Test Tags API.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])


# Helper functions:
def print_helper(thing):
    print(f"\n\n{thing}\n")


def create_user_helper(email='user@example.com', password='testpassword123'):
    """Helper function to create a user."""
    return get_user_model().objects.create_user(email=email, password=password)


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
        print_helper(url)
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
