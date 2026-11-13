import random
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import NotificationLog, PriceAlert
from .permissions import IsAdminUser
from .serializers import PriceAlertSerializer, RegisterSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = RefreshToken.for_user(user)
        return Response(
            {"username": user.username, "access": str(token.access_token),
             "role": user.profile.role},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response({"detail": "Invalid credentials."},
                            status=status.HTTP_401_UNAUTHORIZED)
        token = RefreshToken.for_user(user)
        return Response({"username": user.username, "access": str(token.access_token),
                         "role": user.profile.role}, status=status.HTTP_200_OK)


class AlertListCreateView(generics.ListCreateAPIView):
    serializer_class = PriceAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        alert = get_object_or_404(PriceAlert, id=id)
        if alert.user_id != request.user.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alert.status = PriceAlert.Status.INACTIVE
        alert.save(update_fields=["status"])
        return Response({"status": "inactive"}, status=status.HTTP_200_OK)


MOCK_PRICES = {
    "DEL-BOM": (3000, 7000),
    "BLR-HYD": (1500, 4000),
    "DEL-BLR": (4000, 9000),
    "BOM-GOA": (2000, 5000),
}

def get_flight_price(request):
    route = request.GET.get("route", "")
    price_range = MOCK_PRICES.get(route)
    if not price_range:
        return JsonResponse({"error": "Route not found"}, status=404)
    return JsonResponse({"route": route, "price": random.randint(*price_range)})


class AdminSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        alert_counts = PriceAlert.objects.aggregate(
            total_alerts=Count("id"),
            active_alerts=Count("id", filter=Q(status=PriceAlert.Status.ACTIVE)),
            triggered_alerts=Count("id", filter=Q(status=PriceAlert.Status.TRIGGERED)),
        )
        notification_counts = NotificationLog.objects.aggregate(
            total_notifications=Count("id")
        )
        route_rows = (
            PriceAlert.objects.values("origin", "destination")
            .annotate(alert_count=Count("id"))
            .order_by("-alert_count")[:10]
        )
        top_routes = [
            {"route": f"{row['origin']}-{row['destination']}",
             "alert_count": row["alert_count"]}
            for row in route_rows
        ]
        return Response({**alert_counts, **notification_counts, "top_routes": top_routes})
