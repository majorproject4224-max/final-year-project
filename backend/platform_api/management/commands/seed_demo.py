"""The old generated training-data seeder is retired."""
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Retired. Use prepare_presentation for explicitly fictional UI fixtures."

    def handle(self, *args, **options):
        raise CommandError("Synthetic training seeding is retired. Use prepare_presentation --apply in a disposable _demo/_test database. Never import survey respondents as registered users.")
