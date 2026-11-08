"""
TourVibe REST API

Everyone can read places, packages and reviews, and use the planner.
Logged-in users manage their own orders, reviews and plans.
Admins (staff) can add or change content and confirm or cancel orders.
Login with the browser session or a token: header "Authorization: Token <key>".
"""
from django.core.exceptions import ValidationError
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse

from booking.models import Order, TourPackage
from booking.services import change_status, place_order
from planner.engine import PlannerError, estimate_trip, recommend
from tour.models import Category, Division, Review, TourDestination
from tour.views import search_destinations
from userprofile.models import is_admin

from . import serializers as s


class AdminCanEdit(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or is_admin(request.user)


class OwnerCanEdit(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or obj.user == request.user or is_admin(request.user)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_home(request, format=None):
    links = ['destinations', 'categories', 'divisions', 'packages', 'reviews', 'orders', 'plans']
    data = {name: reverse(f'api-{name}-list', request=request, format=format) for name in links}
    data['planner estimate (POST)'] = reverse('api-estimate', request=request, format=format)
    data['planner recommend (POST)'] = reverse('api-recommend', request=request, format=format)
    data['get token (POST)'] = reverse('api-token', request=request, format=format)
    return Response(data)


class DivisionViewSet(viewsets.ModelViewSet):
    queryset = Division.objects.all()
    serializer_class = s.DivisionSerializer
    permission_classes = [AdminCanEdit]
    pagination_class = None


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = s.CategorySerializer
    permission_classes = [AdminCanEdit]
    pagination_class = None


class DestinationViewSet(viewsets.ModelViewSet):
    """Filters: ?q= &division=<slug> &category=<slug> &month=1-12 &max_price= &sort=name|rating|cheap|expensive|popular"""
    serializer_class = s.DestinationSerializer
    permission_classes = [AdminCanEdit]
    lookup_field = 'slug'

    def get_queryset(self):
        if self.action == 'list':
            return search_destinations(self.request.query_params)[1]
        places = TourDestination.objects.select_related('division', 'category').with_rating()
        if not is_admin(self.request.user):
            places = places.filter(is_active=True)
        return places


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = s.ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, OwnerCanEdit]

    def get_queryset(self):
        reviews = Review.objects.select_related('user', 'tour')
        if self.request.query_params.get('tour'):
            reviews = reviews.filter(tour__slug=self.request.query_params['tour'])
        return reviews

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PackageViewSet(viewsets.ModelViewSet):
    serializer_class = s.PackageSerializer
    permission_classes = [AdminCanEdit]
    lookup_field = 'slug'

    def get_queryset(self):
        packages = TourPackage.objects.prefetch_related('destinations')
        return packages if is_admin(self.request.user) else packages.filter(is_active=True)


class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    serializer_class = s.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference'

    def get_queryset(self):
        orders = Order.objects.select_related('user').prefetch_related('items__package')
        return orders if is_admin(self.request.user) else orders.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            order = place_order(request.user, [(i['package'], i['travelers']) for i in data['items']],
                                data['contact_name'], data['contact_phone'], data.get('note', ''))
        except ValidationError as error:
            return Response({'detail': error.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, reference=None):
        order = self.get_object()
        if not order.can_cancel:
            return Response({'detail': 'This order can no longer be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        change_status(order, Order.CANCELLED)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, reference=None):
        if not is_admin(request.user):
            return Response({'detail': 'Only admins can change order status.'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        body = s.StatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            change_status(order, body.validated_data['status'])
        except ValidationError as error:
            return Response({'detail': error.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)


class TripPlanViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    serializer_class = s.TripPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.trip_plans.prefetch_related('places')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def planner_estimate(request):
    """Body example: {"places": ["srimangal", "jaflong"], "days": 4, "travelers": 2, "budget": "STANDARD", "transport": "TRAIN"}"""
    body = s.EstimateSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    d = body.validated_data
    try:
        return Response(estimate_trip(d['places'], d['days'], d['travelers'], d['budget'], d['transport']))
    except PlannerError as error:
        return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def planner_recommend(request):
    """Body example: {"month": 12, "daily_budget": 3000, "categories": [1, 3], "max_km": 400}"""
    body = s.RecommendSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    d = body.validated_data
    results = recommend(TourDestination.objects.active(), d['month'], d.get('daily_budget'), d.get('categories'),
                        d.get('max_km'), d['limit'])
    return Response([{'place': s.DestinationSerializer(r['place']).data, 'score': r['score'], 'reasons': r['reasons']}
                     for r in results])
