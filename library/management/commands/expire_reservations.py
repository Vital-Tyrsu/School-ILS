from django.core.management.base import BaseCommand
from library.models import Reservation

class Command(BaseCommand):
    help = 'Check and expire overdue reservations, then assign available copies'

    def handle(self, *args, **kwargs):
        # Expire overdue reservations
        reservations = Reservation.objects.filter(status='assigned')
        for reservation in reservations:
            if reservation.check_expiration():
                self.stdout.write(f"Expired reservation {reservation.id}")

        # Assign copies to pending reservations
        pending = Reservation.objects.filter(status='pending').order_by('reservation_date')
        for reservation in pending:
            if reservation.assign_available_copy():
                self.stdout.write(f"Assigned copy to reservation {reservation.id}")
        self.stdout.write("Done checking expirations and assignments")