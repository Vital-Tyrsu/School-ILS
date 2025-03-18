from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Reservation, BookCopy, Borrowing
from django.contrib.auth.models import User
from django.utils import timezone

@receiver(post_save, sender=BookCopy)
def check_pending_reservations(sender, instance, **kwargs):
    if kwargs.get('raw', False):
        print("Skipping raw data load")
        return
    print(f"Signal triggered for copy {instance.id}, status: {instance.status}, created: {kwargs.get('created', False)}")
    if instance.status == 'available':
        pending_reservations = Reservation.objects.filter(
            book=instance.book, status='pending'
        ).order_by('reservation_date')
        print(f"Found {pending_reservations.count()} pending reservations for book {instance.book.title}")
        if pending_reservations.exists():
            reservation = pending_reservations.first()
            print(f"Assigning copy {instance.id} to reservation {reservation.id} for user {reservation.user.username}")
            reservation.copy = instance
            reservation.status = 'assigned'
            reservation.save(update_fields=['copy', 'status'])
            instance.status = 'reserved'
            instance.save(update_fields=['status'])
            print(f"Successfully assigned copy {instance.id} to reservation {reservation.id}")
        else:
            print(f"No pending reservations found for book {instance.book.title}")
    else:
        print(f"Copy {instance.id} status is {instance.status}, not processing")

@receiver(post_save, sender=Reservation)
def try_assign_copy(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):  # Skip during migrations/fixtures
        return
    print(f"try_assign_copy: Running for reservation {instance.id}, created={created}, status={instance.status}")
    if created or instance.status == 'pending':
        assigned = instance.assign_available_copy()
        print(f"try_assign_copy: Assignment result for reservation {instance.id}: {assigned}")
    else:
        print(f"try_assign_copy: Skipped for reservation {instance.id}, not pending")


@receiver(post_save, sender=Borrowing)
def try_assign_after_return(sender, instance, **kwargs):
    if kwargs.get('raw', False):  # Skip during migrations/fixtures
        return
    if instance.return_date:  # Only trigger if the book has been returned
        print(f"try_assign_after_return: Borrowing {instance.id} returned, checking for pending reservations")
        pending_reservations = Reservation.objects.filter(status='pending').order_by('reservation_date')
        for reservation in pending_reservations:
            print(f"try_assign_after_return: Attempting to assign copy to reservation {reservation.id} for book {reservation.book.title}")
            if reservation.assign_available_copy():
                print(f"try_assign_after_return: Assigned copy to reservation {reservation.id}")
                break  # Assign to the first eligible pending reservation


# Optional: Add a signal for when a Borrowing is saved to trigger reassignment
@receiver(post_save, sender=Borrowing)
def handle_borrowing_return(sender, instance, **kwargs):
    if instance.return_date and not kwargs.get('raw', False):  # Only trigger on return
        print(f"handle_borrowing_return: Borrowing {instance.id} returned, triggering reassignment")
        pending_reservations = Reservation.objects.filter(status='pending').order_by('reservation_date')
        for reservation in pending_reservations:
            if reservation.assign_available_copy():
                print(f"handle_borrowing_return: Assigned copy to reservation {reservation.id}")
                break


@receiver(post_save, sender=Reservation)
def send_reservation_email(sender, instance, created, **kwargs):
    if created and instance.status == 'pending':
        subject = 'Reservation Confirmation'
        message = (
            f'Dear {instance.user.username},\n\n'
            f'Your reservation for "{instance.book.title}" has been received and is pending.\n'
            f'We will notify you when a copy is available for pickup.\n\n'
            f'Thank you!'
        )
        send_mail(subject, message, 'from@example.com', [instance.user.email], fail_silently=True)

    elif instance.status == 'assigned':
        subject = 'Book Assigned - Ready for Pickup'
        message = (
            f'Dear {instance.user.username},\n\n'
            f'A copy of "{instance.book.title}" has been assigned to your reservation.\n'
            f'Please pick it up by {instance.expiration_date.strftime("%Y-%m-%d")}.\n'
            f'Thank you!'
        )
        send_mail(subject, message, 'from@example.com', [instance.user.email], fail_silently=True)

    elif instance.status == 'picked_up':
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

    elif instance.status == 'expired':
        subject = 'Reservation Expired'
        message = (
            f'Dear {instance.user.username},\n\n'
            f'Your reservation for "{instance.book.title}" has been expired as of '
            f'{instance.expiration_date.strftime("%Y-%m-%d")}.\n'
            f'Please place a new reservation if you still need the book.\n\n'
            f'Thank you!'
        )
        send_mail(subject, message, 'from@example.com', [instance.user.email], fail_silently=True)

@receiver(post_delete, sender=User)
def cancel_user_reservations(sender, instance, **kwargs):
    reservations = Reservation.objects.filter(user=instance)
    for reservation in reservations:
        reservation.cancel()
