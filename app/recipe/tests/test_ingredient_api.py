"""
Test Ingredients
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient

from recipe.serializers import IngredientSerializer

ING_URL = reverse('recipe:ingredient-list')


def detail_url(ing_id):
    return reverse('recipe:ingredient-detail', args=[ing_id])


# Helper functions:
def print_helper(thing):
    """ helper for print formatting """
    print(f"\n\n{thing}\n")


def create_user_helper(email='user@example.com', password='testpassword123'):
    """Helper function to create a user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientApiTest(TestCase):
    """Tests the public ingredients view"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test authentication required"""
        res = self.client.get(ING_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTest(TestCase):
    """Tests the private ingredients view"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user_helper()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving ingredients"""
        Ingredient.objects.create(user=self.user, name='Coffee Grounds')
        Ingredient.objects.create(user=self.user, name='Flour')

        res = self.client.get(ING_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_limited_to_user(self):
        """Test limiting ingredient to user"""
        user4 = create_user_helper(email='bla@example.com')
        Ingredient.objects.create(user=user4, name='Sugar')
        ing = Ingredient.objects.create(user=self.user, name='Kale')

        res = self.client.get(ING_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ing.name)
        self.assertEqual(res.data[0]['id'], ing.id)

    def test_update_ingredient(self):
        """Test updating an ingredient"""
        ing = Ingredient.objects.create(user=self.user, name='Coffee')
        payload = {'name': 'Beans'}

        url = detail_url(ing.id)
        res = self.client.patch(url, payload)
        print_helper(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ing.refresh_from_db()
        self.assertEqual(res.data['name'], payload['name'])

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ing = Ingredient.objects.create(user=self.user, name='Coffee')
        url = detail_url(ing.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ings = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ings.exists())
