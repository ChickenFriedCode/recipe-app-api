"""

Views for recipe APIs.
"""


from rest_framework import (

    viewsets,

    mixins,

)

from rest_framework.permissions import IsAuthenticated

from rest_framework.authentication import TokenAuthentication


from core.models import (
    Recipe,
    Tag,
    Ingredient,
)

from recipe import serializers


class RecipeViewSet(viewsets.ModelViewSet):

    """View for manage recipe APIs."""

    queryset = Recipe.objects.all()

    serializer_class = serializers.RecipeDetailSerializer

    authentication_classes = [TokenAuthentication]

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retrieve recipes for authenticated user."""

        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        """Retrieve recipe serializer class on request."""

        if self.action == 'list':

            return serializers.RecipeSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        """Create new recipe."""

        serializer.save(user=self.request.user)


class BaseAttributeViewSet(mixins.DestroyModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    """View for manage recipe tags APIs."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to authenticated user. """
        return self.queryset.filter(user=self.request.user).order_by('-name')


class TagViewSet(BaseAttributeViewSet):

    """View for manage recipe tags APIs."""
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer


class IngredientViewSet(BaseAttributeViewSet):
    """View for manage recipe ingredients APIs."""
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
