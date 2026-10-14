from django.contrib.auth import get_user_model
from django.core import signing
from rest_framework.serializers import ValidationError

User = get_user_model()
SALT = "email-verification-pre-token"
ERROR = "pre_token yaroqsiz yoki muddati tugagan"
PRE_TOKEN_LIFETIME_SECONDS = 30 * 60


def make_pre_token(user_id):
    return signing.dumps({"user_id": user_id}, salt=SALT)


def get_user(pre_token):
    try:
        data = signing.loads(
            pre_token,
            salt=SALT,
            max_age=PRE_TOKEN_LIFETIME_SECONDS,
        )
        user_id = data["user_id"]
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        raise ValidationError({"detail": ERROR})

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        raise ValidationError({"detail": ERROR})
    return user
