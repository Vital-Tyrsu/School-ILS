# library/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Reservation, BookCopy, Borrowing

@receiver(post_save, sender=Reservation)
def assign_copy_to_reservation(sender, instance, created, **kwargs):
    if created and instance.status == 'pending':
        available_copy = BookCopy.objects.filter(book=instance.book, status='available').first()
        if available_copy:
            instance.copy = available_copy
            instance.status = 'assigned'
            instance.save()
            available_copy.status = 'reserved'
            available_copy.save()

@receiver(post_save, sender=BookCopy)
def check_pending_reservations(sender, instance, **kwargs):
    if instance.status == 'available':
        pending_reservation = Reservation.objects.filter(book=instance.book, status='pending').first()
        if pending_reservation:
            pending_reservation.copy = instance
            pending_reservation.status = 'assigned'
            pending_reservation.save()
            instance.status = 'reserved'
            instance.save()

@receiver(post_save, sender=Reservation)
def send_reservation_email(sender, instance, created, **kwargs):
    if created and instance.status == 'pending':
        # Email when reservation is created
        subject = 'Reservation Confirmation'
        message = (
            f'Dear {instance.user.username},\n\n'
            f'Your reservation for "{instance.book.title}" has been received and is pending.\n'
            f'We will notify you when a copy is available for pickup.\n\n'
            f'Thank you!'
        )
        send_mail(subject, message, 'from@example.com', [instance.user.email], fail_silently=True)

    elif instance.status == 'picked_up':
        # Email when book is picked up, including borrowing period
        borrowing = Borrowing.objects.filter(reservation=instance).first()
        if borrowing:
            due_date = borrowing.due_date.strftime('%Y-%m-%d')
            subject = 'Book Pickup Confirmation'
            message = (
                f'Dear {instance.user.username},\n\n'
                f'You have successfully picked up "{instance.book.title}".\n'
                f'Please return it by {due_date}.\n\n'
                f'Thank you!'
            )
            send_mail(subject, message, 'from@example.com', [instance.user.email], fail_silently=True)