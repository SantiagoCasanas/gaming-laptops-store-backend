from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    """Custom manager for User model where email is the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model where email is used as username.
    """
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(
        verbose_name='first name',
        max_length=150,
        blank=True
    )
    last_name = models.CharField(
        verbose_name='last name',
        max_length=150,
        blank=True
    )
    creation_date = models.DateTimeField(
        verbose_name='creation date',
        auto_now_add=True
    )
    last_access = models.DateTimeField(
        verbose_name='last access',
        auto_now=True
    )
    is_active = models.BooleanField(
        verbose_name='active',
        default=True
    )
    is_staff = models.BooleanField(
        verbose_name='staff status',
        default=False
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required by USERNAME_FIELD

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-creation_date']

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the full name of the user."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip() or self.email

    def get_short_name(self):
        """Return the short name of the user."""
        return self.first_name or self.email
