"""
Test Ingredients
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Ingredient
)

from recipe.serializers import IngredientSerializer

ING_URL = reverse('recipe:ingredient-list')


def detail_url(ing_id):
    return reverse('recipe:ingredient-detail', args=[ing_id])


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

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients assigned to recipes"""
        ing1 = Ingredient.objects.create(user=self.user, name='Coffee')
        ing2 = Ingredient.objects.create(user=self.user, name='Flour')

        recipe = create_recipe_helper(user=self.user)
        recipe.ingredients.add(ing1)

        res = self.client.get(ING_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtering ingredients unique"""
        ing1 = Ingredient.objects.create(user=self.user, name='Choco-Cream')
        Ingredient.objects.create(user=self.user, name='Flour-Bites')

        recipe1 = create_recipe_helper(user=self.user, title='pancakes')
        recipe2 = create_recipe_helper(user=self.user, title='air waffles')

        recipe1.ingredients.add(ing1)
        recipe2.ingredients.add(ing1)

        res = self.client.get(ING_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
