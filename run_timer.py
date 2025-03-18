import sys
import os
import schedule
import time
import django
from django.core.management import call_command

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_project.settings')  # Adjust if your settings module differs
django.setup()

def run_expire_reservations():
    print("Running expire_reservations at", time.ctime())
    try:
        call_command('expire_reservations')
        print("expire_reservations completed successfully")
    except Exception as e:
        print(f"Error running expire_reservations: {e}")

# Schedule the task to run every minute
schedule.every(1).minutes.do(run_expire_reservations)

# Keep the script running
print("Timer started. Press Ctrl+C to stop.")
while True:
    schedule.run_pending()
    time.sleep(1)