import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Создаёт резервную копию локальной SQLite базы данных.'

    def handle(self, *args, **options):
        database = settings.DATABASES['default']
        if database['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError(
                'Для PostgreSQL используйте pg_dump в инфраструктуре размещения.',
            )

        source = Path(database['NAME']).resolve()
        backup_directory = Path(settings.BASE_DIR, 'backups').resolve()
        backup_directory.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        destination = backup_directory / f'db-{timestamp}.sqlite3'
        shutil.copy2(source, destination)
        self.stdout.write(self.style.SUCCESS(f'Резервная копия: {destination}'))
