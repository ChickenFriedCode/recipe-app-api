"""
Tests for recipe APIs.
"""

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)
from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPES_URL = reverse('recipe:recipe-list')

# ----- Helper Functions: --------------------------------


def detail_url(recipe_id):
    """Create and return a recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def img_upload_url(recipe_id):
    """Create and return a recipe image upload URL"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample Description',
        'link': 'https://example.com/resipes.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a sample user."""
    return get_user_model().objects.create_user(**params)

# ----------------------------------------------------------------


# - Test Classes
class PublicRecipeAPITest(TestCase):
    """Tests for public Unauthcated recipe API endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """test auth is required to call API"""
        response = self.client.get(RECIPES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITest(TestCase):
    """Tests for private Authcated recipe API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrive_recipe(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """ Test list of recipies is limited to authenticated user. """
        other_user = create_user(
            email='other@example.com', password='password123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test retrieving a single recipe."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        "Test creating a new recipe."""
        payload = {
            'title': 'cookies a lot of cookies',
            'time_minutes': 15,
            'price': Decimal('15.23'),
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial updating a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample Brownies',
            link=original_link,
        )
        payload = {
            'title': 'New Title',
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full updating a recipe."""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample cookies',
            link=original_link,
            description='The Sample Cookies are chocolate',
        )
        payload = {
            'title': 'New Title',
            'link': 'https://example.com/new_link.pdf',
            'description': 'They are now Vanilla cookies~!',
            'time_minutes': 50,
            'price': Decimal('2.30'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test updating a recipe with an invalid user."""
        new_user = create_user(email='user2@example.com',
                               password='password123')
        recipe = create_recipe(user=self.user)
        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe."""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        """test deleting other users recipe"""
        new_user = create_user(email='user3@example.com',
                               password='password123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    # ----- Tags --------------------------------

    def test_create_recipe_with_new_tags(self):
        """ Test creating recipe with new tags."""
        payload = {
            'title': 'Sample Brownies',
            'time_minutes': 50,
            'price': Decimal('2.30'),
            'tags': [{'name': 'Cookies'}, {'name': 'Snacks'}],
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating recipe with existing tags."""
        tag_cookie = Tag.objects.create(user=self.user, name='Cookies')
        payload = {
            'title': 'Sample Cookies',
            'time_minutes': 50,
            'price': Decimal('2.30'),
            'tags': [{'name': 'Cookies'}, {'name': 'Snacks'}],
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_cookie, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """ Test creating a tag when updating a recipe """
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test updating a recipe's tags"""
        recipe = create_recipe(user=self.user)
        tag_cookie = Tag.objects.create(user=self.user, name='Cookies')
        recipe.tags.add(tag_cookie)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_cookie, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """ Test clearing a recipes tags. """
        recipe = create_recipe(user=self.user)
        tag = Tag.objects.create(user=self.user, name='Cookies')
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    # ----- Ingredients--------------------

    def test_create_recipe_with_new_ingredient(self):
        """Test creating a recipe with a new ingredient"""
        payload = {
            'title': 'Sample Brownies',
            'time_minutes': 50,
            'price': Decimal('2.30'),
            'ingredients': [{'name': 'Chocolate'}, {'name': 'Lime'}],
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]

        self.assertEqual(recipe.ingredients.count(), 2)
        for ing in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ing['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a recipe with existing tags"""
        ing_hot_coco = Ingredient.objects.create(
            user=self.user, name='Hot_Chocolate')
        payload = {
            'title': 'Sample Cookies',
            'time_minutes': 50,
            'price': Decimal('2.30'),
            'ingredients': [{'name': 'Hot_Chocolate'}, {'name': 'Snacks'}],
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ing_hot_coco, recipe.ingredients.all())
        for ing in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ing['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """ Test creating a ingredient when updating a recipe """
        # ing_name = 'Peppers'
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Peppers'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ing = Ingredient.objects.get(user=self.user, name='Peppers')
        self.assertIn(new_ing, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test updating a recipe's tags"""
        ing_1 = 'chocolate'
        ing_2 = 'honey'

        recipe = create_recipe(user=self.user)
        ing_original = Ingredient.objects.create(user=self.user, name=ing_1)
        recipe.ingredients.add(ing_original)

        ing_updated = Ingredient.objects.create(user=self.user, name=ing_2)
        payload = {'ingredients': [{'name': ing_2}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ing_updated, recipe.ingredients.all())
        self.assertNotIn(ing_original, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """ Test clearing a recipes tags. """
        recipe = create_recipe(user=self.user)
        ing = Ingredient.objects.create(user=self.user, name='Cookies')
        recipe.ingredients.add(ing)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """ Test filtering recipes by tags """
        r1 = create_recipe(user=self.user, title='Fasting Foods')
        r2 = create_recipe(user=self.user, title='Fasting Drinks')
        r3 = create_recipe(user=self.user, title='Chocolate cake')
        tag1 = Tag.objects.create(user=self.user, name='Eats')
        tag2 = Tag.objects.create(user=self.user, name='Diet Foods')
        tag3 = Tag.objects.create(user=self.user, name='Drinks')

        r1.tags.add(tag1)
        r1.tags.add(tag2)
        r2.tags.add(tag2)
        r2.tags.add(tag3)

        params = {'tags': f'{tag1.id},{tag3.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """ Test filtering recipes by ingredients """
        r1 = create_recipe(user=self.user, title='Fasting Foods')
        r2 = create_recipe(user=self.user, title='Fasting Drinks')
        r3 = create_recipe(user=self.user, title='Chocolate cake')
        ing1 = Ingredient.objects.create(user=self.user, name='Air')
        ing2 = Ingredient.objects.create(user=self.user, name='Water')
        ing3 = Ingredient.objects.create(user=self.user, name='Salt')

        r1.ingredients.add(ing1)
        r1.ingredients.add(ing2)
        r2.ingredients.add(ing2)
        r2.ingredients.add(ing3)

        params = {'ingredients': f'{ing1.id},{ing3.id}'}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

# ----- Image Tests API: --------------------------------


class ImageUploadTests(TestCase):
    """
    Test the image upload endpoint
    """

    def setUp(self):
        """ Set up for image tests"""
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='testpass1234'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """ Test uploading an image"""
        url = img_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_not_an_image(self):
        """ Test uploading a non-image"""
        url = img_upload_url(self.recipe.id)
        payload = {'image': 'not an image'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
