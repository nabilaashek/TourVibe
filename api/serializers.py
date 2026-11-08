from django.utils import timezone
from rest_framework import serializers

from booking.models import Order, OrderItem, TourPackage, Transport
from planner.models import TripPlan
from tour.models import Category, Division, Review, TourDestination
from userprofile.models import bd_phone


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = ['id', 'name', 'bangla_name', 'slug']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon']


class DestinationSerializer(serializers.ModelSerializer):
    division = serializers.SlugRelatedField(slug_field='slug', queryset=Division.objects.all())
    category = serializers.SlugRelatedField(slug_field='slug', queryset=Category.objects.all())
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField(read_only=True, default=0)
    km_from_dhaka = serializers.IntegerField(read_only=True)

    class Meta:
        model = TourDestination
        fields = ['id', 'name', 'slug', 'division', 'district', 'category', 'short_description', 'description',
                  'highlights', 'tips', 'best_months', 'price_per_day', 'entry_fee', 'latitude', 'longitude',
                  'avg_rating', 'review_count', 'km_from_dhaka', 'is_featured', 'is_active']
        read_only_fields = ['slug']

    def get_avg_rating(self, obj):
        value = getattr(obj, 'avg_rating', None)
        return round(value, 1) if value is not None else None

    def validate_best_months(self, value):
        try:
            months = [int(m) for m in value.replace(' ', '').split(',') if m]
        except ValueError:
            months = []
        if not months or any(m < 1 or m > 12 for m in months):
            raise serializers.ValidationError('Write month numbers from 1 to 12, separated by commas.')
        return ','.join(str(m) for m in months)


class ReviewSerializer(serializers.ModelSerializer):
    tour = serializers.SlugRelatedField(slug_field='slug', queryset=TourDestination.objects.active())
    user = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'tour', 'user', 'rating', 'title', 'comment', 'visited_on', 'created_at']
        read_only_fields = ['created_at']

    def validate_visited_on(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('Visit date cannot be in the future.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if self.instance is None and Review.objects.filter(user=user, tour=attrs['tour']).exists():
            raise serializers.ValidationError('You already reviewed this place.')
        if self.instance is not None and 'tour' in attrs and attrs['tour'] != self.instance.tour:
            raise serializers.ValidationError({'tour': 'You cannot move a review to another place.'})
        return attrs


class PackageSerializer(serializers.ModelSerializer):
    destinations = serializers.SlugRelatedField(slug_field='slug', many=True, queryset=TourDestination.objects.all())
    seats_left = serializers.IntegerField(read_only=True)
    end_date = serializers.DateField(read_only=True)

    class Meta:
        model = TourPackage
        fields = ['id', 'title', 'slug', 'summary', 'description', 'destinations', 'start_city', 'transport', 'days',
                  'price_per_person', 'total_seats', 'seats_left', 'start_date', 'end_date', 'includes', 'excludes',
                  'is_active']
        read_only_fields = ['slug']


class OrderItemSerializer(serializers.ModelSerializer):
    package = serializers.SlugRelatedField(slug_field='slug', queryset=TourPackage.objects.filter(is_active=True))
    unit_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['package', 'travelers', 'unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    user = serializers.CharField(source='user.username', read_only=True)
    contact_phone = serializers.CharField(max_length=14, validators=[bd_phone])

    class Meta:
        model = Order
        fields = ['reference', 'user', 'items', 'contact_name', 'contact_phone', 'note', 'status', 'total_price',
                  'created_at']
        read_only_fields = ['reference', 'status', 'total_price', 'created_at']

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('Add at least one tour package.')
        slugs = [i['package'].slug for i in items]
        if len(slugs) != len(set(slugs)):
            raise serializers.ValidationError('Each package can appear only once.')
        return items


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)


class TripPlanSerializer(serializers.ModelSerializer):
    places = serializers.SlugRelatedField(slug_field='slug', many=True, read_only=True)

    class Meta:
        model = TripPlan
        fields = ['id', 'title', 'places', 'start_date', 'days', 'travelers', 'budget', 'transport',
                  'estimated_total', 'details', 'created_at']


class EstimateSerializer(serializers.Serializer):
    places = serializers.SlugRelatedField(slug_field='slug', many=True, queryset=TourDestination.objects.active())
    days = serializers.IntegerField(min_value=1, max_value=30)
    travelers = serializers.IntegerField(min_value=1, max_value=20)
    budget = serializers.ChoiceField(choices=TripPlan.BUDGET_CHOICES, default='STANDARD')
    transport = serializers.ChoiceField(choices=Transport.choices, default='BUS')


class RecommendSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    daily_budget = serializers.IntegerField(min_value=500, max_value=100000, required=False)
    categories = serializers.ListField(child=serializers.IntegerField(), required=False)
    max_km = serializers.IntegerField(min_value=10, max_value=1000, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=6)
