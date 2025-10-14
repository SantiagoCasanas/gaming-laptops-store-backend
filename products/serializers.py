from rest_framework import serializers
from .models import Brand, Category, BaseProduct, Image, ProductVariant


class BrandSerializer(serializers.ModelSerializer):
    """
    Serializer for Brand model.
    Used for listing and retrieving brand information.
    """
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'active']
        read_only_fields = ['slug']


class BrandCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new brand.
    """
    class Meta:
        model = Brand
        fields = ['name']

    def create(self, validated_data):
        """Create and return a new brand instance."""
        brand = Brand.objects.create(**validated_data)
        return brand


class BrandUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating brand information.
    Only allows modification of name.
    """
    class Meta:
        model = Brand
        fields = ['name']

    def update(self, instance, validated_data):
        """Update and return the brand instance."""
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model.
    Used for listing and retrieving category information.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'active']
        read_only_fields = ['slug']


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new category.
    """
    class Meta:
        model = Category
        fields = ['name', 'description']
        extra_kwargs = {
            'description': {'required': False},
        }

    def create(self, validated_data):
        """Create and return a new category instance."""
        category = Category.objects.create(**validated_data)
        return category


class CategoryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating category information.
    Allows modification of name and description.
    """
    class Meta:
        model = Category
        fields = ['name', 'description']
        extra_kwargs = {
            'name': {'required': False},
            'description': {'required': False},
        }

    def update(self, instance, validated_data):
        """Update and return the category instance."""
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        return instance


# BaseProduct Serializers

class ImageSerializer(serializers.ModelSerializer):
    """
    Serializer for Image model.
    """
    class Meta:
        model = Image
        fields = ['id', 'imagen', 'alt_text', 'active']
        read_only_fields = ['id']


class BaseProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new BaseProduct with images.
    Accepts up to 4 images as file uploads.
    """
    # Image fields for file uploads (up to 4 images)
    image_1 = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_2 = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_3 = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_4 = serializers.ImageField(write_only=True, required=False, allow_null=True)

    # Alt text for each image
    alt_text_1 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    alt_text_2 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    alt_text_3 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    alt_text_4 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)

    # Categories as list of IDs
    categories = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True,
        help_text="List of category IDs"
    )

    class Meta:
        model = BaseProduct
        fields = [
            'model_name',
            'long_description',
            'brand',
            'categories',
            'specs',
            'image_1', 'image_2', 'image_3', 'image_4',
            'alt_text_1', 'alt_text_2', 'alt_text_3', 'alt_text_4'
        ]
        extra_kwargs = {
            'specs': {'required': True},
        }

    def validate_categories(self, value):
        """Validate that at least one category is provided and all exist."""
        if not value:
            raise serializers.ValidationError("At least one category is required.")

        # Check if all category IDs exist
        existing_categories = Category.objects.filter(id__in=value, active=True)
        if existing_categories.count() != len(value):
            raise serializers.ValidationError("One or more category IDs are invalid or inactive.")

        return value

    def validate_brand(self, value):
        """Validate that the brand is active."""
        if not value.active:
            raise serializers.ValidationError("The selected brand is inactive.")
        return value

    def validate_specs(self, value):
        """Validate that specs is a valid JSON object."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Specs must be a valid JSON object.")
        return value

    def create(self, validated_data):
        """Create BaseProduct with images."""
        # Extract image data
        images_data = []
        for i in range(1, 5):
            image_file = validated_data.pop(f'image_{i}', None)
            alt_text = validated_data.pop(f'alt_text_{i}', '')
            if image_file:
                images_data.append({'imagen': image_file, 'alt_text': alt_text})

        # Extract categories
        category_ids = validated_data.pop('categories')

        # Get user from context
        user = self.context['request'].user

        # Create BaseProduct
        base_product = BaseProduct.objects.create(
            **validated_data,
            user_last_modified=user
        )

        # Add categories
        base_product.categories.set(category_ids)
        print(images_data)

        # Create images
        for image_data in images_data:
            Image.objects.create(
                base_product=base_product,
                **image_data
            )

        return base_product


class BaseProductSerializer(serializers.ModelSerializer):
    """
    Serializer for BaseProduct listing and retrieval.
    Includes related brand, categories, and images.
    """
    brand = BrandSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = BaseProduct
        fields = [
            'id',
            'model_name',
            'slug',
            'long_description',
            'brand',
            'categories',
            'specs',
            'active',
            'creation_date',
            'update_date',
            'images'
        ]


class BaseProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating BaseProduct.
    Allows updating images by adding/removing them.
    """
    # Image fields for file uploads (up to 4 new images)
    image_1 = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_2 = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_3 = serializers.ImageField(write_only=True, required=False, allow_null=True)
    image_4 = serializers.ImageField(write_only=True, required=False, allow_null=True)

    # Alt text for each image
    alt_text_1 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    alt_text_2 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    alt_text_3 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)
    alt_text_4 = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=255)

    # Categories as list of IDs
    categories = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of category IDs"
    )

    # Option to remove existing images by ID
    remove_images = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of image IDs to remove"
    )

    class Meta:
        model = BaseProduct
        fields = [
            'model_name',
            'long_description',
            'brand',
            'categories',
            'specs',
            'image_1', 'image_2', 'image_3', 'image_4',
            'alt_text_1', 'alt_text_2', 'alt_text_3', 'alt_text_4',
            'remove_images'
        ]
        extra_kwargs = {
            'model_name': {'required': False},
            'long_description': {'required': False},
            'brand': {'required': False},
            'specs': {'required': False},
        }

    def validate_categories(self, value):
        """Validate that all category IDs exist and are active."""
        if value:
            existing_categories = Category.objects.filter(id__in=value, active=True)
            if existing_categories.count() != len(value):
                raise serializers.ValidationError("One or more category IDs are invalid or inactive.")
        return value

    def validate_brand(self, value):
        """Validate that the brand is active."""
        if value and not value.active:
            raise serializers.ValidationError("The selected brand is inactive.")
        return value

    def validate_specs(self, value):
        """Validate that specs is a valid JSON object."""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Specs must be a valid JSON object.")
        return value

    def update(self, instance, validated_data):
        """Update BaseProduct with new data and handle images."""
        # Extract image data
        images_data = []
        for i in range(1, 5):
            image_file = validated_data.pop(f'image_{i}', None)
            alt_text = validated_data.pop(f'alt_text_{i}', '')
            if image_file:
                images_data.append({'imagen': image_file, 'alt_text': alt_text})

        # Handle image removal
        remove_images = validated_data.pop('remove_images', [])
        if remove_images:
            Image.objects.filter(id__in=remove_images, base_product=instance).delete()

        # Extract categories
        category_ids = validated_data.pop('categories', None)

        # Get user from context
        user = self.context['request'].user

        # Update basic fields
        instance.model_name = validated_data.get('model_name', instance.model_name)
        instance.long_description = validated_data.get('long_description', instance.long_description)
        instance.brand = validated_data.get('brand', instance.brand)
        instance.specs = validated_data.get('specs', instance.specs)
        instance.user_last_modified = user
        instance.save()

        # Update categories if provided
        if category_ids is not None:
            instance.categories.set(category_ids)

        # Add new images
        for image_data in images_data:
            Image.objects.create(
                base_product=instance,
                **image_data
            )

        return instance


# ProductVariant Serializers

class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductVariant listing and retrieval.
    Includes related base product information.
    """
    base_product = BaseProductSerializer(read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    stock_status_display = serializers.CharField(source='get_stock_status_display', read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'base_product',
            'price',
            'condition',
            'condition_display',
            'stock_status',
            'stock_status_display',
            'is_published',
            'active',
            'creation_date',
            'update_date'
        ]


class ProductVariantCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new ProductVariant.
    """
    class Meta:
        model = ProductVariant
        fields = [
            'base_product',
            'price',
            'condition',
            'stock_status',
            'is_published'
        ]

    def validate_base_product(self, value):
        """Validate that the base product exists and is active."""
        if not value.active:
            raise serializers.ValidationError("The selected base product is inactive.")
        return value

    def validate_price(self, value):
        """Validate that the price is positive."""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def create(self, validated_data):
        """Create ProductVariant with user tracking."""
        # Get user from context
        user = self.context['request'].user

        # Create ProductVariant
        product_variant = ProductVariant.objects.create(
            **validated_data,
            user_last_modified=user
        )

        return product_variant


class ProductVariantUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating ProductVariant.
    All fields are optional for partial updates.
    """
    class Meta:
        model = ProductVariant
        fields = [
            'base_product',
            'price',
            'condition',
            'stock_status',
            'is_published'
        ]
        extra_kwargs = {
            'base_product': {'required': False},
            'price': {'required': False},
            'condition': {'required': False},
            'stock_status': {'required': False},
            'is_published': {'required': False}
        }

    def validate_base_product(self, value):
        """Validate that the base product exists and is active."""
        if value and not value.active:
            raise serializers.ValidationError("The selected base product is inactive.")
        return value

    def validate_price(self, value):
        """Validate that the price is positive."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def update(self, instance, validated_data):
        """Update ProductVariant with user tracking."""
        # Get user from context
        user = self.context['request'].user

        # Update fields
        instance.base_product = validated_data.get('base_product', instance.base_product)
        instance.price = validated_data.get('price', instance.price)
        instance.condition = validated_data.get('condition', instance.condition)
        instance.stock_status = validated_data.get('stock_status', instance.stock_status)
        instance.is_published = validated_data.get('is_published', instance.is_published)
        instance.user_last_modified = user
        instance.save()

        return instance
