# File: library/management/commands/expire_reservations.py
from django.core.management.base import BaseCommand
from library.models import Reservation
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check and expire overdue reservations and assign available copies'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Checking reservations at {timezone.now()}")
        # Expire overdue reservations
        reservations = Reservation.objects.filter(status='assigned')
        expired_count = 0
        for reservation in reservations:
            if reservation.check_expiration():
                expired_count += 1
                self.stdout.write(f"Expired reservation {reservation.id} for user {reservation.user.username}")
                # Immediately try to assign the freed copy to a pending reservation
                pending_reservations = Reservation.objects.filter(status='pending').order_by('reservation_date')
                for pending_reservation in pending_reservations:
                    self.stdout.write(f"After expiration: Attempting to assign copy to pending reservation {pending_reservation.id} for user {pending_reservation.user.username}, book: {pending_reservation.book.title}")
                    if pending_reservation.assign_available_copy():
                        self.stdout.write(f"After expiration: Assigned freed copy to pending reservation {pending_reservation.id} for user {pending_reservation.user.username}")
                        break  # Assign to the first eligible pending reservation
        self.stdout.write(f"Expired {expired_count} reservations")

        # Assign copies to any remaining pending reservations
        pending_reservations = Reservation.objects.filter(status='pending').order_by('reservation_date')
        assigned_count = 0
        for reservation in pending_reservations:
            self.stdout.write(f"Final check: Processing pending reservation {reservation.id} for user {reservation.user.username}, book: {reservation.book.title}")
            if reservation.assign_available_copy():
                assigned_count += 1
                self.stdout.write(f"Final check: Assigned copy to reservation {reservation.id} for user {reservation.user.username}")
        self.stdout.write(f"Assigned copies to {assigned_count} reservations")