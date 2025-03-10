from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.contrib import messages

# User Model
class User(AbstractUser):
    ROLE_CHOICES = (('student', 'Student'), ('teacher', 'Teacher'), ('admin', 'Admin'))
    email = models.EmailField(unique=True, verbose_name="Email Address")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="User Role")

    def __str__(self):
        return self.username

# Book Model
class Book(models.Model):
    title = models.CharField(max_length=255, verbose_name="Book Title")
    author = models.CharField(max_length=255, verbose_name="Author Name")
    isbn = models.CharField(
        max_length=13, unique=True, null=True, blank=True,
        verbose_name="ISBN", help_text="Enter ISBN (e.g., 9780451524935)"
    )
    publication_year = models.IntegerField(
        null=True, blank=True, verbose_name="Publication Year", help_text="e.g., 1949"
    )
    genre = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Genre", help_text="e.g., Fiction"
    )
    publisher = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Publisher", help_text="e.g., Penguin Books"
    )

    def __str__(self):
        return self.title

# BookCopy Model
class BookCopy(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="Book")
    condition = models.CharField(
        max_length=50, default='good', verbose_name="Condition", help_text="e.g., good, damaged"
    )
    location = models.CharField(
        max_length=50,
        validators=[RegexValidator(r'^[A-Z0-9]+-[A-Z]-[0-9]{2}$', message='Use format like L1-A-12')],
        verbose_name="Location",
        help_text="Use format Room-Shelf-Number (e.g., L1-A-12)"
    )

    def __str__(self):
        return f"{self.book.title} - {self.location}"

# Reservation Model
class Reservation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="Book")
    copy = models.ForeignKey(BookCopy, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Copy")
    reservation_date = models.DateTimeField(auto_now_add=True, verbose_name="Reservation Date")
    expiration_date = models.DateTimeField(verbose_name="Expiration Date", help_text="e.g., 2025-03-13")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Status"
    )

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    def check_expiration(self):
        if self.status == 'assigned' and self.expiration_date < timezone.now():
            self.status = 'expired'
            self.copy = None
            self.save()
            return True
        return False

    def assign_available_copy(self):
        if self.status == 'pending':
            available_copies = BookCopy.objects.filter(book=self.book).exclude(
                id__in=Reservation.objects.filter(
                    status__in=['assigned', 'picked_up']
                ).values_list('copy_id', flat=True)
            ).exclude(
                id__in=Borrowing.objects.filter(return_date__isnull=True).values_list('copy_id', flat=True)
            )
            if available_copies.exists():
                self.copy = available_copies.first()
                self.status = 'assigned'
                self.save()
                return True
        return False

# Borrowing Model
class Borrowing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    copy = models.ForeignKey(BookCopy, on_delete=models.CASCADE, verbose_name="Copy")
    borrow_date = models.DateTimeField(auto_now_add=True, verbose_name="Borrow Date")
    due_date = models.DateTimeField(verbose_name="Due Date")
    return_date = models.DateTimeField(null=True, blank=True, verbose_name="Return Date")
    renewal_count = models.IntegerField(default=0, verbose_name="Renewal Count")

    def __str__(self):
        return f"{self.user.username} - {self.copy}"

    def clean(self):
        """
        Validate the due_date change to enforce renewal limits.
        """
        if self.pk:
            old_instance = Borrowing.objects.get(pk=self.pk)
            if old_instance.due_date != self.due_date:
                if old_instance.renewal_count >= 2:
                    raise ValidationError({
                        'due_date': ["Cannot extend due date: Maximum number of renewals (2) reached."]
                    })
                if old_instance.return_date is not None:
                    raise ValidationError({
                        'due_date': ["Cannot extend due date: Borrowing has been returned."]
                    })

    def return_book(self):
        if self.return_date is None:
            self.return_date = timezone.now()
            self.save()

    def renew(self):
        """
        Renew the borrowing by extending the due_date by 14 days and incrementing renewal_count.
        Raises ValidationError if conditions are not met.
        """
        if self.renewal_count >= 2:
            raise ValidationError("Maximum number of renewals (2) reached.")
        if self.return_date is not None:
            raise ValidationError("Cannot renew a borrowing that has been returned.")
        self.due_date += timedelta(days=14)
        self.renewal_count += 1
        self.save()
        return True

# Signals for Reservation
@receiver(pre_save, sender=Reservation)
def capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Reservation.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Reservation.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Reservation)
def handle_picked_up(sender, instance, **kwargs):
    if (instance.status == 'picked_up' and 
        instance.copy and 
        getattr(instance, '_old_status', None) != 'picked_up'):
        Borrowing.objects.create(
            user=instance.user,
            copy=instance.copy,
            borrow_date=timezone.now(),
            due_date=timezone.now() + timezone.timedelta(days=14),
            renewal_count=0
        )

@receiver(post_save, sender=Reservation)
def try_assign_copy(sender, instance, created, **kwargs):
    if created or instance.status == 'pending':
        instance.assign_available_copy()

# Remove the old handle_manual_renewal signal since we're using clean() now