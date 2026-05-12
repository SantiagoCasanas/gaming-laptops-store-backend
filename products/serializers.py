from rest_framework import serializers
from django.db import transaction
from .models import (
    Brand, TipoProducto, CampoProducto, TipoProductoCampo, Proveedor,
    Producto, ProductoCampoValor, ImagenProducto,
    BajoPedido, Descuento, UnidadProducto
)


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


# TipoProducto Serializers

class TipoProductoSerializer(serializers.ModelSerializer):
    """
    Serializer for TipoProducto model.
    Used for listing and retrieving product type information.
    """
    class Meta:
        model = TipoProducto
        fields = ['id', 'nombre', 'descripcion', 'active']


class TipoProductoCampoWriteSerializer(serializers.Serializer):
    """
    Nested serializer representing one field association in a create/update request.
    Accepts the CampoProducto id, an optional display order, and a required flag.
    The required flag is stored on the association (TipoProductoCampo), not on the
    field itself, implementing Option B (per-association required constraint).

    Promo card configuration (mostrar_en_promo, orden_promo, icono_slug) is also
    stored per-association so the same CampoProducto can be on the promo card of
    one TipoProducto and not on another's.
    """
    id = serializers.IntegerField()
    orden = serializers.IntegerField(default=0)
    required = serializers.BooleanField(default=False)
    mostrar_en_promo = serializers.BooleanField(default=False, required=False)
    orden_promo = serializers.IntegerField(default=0, required=False)
    icono_slug = serializers.CharField(default='', required=False, allow_blank=True, max_length=40)


class TipoProductoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new product type with optional field associations.
    Accepts a 'campos' list of {id, orden} entries that are created atomically
    together with the product type.
    """
    campos = TipoProductoCampoWriteSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = TipoProducto
        fields = ['nombre', 'descripcion', 'campos']
        extra_kwargs = {
            'descripcion': {'required': False}
        }

    def create(self, validated_data):
        """Create product type and field associations atomically."""
        from django.db import transaction

        campos_data = validated_data.pop('campos', [])

        with transaction.atomic():
            tipo_producto = TipoProducto.objects.create(**validated_data)

            if campos_data:
                campo_ids = [f['id'] for f in campos_data]
                found_ids = set(
                    CampoProducto.objects.filter(id__in=campo_ids).values_list('id', flat=True)
                )
                missing = set(campo_ids) - found_ids
                if missing:
                    raise serializers.ValidationError({
                        'campos': f'Product field(s) with id(s) {sorted(missing)} not found.'
                    })

                for field_data in campos_data:
                    TipoProductoCampo.objects.create(
                        tipo_producto=tipo_producto,
                        campo_producto_id=field_data['id'],
                        orden=field_data.get('orden', 0),
                        required=field_data.get('required', False),
                        mostrar_en_promo=field_data.get('mostrar_en_promo', False),
                        orden_promo=field_data.get('orden_promo', 0),
                        icono_slug=field_data.get('icono_slug', ''),
                    )

        return tipo_producto


class TipoProductoUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a product type and atomically replacing its field associations.
    When 'campos' is provided the existing associations are fully replaced.
    When 'campos' is omitted the associations are left unchanged.
    """
    campos = TipoProductoCampoWriteSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = TipoProducto
        fields = ['nombre', 'descripcion', 'campos']
        extra_kwargs = {
            'nombre': {'required': False},
            'descripcion': {'required': False},
        }

    def update(self, instance, validated_data):
        """Update product type and replace field associations atomically."""
        from django.db import transaction

        campos_data = validated_data.pop('campos', None)

        with transaction.atomic():
            instance.nombre = validated_data.get('nombre', instance.nombre)
            instance.descripcion = validated_data.get('descripcion', instance.descripcion)
            instance.save()

            if campos_data is not None:
                campo_ids = [f['id'] for f in campos_data]
                if campo_ids:
                    found_ids = set(
                        CampoProducto.objects.filter(id__in=campo_ids).values_list('id', flat=True)
                    )
                    missing = set(campo_ids) - found_ids
                    if missing:
                        raise serializers.ValidationError({
                            'campos': f'Product field(s) with id(s) {sorted(missing)} not found.'
                        })

                instance.tipo_producto_campos.all().delete()
                for field_data in campos_data:
                    TipoProductoCampo.objects.create(
                        tipo_producto=instance,
                        campo_producto_id=field_data['id'],
                        orden=field_data.get('orden', 0),
                        required=field_data.get('required', False),
                        mostrar_en_promo=field_data.get('mostrar_en_promo', False),
                        orden_promo=field_data.get('orden_promo', 0),
                        icono_slug=field_data.get('icono_slug', ''),
                    )

        return instance


# CampoProducto Serializers

class CampoProductoSerializer(serializers.ModelSerializer):
    """
    Serializer for CampoProducto model.
    Used for listing and retrieving field information.
    """
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = CampoProducto
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'required', 'active']


class CampoProductoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new product field.
    Includes the optional 'required' flag.
    """
    class Meta:
        model = CampoProducto
        fields = ['nombre', 'tipo', 'required']
        extra_kwargs = {
            'tipo': {'required': True},
            'required': {'required': False},
        }

    def create(self, validated_data):
        """Create and return a new product field instance."""
        campo = CampoProducto.objects.create(**validated_data)
        return campo


class CampoProductoUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating product field information.
    Allows modification of nombre, tipo, and required.
    """
    class Meta:
        model = CampoProducto
        fields = ['nombre', 'tipo', 'required']
        extra_kwargs = {
            'nombre': {'required': False},
            'tipo': {'required': False},
            'required': {'required': False},
        }

    def update(self, instance, validated_data):
        """Update and return the field instance."""
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.tipo = validated_data.get('tipo', instance.tipo)
        instance.required = validated_data.get('required', instance.required)
        instance.save()
        return instance


# TipoProductoCampo Serializers

class TipoProductoCampoSerializer(serializers.ModelSerializer):
    """
    Serializer for TipoProductoCampo junction model.
    Exposes the linked field's name, type, and ordering value.
    The 'required' flag is read directly from the association row (Option B),
    so the same CampoProducto can be required in one product type and optional
    in another.
    Used when reading field associations on a product type detail endpoint.
    """
    campo_nombre = serializers.CharField(source='campo_producto.nombre', read_only=True)
    campo_tipo = serializers.CharField(source='campo_producto.tipo', read_only=True)
    campo_tipo_display = serializers.CharField(source='campo_producto.get_tipo_display', read_only=True)

    class Meta:
        model = TipoProductoCampo
        fields = [
            'id', 'campo_producto', 'campo_nombre', 'campo_tipo', 'campo_tipo_display',
            'required', 'orden', 'mostrar_en_promo', 'orden_promo', 'icono_slug',
        ]


class TipoProductoDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer for TipoProducto.
    Includes the ordered list of associated CampoProducto entries
    through the TipoProductoCampo junction table.
    """
    campos = TipoProductoCampoSerializer(source='tipo_producto_campos', many=True, read_only=True)

    class Meta:
        model = TipoProducto
        fields = ['id', 'nombre', 'descripcion', 'active', 'campos']


# Proveedor Serializers

class ProveedorSerializer(serializers.ModelSerializer):
    """
    Serializer for Proveedor model.
    Used for listing and retrieving supplier information.
    """
    class Meta:
        model = Proveedor
        fields = ['id', 'nombre', 'slug', 'active']
        read_only_fields = ['slug']


class ProveedorCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new supplier.
    Slug is auto-generated from nombre on model save.
    """
    class Meta:
        model = Proveedor
        fields = ['nombre']

    def create(self, validated_data):
        """Create and return a new Proveedor instance."""
        proveedor = Proveedor.objects.create(**validated_data)
        return proveedor


class ProveedorUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating supplier information.
    Only allows modification of nombre.
    Slug is not regenerated on update (set once at creation).
    """
    class Meta:
        model = Proveedor
        fields = ['nombre']
        extra_kwargs = {
            'nombre': {'required': False},
        }

    def update(self, instance, validated_data):
        """Update and return the Proveedor instance."""
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# Producto serializers
# ---------------------------------------------------------------------------

class ImagenProductoSerializer(serializers.ModelSerializer):
    """
    Read serializer for ImagenProducto.
    Returns the image URL (absolute) and display order.
    """
    url = serializers.SerializerMethodField()

    class Meta:
        model = ImagenProducto
        fields = ['id', 'url', 'orden']

    def get_url(self, obj):
        """Return the absolute URL for the image."""
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.url.url)
        return obj.url.url


class ProductoCampoValorSerializer(serializers.ModelSerializer):
    """
    Read serializer for ProductoCampoValor.
    Returns the campo id, its name, tipo, and the active value column.
    The required constraint is now stored on TipoProductoCampo (Option B) and
    is exposed via TipoProductoDetailSerializer, not here.
    """
    campo_nombre = serializers.CharField(source='campo_producto.nombre', read_only=True)
    campo_tipo = serializers.CharField(source='campo_producto.tipo', read_only=True)

    class Meta:
        model = ProductoCampoValor
        fields = [
            'id', 'campo_producto', 'campo_nombre', 'campo_tipo',
            'valor_texto', 'valor_numero', 'valor_booleano',
        ]


class ProductoSerializer(serializers.ModelSerializer):
    """
    Read serializer for Producto.
    Used for list and detail views. Includes nested marca, tipo_producto,
    campo_valores, and imagenes.
    """
    marca_nombre = serializers.CharField(source='marca.name', read_only=True)
    tipo_producto_nombre = serializers.CharField(source='tipo_producto.nombre', read_only=True)
    campo_valores = ProductoCampoValorSerializer(many=True, read_only=True)
    imagenes = ImagenProductoSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'nombre_base', 'descripcion', 'active',
            'marca', 'marca_nombre',
            'tipo_producto', 'tipo_producto_nombre',
            'campo_valores', 'imagenes',
        ]


class ProductoCampoValorWriteSerializer(serializers.Serializer):
    """
    Nested write serializer for a single campo_valor entry inside create/update.
    Accepts campo_producto id and the raw value; the view resolves which
    value column to populate based on the campo's tipo.
    """
    campo_producto = serializers.IntegerField()
    valor = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class ProductoCreateSerializer(serializers.Serializer):
    """
    Write serializer for creating a Producto.
    Accepts base fields, category IDs, campo_valor entries, and image files
    (passed through request.FILES as image_0, image_1, …, image_9).
    """
    nombre = serializers.CharField(max_length=255)
    nombre_base = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    descripcion = serializers.CharField()
    marca = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())
    tipo_producto = serializers.PrimaryKeyRelatedField(queryset=TipoProducto.objects.all())
    campo_valores = serializers.ListField(
        child=ProductoCampoValorWriteSerializer(), required=False, allow_empty=True
    )

    def _resolve_campo_valor(self, campo, raw_value, association_required=False):
        """
        Given a CampoProducto instance, a raw string value, and the required flag
        from the TipoProductoCampo association (Option B), return a dict with only
        the correct value column populated.
        Raises ValidationError if the association marks the field as required and
        the value is blank.
        """
        tipo = campo.tipo
        valor_texto = None
        valor_numero = None
        valor_booleano = None

        if raw_value is None or str(raw_value).strip() == '':
            if association_required:
                raise serializers.ValidationError(
                    {f'campo_{campo.id}': f'El campo "{campo.nombre}" es obligatorio.'}
                )
            # Optional empty field — store None in all columns
            return {'valor_texto': None, 'valor_numero': None, 'valor_booleano': None}

        if tipo == CampoProducto.TipoCampoChoices.TEXTO:
            valor_texto = str(raw_value)
        elif tipo == CampoProducto.TipoCampoChoices.NUMERO:
            try:
                valor_numero = float(raw_value)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {f'campo_{campo.id}': f'El campo "{campo.nombre}" debe ser un número.'}
                )
        elif tipo == CampoProducto.TipoCampoChoices.BOOLEANO:
            if isinstance(raw_value, bool):
                valor_booleano = raw_value
            else:
                valor_booleano = str(raw_value).lower() in ('true', '1', 'yes', 'on')

        return {
            'valor_texto': valor_texto,
            'valor_numero': valor_numero,
            'valor_booleano': valor_booleano,
        }

    @transaction.atomic
    def create(self, validated_data):
        """
        Create Producto, ProductoCampoValor entries, and ImagenProducto entries atomically.
        Images are read from self.context['request'].FILES.
        The required constraint is read from TipoProductoCampo.required (Option B).
        """
        request = self.context['request']
        campo_valores_data = validated_data.pop('campo_valores', [])
        tipo_producto = validated_data['tipo_producto']

        # Create the Producto
        producto = Producto.objects.create(
            nombre=validated_data['nombre'],
            nombre_base=validated_data.get('nombre_base', '') or '',
            descripcion=validated_data['descripcion'],
            marca=validated_data['marca'],
            tipo_producto=tipo_producto,
            usuario_ultima_modificacion=request.user,
        )

        # Resolve campo IDs into CampoProducto instances
        campo_ids = [entry['campo_producto'] for entry in campo_valores_data]
        campos_map = {
            c.id: c for c in CampoProducto.objects.filter(id__in=campo_ids)
        }
        missing_campos = set(campo_ids) - set(campos_map.keys())
        if missing_campos:
            raise serializers.ValidationError(
                {'campo_valores': f'CampoProducto ID(s) not found: {sorted(missing_campos)}'}
            )

        # Build required map from TipoProductoCampo associations (Option B)
        required_map = {
            assoc.campo_producto_id: assoc.required
            for assoc in TipoProductoCampo.objects.filter(
                tipo_producto=tipo_producto,
                campo_producto_id__in=campo_ids,
            )
        }

        # Create ProductoCampoValor entries
        for entry in campo_valores_data:
            campo = campos_map[entry['campo_producto']]
            association_required = required_map.get(campo.id, False)
            resolved = self._resolve_campo_valor(campo, entry.get('valor'), association_required)
            ProductoCampoValor.objects.create(
                producto=producto,
                campo_producto=campo,
                **resolved,
            )

        # Process uploaded images (image_0 … image_9)
        MAX_IMAGES = 10
        for i in range(MAX_IMAGES):
            img_file = request.FILES.get(f'image_{i}')
            if img_file:
                ImagenProducto.objects.create(
                    producto=producto,
                    url=img_file,
                    orden=i,
                )

        return producto


class ProductoUpdateSerializer(serializers.Serializer):
    """
    Write serializer for updating a Producto.
    All fields are optional. When tipo_producto is changed, existing
    campo_valores are deleted and rebuilt from scratch (caller must warn user).
    Images are updated via remove_images (list of IDs) and new image_N files.
    """
    nombre = serializers.CharField(max_length=255, required=False)
    nombre_base = serializers.CharField(max_length=120, required=False, allow_blank=True)
    descripcion = serializers.CharField(required=False)
    marca = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), required=False)
    tipo_producto = serializers.PrimaryKeyRelatedField(queryset=TipoProducto.objects.all(), required=False)
    campo_valores = serializers.ListField(
        child=ProductoCampoValorWriteSerializer(), required=False, allow_empty=True
    )
    remove_images = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )
    reorder_data = serializers.CharField(required=False, allow_blank=True)

    def _resolve_campo_valor(self, campo, raw_value, association_required=False):
        """
        Given a CampoProducto instance, a raw string value, and the required flag
        from the TipoProductoCampo association (Option B), return a dict with only
        the correct value column populated.
        Raises ValidationError if the association marks the field as required and
        the value is blank.
        """
        tipo = campo.tipo
        valor_texto = None
        valor_numero = None
        valor_booleano = None

        if raw_value is None or str(raw_value).strip() == '':
            if association_required:
                raise serializers.ValidationError(
                    {f'campo_{campo.id}': f'El campo "{campo.nombre}" es obligatorio.'}
                )
            return {'valor_texto': None, 'valor_numero': None, 'valor_booleano': None}

        if tipo == CampoProducto.TipoCampoChoices.TEXTO:
            valor_texto = str(raw_value)
        elif tipo == CampoProducto.TipoCampoChoices.NUMERO:
            try:
                valor_numero = float(raw_value)
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {f'campo_{campo.id}': f'El campo "{campo.nombre}" debe ser un número.'}
                )
        elif tipo == CampoProducto.TipoCampoChoices.BOOLEANO:
            if isinstance(raw_value, bool):
                valor_booleano = raw_value
            else:
                valor_booleano = str(raw_value).lower() in ('true', '1', 'yes', 'on')

        return {
            'valor_texto': valor_texto,
            'valor_numero': valor_numero,
            'valor_booleano': valor_booleano,
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update Producto fields, upsert or rebuild campo_valores, and process image changes.
        """
        import json
        request = self.context['request']

        # --- Base fields ---
        if 'nombre' in validated_data:
            instance.nombre = validated_data['nombre']
        if 'nombre_base' in validated_data:
            instance.nombre_base = validated_data['nombre_base'] or ''
        if 'descripcion' in validated_data:
            instance.descripcion = validated_data['descripcion']
        if 'marca' in validated_data:
            instance.marca = validated_data['marca']

        tipo_changed = (
            'tipo_producto' in validated_data
            and validated_data['tipo_producto'] != instance.tipo_producto
        )
        if 'tipo_producto' in validated_data:
            instance.tipo_producto = validated_data['tipo_producto']

        instance.usuario_ultima_modificacion = request.user
        instance.save()

        # --- Campo valores ---
        if 'campo_valores' in validated_data:
            if tipo_changed:
                # New tipo_producto: wipe all existing values and create fresh
                instance.campo_valores.all().delete()

            campo_valores_data = validated_data['campo_valores']
            campo_ids = [entry['campo_producto'] for entry in campo_valores_data]
            campos_map = {
                c.id: c for c in CampoProducto.objects.filter(id__in=campo_ids)
            }
            missing_campos = set(campo_ids) - set(campos_map.keys())
            if missing_campos:
                raise serializers.ValidationError(
                    {'campo_valores': f'CampoProducto ID(s) not found: {sorted(missing_campos)}'}
                )

            # Build required map from TipoProductoCampo associations (Option B)
            tipo_producto = instance.tipo_producto
            required_map = {
                assoc.campo_producto_id: assoc.required
                for assoc in TipoProductoCampo.objects.filter(
                    tipo_producto=tipo_producto,
                    campo_producto_id__in=campo_ids,
                )
            }

            for entry in campo_valores_data:
                campo = campos_map[entry['campo_producto']]
                association_required = required_map.get(campo.id, False)
                resolved = self._resolve_campo_valor(campo, entry.get('valor'), association_required)
                ProductoCampoValor.objects.update_or_create(
                    producto=instance,
                    campo_producto=campo,
                    defaults=resolved,
                )

        # --- Images: removals ---
        remove_ids = validated_data.get('remove_images', [])
        if remove_ids:
            ImagenProducto.objects.filter(producto=instance, id__in=remove_ids).delete()

        # --- Images: reorder existing ---
        reorder_raw = validated_data.get('reorder_data', '')
        if reorder_raw:
            try:
                reorder_list = json.loads(reorder_raw)
                for entry in reorder_list:
                    ImagenProducto.objects.filter(
                        producto=instance, id=entry['id']
                    ).update(orden=entry['order'])
            except (json.JSONDecodeError, KeyError):
                pass  # Malformed reorder_data is silently ignored

        # --- Images: new uploads ---
        MAX_IMAGES = 10
        current_count = instance.imagenes.count()
        slot = 0
        for i in range(MAX_IMAGES):
            img_file = request.FILES.get(f'image_{i}')
            if img_file and current_count + slot < MAX_IMAGES:
                ImagenProducto.objects.create(
                    producto=instance,
                    url=img_file,
                    orden=current_count + slot,
                )
                slot += 1

        return instance


# ---------------------------------------------------------------------------
# Descuento serializers
# ---------------------------------------------------------------------------

class DescuentoSerializer(serializers.ModelSerializer):
    """
    Read serializer for Descuento.
    Shows product name, condition, and discount price/dates.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)

    class Meta:
        model = Descuento
        fields = ['id', 'producto', 'producto_nombre', 'condicion', 'condicion_display',
                  'precio_descuento', 'fecha_inicio', 'fecha_fin', 'active']


class DescuentoCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer for creating a Descuento for a product + condition.
    Applies to all sin_vender units matching (producto, condicion).
    """
    class Meta:
        model = Descuento
        fields = ['producto', 'condicion', 'precio_descuento', 'fecha_inicio', 'fecha_fin']

    def validate(self, data):
        """Ensure fecha_fin is not before fecha_inicio."""
        if data.get('fecha_fin') and data.get('fecha_inicio'):
            if data['fecha_fin'] < data['fecha_inicio']:
                raise serializers.ValidationError(
                    {'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'}
                )
        return data

    def create(self, validated_data):
        """Create and return a new Descuento."""
        descuento = Descuento.objects.create(**validated_data)
        return descuento


class DescuentoUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer for updating an existing Descuento.
    All fields are optional (partial updates allowed).
    """
    class Meta:
        model = Descuento
        fields = ['precio_descuento', 'fecha_inicio', 'fecha_fin']
        extra_kwargs = {
            'precio_descuento': {'required': False},
            'fecha_inicio': {'required': False},
            'fecha_fin': {'required': False},
        }

    def validate(self, data):
        """Ensure fecha_fin is not before fecha_inicio when both are provided."""
        fecha_inicio = data.get('fecha_inicio', self.instance.fecha_inicio if self.instance else None)
        fecha_fin = data.get('fecha_fin', self.instance.fecha_fin if self.instance else None)
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'}
            )
        return data

    def update(self, instance, validated_data):
        """Update and return the Descuento instance."""
        instance.precio_descuento = validated_data.get('precio_descuento', instance.precio_descuento)
        instance.fecha_inicio = validated_data.get('fecha_inicio', instance.fecha_inicio)
        instance.fecha_fin = validated_data.get('fecha_fin', instance.fecha_fin)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# BajoPedido serializers
# ---------------------------------------------------------------------------

class BajoPedidoSerializer(serializers.ModelSerializer):
    """
    Read serializer for BajoPedido.
    Used for list views. Includes producto name, marca, proveedor name, and descuento.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_marca = serializers.CharField(source='producto.marca.name', read_only=True)
    proveedor_nombre = serializers.SerializerMethodField()
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    descuento = serializers.SerializerMethodField()

    class Meta:
        model = BajoPedido
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_marca',
            'precio', 'condicion', 'condicion_display',
            'estado', 'estado_display',
            'proveedor', 'proveedor_nombre', 'enlace_proveedor',
            'fecha_creacion', 'active', 'descuento',
        ]

    def get_proveedor_nombre(self, obj):
        """Return supplier name or None if no supplier."""
        return obj.proveedor.nombre if obj.proveedor else None

    def get_descuento(self, obj):
        """Return serialized Descuento if one exists for this (producto, condicion) pair, otherwise None."""
        try:
            descuento = Descuento.objects.get(producto=obj.producto, condicion=obj.condicion)
            return DescuentoSerializer(descuento).data
        except Descuento.DoesNotExist:
            return None


class BajoPedidoDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer for BajoPedido.
    Includes all list fields plus nested descuento (if it exists).
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_marca = serializers.CharField(source='producto.marca.name', read_only=True)
    proveedor_nombre = serializers.SerializerMethodField()
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    descuento = serializers.SerializerMethodField()

    class Meta:
        model = BajoPedido
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_marca',
            'precio', 'condicion', 'condicion_display',
            'estado', 'estado_display',
            'proveedor', 'proveedor_nombre', 'enlace_proveedor',
            'fecha_creacion', 'active', 'descuento',
        ]

    def get_proveedor_nombre(self, obj):
        """Return supplier name or None if no supplier."""
        return obj.proveedor.nombre if obj.proveedor else None

    def get_descuento(self, obj):
        """Return serialized Descuento if one exists for this (producto, condicion) pair, otherwise None."""
        try:
            descuento = Descuento.objects.get(producto=obj.producto, condicion=obj.condicion)
            return DescuentoSerializer(descuento).data
        except Descuento.DoesNotExist:
            return None


class BajoPedidoCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer for creating a BajoPedido.
    Accepts producto_id to link the on-demand record to a product.
    precio is required on creation.
    An optional descuento nested object can be provided to create the discount atomically.
    """
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        source='producto',
        write_only=True,
    )
    descuento = DescuentoCreateSerializer(required=False, write_only=True)

    class Meta:
        model = BajoPedido
        fields = [
            'producto_id', 'precio', 'condicion', 'estado',
            'proveedor', 'enlace_proveedor', 'descuento',
        ]
        extra_kwargs = {
            'proveedor': {'required': False, 'allow_null': True},
            'enlace_proveedor': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    @transaction.atomic
    def create(self, validated_data):
        """
        Create BajoPedido and optional Descuento atomically.
        Sets usuario_ultima_modificacion from context['request'].
        """
        request = self.context['request']
        descuento_data = validated_data.pop('descuento', None)

        bajo_pedido = BajoPedido.objects.create(
            usuario_ultima_modificacion=request.user,
            **validated_data,
        )

        if descuento_data:
            Descuento.objects.create(
                producto=bajo_pedido.producto,
                condicion=bajo_pedido.condicion,
                **descuento_data
            )

        return bajo_pedido


class BajoPedidoUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer for updating a BajoPedido.
    All fields are optional. precio is editable here as a manual override.
    An optional descuento nested object will create or replace the linked discount.
    """
    descuento = DescuentoCreateSerializer(required=False, write_only=True)

    class Meta:
        model = BajoPedido
        fields = [
            'precio', 'condicion', 'estado',
            'proveedor', 'enlace_proveedor', 'descuento',
        ]
        extra_kwargs = {
            'precio': {'required': False},
            'condicion': {'required': False},
            'estado': {'required': False},
            'proveedor': {'required': False, 'allow_null': True},
            'enlace_proveedor': {'required': False, 'allow_null': True, 'allow_blank': True},
        }

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Update BajoPedido fields and upsert Descuento if provided.
        Sets usuario_ultima_modificacion from context['request'].
        """
        request = self.context['request']
        descuento_data = validated_data.pop('descuento', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.usuario_ultima_modificacion = request.user
        instance.save()

        if descuento_data is not None:
            try:
                descuento = Descuento.objects.get(
                    producto=instance.producto,
                    condicion=instance.condicion
                )
                # Update existing discount
                descuento.precio_descuento = descuento_data.get('precio_descuento', descuento.precio_descuento)
                descuento.fecha_inicio = descuento_data.get('fecha_inicio', descuento.fecha_inicio)
                descuento.fecha_fin = descuento_data.get('fecha_fin', descuento.fecha_fin)
                descuento.save()
            except Descuento.DoesNotExist:
                # Create new discount
                Descuento.objects.create(
                    producto=instance.producto,
                    condicion=instance.condicion,
                    **descuento_data
                )

        return instance


# ---------------------------------------------------------------------------
# UnidadProducto serializers
# ---------------------------------------------------------------------------

class UnidadProductoSerializer(serializers.ModelSerializer):
    """
    Read serializer for UnidadProducto.
    Used for list and detail views. Includes display labels for choice fields
    and product information for context.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_marca = serializers.CharField(source='producto.marca.name', read_only=True)
    tipo_producto_nombre = serializers.CharField(source='producto.tipo_producto.nombre', read_only=True)
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)
    estado_venta_display = serializers.CharField(source='get_estado_venta_display', read_only=True)
    estado_producto_display = serializers.CharField(source='get_estado_producto_display', read_only=True)

    cliente_garantia_nombre = serializers.CharField(
        source='cliente_garantia.nombre_completo', read_only=True, default=None
    )
    cliente_metodo_aliado_nombre = serializers.CharField(
        source='cliente_metodo_aliado.nombre_completo', read_only=True, default=None
    )
    ciudad_envio_metodo_aliado_nombre = serializers.CharField(
        source='ciudad_envio_metodo_aliado.nombre', read_only=True, default=None
    )
    ciudad_envio_metodo_aliado_departamento = serializers.CharField(
        source='ciudad_envio_metodo_aliado.departamento', read_only=True, default=None
    )

    class Meta:
        model = UnidadProducto
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_marca', 'tipo_producto_nombre',
            'serial', 'condicion', 'condicion_display',
            'estado_venta', 'estado_venta_display',
            'estado_producto', 'estado_producto_display',
            'precio', 'active',
            'cliente_garantia', 'cliente_garantia_nombre',
            'cliente_metodo_aliado', 'cliente_metodo_aliado_nombre',
            'ciudad_envio_metodo_aliado', 'ciudad_envio_metodo_aliado_nombre',
            'ciudad_envio_metodo_aliado_departamento',
            'fecha_solicitud_metodo_aliado', 'fecha_envio_metodo_aliado',
            'fecha_entrega_metodo_aliado',
            'numero_guia_metodo_aliado', 'transportadora_metodo_aliado',
            'notas_metodo_aliado',
        ]


class UnidadProductoCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer for creating a new UnidadProducto.
    Requires producto_id, condicion, serial, estado_venta, estado_producto, and precio.
    Sets usuario_ultima_modificacion from context['request'].
    Serial uniqueness is enforced at the model level; the serializer surfaces the error.
    """
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(),
        source='producto',
        write_only=True,
    )

    class Meta:
        model = UnidadProducto
        fields = ['producto_id', 'serial', 'condicion', 'estado_venta', 'estado_producto', 'precio']
        extra_kwargs = {
            'condicion': {'required': True},
            'estado_venta': {'required': True},
            'estado_producto': {'required': True},
        }

    def validate_precio(self, value):
        """Ensure price is a positive number."""
        if value <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return value

    def create(self, validated_data):
        """Create and return a new UnidadProducto instance."""
        request = self.context['request']
        unidad = UnidadProducto.objects.create(
            usuario_ultima_modificacion=request.user,
            **validated_data,
        )
        return unidad


class UnidadProductoUpdateSerializer(serializers.ModelSerializer):
    """
    Write serializer for updating an existing UnidadProducto.
    All fields are optional (partial updates allowed).
    Units with estado_venta 'vendido' or 'separado' cannot be edited.
    Sets usuario_ultima_modificacion from context['request'].
    """
    LOCKED_STATES = ('vendido', 'separado')

    class Meta:
        model = UnidadProducto
        fields = [
            'serial', 'condicion', 'estado_venta', 'estado_producto', 'precio',
            'cliente_garantia',
            'cliente_metodo_aliado', 'ciudad_envio_metodo_aliado',
            'fecha_solicitud_metodo_aliado', 'fecha_envio_metodo_aliado',
            'fecha_entrega_metodo_aliado',
            'numero_guia_metodo_aliado', 'transportadora_metodo_aliado',
            'notas_metodo_aliado',
        ]
        extra_kwargs = {
            'serial': {'required': False},
            'condicion': {'required': False},
            'estado_venta': {'required': False},
            'estado_producto': {'required': False},
            'precio': {'required': False},
            'cliente_garantia': {'required': False},
            'cliente_metodo_aliado': {'required': False},
            'ciudad_envio_metodo_aliado': {'required': False},
            'fecha_solicitud_metodo_aliado': {'required': False},
            'fecha_envio_metodo_aliado': {'required': False},
            'fecha_entrega_metodo_aliado': {'required': False},
            'numero_guia_metodo_aliado': {'required': False},
            'transportadora_metodo_aliado': {'required': False},
            'notas_metodo_aliado': {'required': False},
        }

    def validate(self, attrs):
        if self.instance and self.instance.estado_venta in self.LOCKED_STATES:
            raise serializers.ValidationError(
                f'Esta unidad tiene estado "{self.instance.get_estado_venta_display()}". '
                'Elimine la venta o separación asociada antes de editarla.'
            )
        # Prevent manually setting estado_venta to vendido/separado
        new_estado = attrs.get('estado_venta')
        if new_estado and new_estado in self.LOCKED_STATES:
            raise serializers.ValidationError({
                'estado_venta': 'Este estado solo se asigna automáticamente al registrar una venta o separación.'
            })
        # Serial required to move estado_producto away from 'viajando'
        new_estado_producto = attrs.get('estado_producto')
        if new_estado_producto and new_estado_producto != 'viajando' and self.instance:
            serial = attrs.get('serial', self.instance.serial)
            if serial.startswith('SIN-SERIAL-'):
                raise serializers.ValidationError({
                    'estado_producto': 'Debe registrar el serial antes de cambiar el estado del producto.'
                })
        return attrs

    def validate_precio(self, value):
        """Ensure price is a positive number when provided."""
        if value <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return value

    def update(self, instance, validated_data):
        """Update and return the UnidadProducto instance."""
        from django.utils import timezone
        request = self.context['request']
        old_estado_producto = instance.estado_producto
        old_estado_venta = instance.estado_venta

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Auto-set fecha_solicitud when entering solicitud_metodo_aliado
        if (instance.estado_venta == 'solicitud_metodo_aliado'
                and old_estado_venta != 'solicitud_metodo_aliado'
                and not instance.fecha_solicitud_metodo_aliado):
            instance.fecha_solicitud_metodo_aliado = timezone.now()

        # Auto-set fecha_entrega when delivering a método aliado unit
        if (instance.estado_venta == 'solicitud_metodo_aliado'
                and instance.estado_producto == 'entregado'
                and old_estado_producto != 'entregado'
                and not instance.fecha_entrega_metodo_aliado):
            instance.fecha_entrega_metodo_aliado = timezone.now()

        instance.usuario_ultima_modificacion = request.user
        instance.save()

        # Sync OrdenCompra.estado_logistico when unit transitions viajando → en_stock
        if old_estado_producto == 'viajando' and instance.estado_producto == 'en_stock':
            from purchases.models import OrdenCompra
            try:
                orden = OrdenCompra.objects.get(unidad_producto=instance)
                orden.estado_logistico = 'en_oficina'
                orden.save(update_fields=['estado_logistico'])
            except OrdenCompra.DoesNotExist:
                pass

        return instance


class UnidadReparacionSerializer(serializers.ModelSerializer):
    """
    Read serializer for the repair listing. Exposes unit info plus a derived
    `origen` field (stock/venta/separacion) computed from the existing
    ItemVenta / Separacion relations — no new storage required.
    """
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_marca = serializers.CharField(source='producto.marca.name', read_only=True)
    estado_venta_display = serializers.CharField(source='get_estado_venta_display', read_only=True)
    estado_producto_display = serializers.CharField(source='get_estado_producto_display', read_only=True)
    origen = serializers.SerializerMethodField()
    venta_id = serializers.SerializerMethodField()
    separacion_id = serializers.SerializerMethodField()
    cliente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = UnidadProducto
        fields = [
            'id', 'serial', 'condicion', 'precio',
            'producto_nombre', 'producto_marca',
            'estado_venta', 'estado_venta_display',
            'estado_producto', 'estado_producto_display',
            'descripcion_dano', 'fecha_reporte_dano',
            'origen', 'venta_id', 'separacion_id', 'cliente_nombre',
        ]

    def _active_item_venta(self, obj):
        return obj.items_venta.filter(active=True).order_by('-id').first()

    def _active_separacion(self, obj):
        return obj.separaciones.filter(active=True).exclude(
            estado='cancelada'
        ).order_by('-id').first()

    def get_origen(self, obj):
        if self._active_item_venta(obj):
            return 'venta'
        if self._active_separacion(obj):
            return 'separacion'
        if obj.cliente_metodo_aliado_id and not obj.fecha_entrega_metodo_aliado:
            return 'metodo_aliado'
        return 'stock'

    def get_venta_id(self, obj):
        item = self._active_item_venta(obj)
        return item.venta_id if item else None

    def get_separacion_id(self, obj):
        sep = self._active_separacion(obj)
        return sep.id if sep else None

    def get_cliente_nombre(self, obj):
        item = self._active_item_venta(obj)
        if item and item.venta and item.venta.cliente:
            return item.venta.cliente.nombre_completo
        sep = self._active_separacion(obj)
        if sep and sep.cliente:
            return sep.cliente.nombre_completo
        if obj.cliente_metodo_aliado_id and not obj.fecha_entrega_metodo_aliado:
            return obj.cliente_metodo_aliado.nombre_completo
        return None
