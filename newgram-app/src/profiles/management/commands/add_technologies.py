from django.core.management.base import BaseCommand
from src.profiles.models import Technology

class Command(BaseCommand):
    help = 'Adds default technologies to the database'

    def handle(self, *args, **options):
        technologies = [
            'Python', 'Django', 'JavaScript', 'React', 'HTML', 'CSS',
            'SQL', 'PostgreSQL', 'Git', 'Docker', 'Linux', 'TypeScript',
            'Node.js', 'Vue.js', 'Angular', 'PHP', 'Java', 'C++',
            'C#', '.NET', 'Ruby', 'Rails', 'Go', 'Rust'
        ]

        for tech_name in technologies:
            Technology.objects.get_or_create(name=tech_name)
            self.stdout.write(self.style.SUCCESS(f'Successfully added technology "{tech_name}"')) 