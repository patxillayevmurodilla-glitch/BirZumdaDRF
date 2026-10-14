import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework.serializers import ValidationError

from ..models import EmailCode

ERROR = "Kod topilmadi, muddati tugagan yoki urinishlar tugagan"
NOT_CONFIRMED = "Tasdiqlash kodi tasdiqlanmagan yoki muddati tugagan"


@transaction.atomic
def send_verification_code(user):
    # 100000-999999 oralig'idagi olti xonali tasodifiy kod.
    code = str(secrets.randbelow(900000) + 100000)
    EmailCode.objects.filter(user=user).delete()
    record = EmailCode.objects.create(user=user, code=code)

    # Email yuborilmasa transaction rollback bo'ladi va eski kod saqlanib qoladi.
    send_mail(
        subject="Email tasdiqlash kodi",
        message=f"Tasdiqlash kodingiz: {code}\nKod 5 daqiqa davomida amal qiladi.",
        from_email=settings.DEFAULT_FROM_EMAIL or None,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return record


def confirm_code(user, code):
    record = EmailCode.objects.filter(user=user).first()

    if record is None or record.is_expired():
        raise ValidationError({"detail": ERROR})
    if record.attempts >= EmailCode.MAX_ATTEMPTS:
        raise ValidationError({"detail": ERROR})

    if not secrets.compare_digest(record.code, code):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        raise ValidationError({"detail": "Kod noto'g'ri"})

    record.is_confirmed = True
    record.save(update_fields=["is_confirmed"])


def finish_code(user):
    record = EmailCode.objects.filter(user=user, is_confirmed=True).first()
    if record is None or record.is_expired():
        raise ValidationError({"detail": NOT_CONFIRMED})
    record.delete()
