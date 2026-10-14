
from django.contrib import admin
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from app.views import (
    ForgotPasswordView,
    LogoutView,
    MeView,
    ProductCreateView,
    ProductDeleteView,
    ProductListCreateView,
    RegisterView,
    ResetPasswordView,
    ResendCodeView,
    VerifyEmailView,
    BlogListCreateAPIView,
    BlogDetailAPIView, ProductListAPIView,
)

schema_view = get_schema_view(
    openapi.Info(
        title="Homework API",
        default_version="v1",
        description=(
            "Authentication, email verification, JWT, "
            "products and blogs API."
        ),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Swagger documentation
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),

    # Authentication
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-code/", ResendCodeView.as_view(), name="resend-code"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),

    # Products
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/create/", ProductCreateView.as_view(), name="product-create"),

    path("products/filter/", ProductListAPIView.as_view(), name="product-create"),

    path("products/<int:pk>/delete/", ProductDeleteView.as_view(), name="product-delete"),

    # Blogs
    path("blogs/", BlogListCreateAPIView.as_view(), name="blog-list-create"),
    path("blogs/<int:pk>/", BlogDetailAPIView.as_view(), name="blog-detail"),
]
