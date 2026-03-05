"""
Management command to sync organizational data from Corporate Service
"""

from django.core.management.base import BaseCommand
from apps.core.services import OrganizationalSyncService


class Command(BaseCommand):
    help = 'Synchronize organizational data from Corporate Service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-type',
            type=str,
            choices=['directorates', 'departments', 'units', 'sections', 'full_sync'],
            default='full_sync',
            help='Type of synchronization to perform (default: full_sync)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if Corporate Service is not responding',
        )

    def handle(self, *args, **options):
        sync_type = options['sync_type']
        
        self.stdout.write(f"Starting {sync_type} synchronization...")
        
        try:
            sync_service = OrganizationalSyncService()
            
            if sync_type == 'full_sync':
                results = sync_service.sync_all()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Full sync completed successfully:\n"
                        f"  Directorates: {results.get('directorates', (0, 0, 0))}\n"
                        f"  Departments: {results.get('departments', (0, 0, 0))}\n"
                        f"  Units: {results.get('units', (0, 0, 0))}\n"
                        f"  Sections: {results.get('sections', (0, 0, 0))}\n"
                        f"  (Format: processed, created, updated)"
                    )
                )
            elif sync_type == 'directorates':
                processed, created, updated = sync_service.sync_directorates()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Directorate sync completed: {processed} processed, {created} created, {updated} updated"
                    )
                )
            elif sync_type == 'departments':
                processed, created, updated = sync_service.sync_departments()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Department sync completed: {processed} processed, {created} created, {updated} updated"
                    )
                )
            elif sync_type == 'units':
                processed, created, updated = sync_service.sync_units()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Unit sync completed: {processed} processed, {created} created, {updated} updated"
                    )
                )
            elif sync_type == 'sections':
                processed, created, updated = sync_service.sync_sections()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Section sync completed: {processed} processed, {created} created, {updated} updated"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Synchronization failed: {str(e)}")
            )
            return

