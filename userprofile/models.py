from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

bd_phone = RegexValidator(
    regex=r'^(\+?88)?01[3-9]\d{8}$',
    message='Enter a valid Bangladeshi mobile number, for example 01712345678.',
)


def check_photo_size(photo):
    if photo and photo.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError('Photo must be smaller than 3 MB.')


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(upload_to='profile_pics/', blank=True, validators=[check_photo_size])
    full_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=14, blank=True, validators=[bd_phone])
    address = models.TextField(blank=True)
    home_city = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f'{self.user.username} profile'

    @property
    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    # Every new user gets an empty profile automatically
    if created:
        UserProfile.objects.create(user=instance)


def is_admin(user):
    """Admins are staff users. Everyone else is a traveler."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)
