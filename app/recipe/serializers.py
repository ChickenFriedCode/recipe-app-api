"""
Serializers for recipe APIs.
"""

from rest_framework import serializers
from core.models import (
    Recipe,
    Tag,
    Ingredient,
)


class IngredientSerializer(serializers.ModelSerializer):
    """serializer for ingredients."""
    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']


class TagSerializer(serializers.ModelSerializer):
    """serializer for tags."""
    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipes."""
    tags = TagSerializer(many=True, required=False)
    ingredients = IngredientSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes',
                  'price', 'link', 'tags', 'ingredients',]
        read_only_fields = ['id']

    def _get_or_create_field(self, field, instance, model, obj):
        """ Handle getting or creating fields. """
        auth_user = self.context['request'].user
        for f in field:
            f_obj, created = model.objects.get_or_create(
                user=auth_user,
                **f,
            )
            obj.add(f_obj)

    def create(self, validated_data) -> Recipe:
        """Create a new recipe."""
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_field(tags, recipe, Tag, recipe.tags)
        self._get_or_create_field(
            ingredients, recipe, Ingredient, recipe.ingredients)

        return recipe

    def update(self, instance, validated_data):
        """Update a recipe."""
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_field(tags, instance, Tag, instance.tags)
        if ingredients is not None:
            instance.ingredients.clear()
            # self._get_or_create_ingredients(ingredients, instance)
            self._get_or_create_field(
                ingredients, instance, Ingredient, instance.ingredients)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class RecipeDetailSerializer(RecipeSerializer):
    """Serializer for recipe details."""

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']
