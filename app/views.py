from rest_framework.generics import ListAPIView
import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from app.filters import ProductFilter


from .models import EmailCode, Product, User
from .serializers import (
    ForgotPasswordSerializer,
    LogoutSerializer,
    ResetPasswordSerializer,
    ProductModelSerializer,
    RegisterSerializer,
    ResendCodeSerializer,
    VerifyEmailSerializer,
)
from .services import confirm_code, finish_code, send_verification_code
from .services.pre_token import get_user, make_pre_token
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from app.models import Blog
from app.serializers import BlogModelSerializer




class ProductListAPIView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductModelSerializer

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_class = ProductFilter
    search_fields = ['title']
    ordering_fields = ['title', 'price']

class BlogListCreateAPIView(ListCreateAPIView):
    queryset = Blog.objects.all().order_by("-id")
    serializer_class = BlogModelSerializer


class BlogDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogModelSerializer

logger = logging.getLogger(__name__)
RESEND_INTERVAL = timedelta(seconds=60)


class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductModelSerializer
    permission_classes = [IsAuthenticated]


class ProductDeleteView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductModelSerializer
    permission_classes = [IsAuthenticated]


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            send_verification_code(user)
        except Exception:
            logger.exception("Email verification message could not be sent")
            user.delete()
            return Response(
                {"detail": "Tasdiqlash emailini yuborib bo'lmadi. Email sozlamalarini tekshiring."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "detail": "Tasdiqlash kodi yuborildi.",
                "email": user.email,
                "pre_token": make_pre_token(user.pk),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(generics.GenericAPIView):
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = get_user(data["pre_token"])

        if user.is_active:
            return Response({"detail": "Email avval tasdiqlangan."}, status=status.HTTP_400_BAD_REQUEST)

        confirm_code(user, data["code"])
        finish_code(user)
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": "Email tasdiqlandi. Endi login qilishingiz mumkin."})


class ResendCodeView(generics.GenericAPIView):
    serializer_class = ResendCodeSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user(serializer.validated_data["pre_token"])

        if user.is_active:
            return Response({"detail": "Email allaqachon tasdiqlangan."}, status=status.HTTP_400_BAD_REQUEST)

        record = EmailCode.objects.filter(user=user).first()
        now = timezone.now()
        if record and now - record.created_at < RESEND_INTERVAL:
            return Response(
                {"detail": "Yangi kodni 60 soniyadan keyin so'rashingiz mumkin."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            send_verification_code(user)
        except Exception:
            logger.exception("Verification email could not be resent")
            return Response(
                {"detail": "Email yuborilmadi. Email sozlamalarini tekshiring."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"detail": "Yangi kod yuborildi.", "pre_token": make_pre_token(user.pk)})


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email, is_active=True).first()

        # Bir email manzili mavjudligini javobdan aniqlab bo'lmasligi uchun
        # topilmagan/tekshirilmagan emailga ham bir xil javob qaytariladi.
        if user:
            record = EmailCode.objects.filter(user=user).first()
            if record is None or timezone.now() - record.created_at >= RESEND_INTERVAL:
                try:
                    send_verification_code(user)
                except Exception:
                    logger.exception("Password reset email could not be sent")

        return Response({
            "detail": "Agar email faol akkauntga tegishli bo'lsa, tiklash kodi yuborildi."
        })


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.filter(email=data["email"], is_active=True).first()

        if user is None:
            return Response(
                {"detail": "Kod noto'g'ri yoki muddati tugagan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            confirm_code(user, data["code"])
            finish_code(user)
        except ValidationError:
            return Response(
                {"detail": "Kod noto'g'ri yoki muddati tugagan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])

        # Eski refresh tokenlar qayta ishlatilmasin.
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)

        return Response({"detail": "Parol yangilandi. Qaytadan login qiling."})


class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"detail": "Refresh token yaroqsiz yoki bekor qilingan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Tizimdan chiqildi."}, status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({"id": user.pk, "email": user.email, "first_name": user.first_name})

