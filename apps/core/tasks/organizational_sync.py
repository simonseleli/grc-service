"""
Celery tasks for GRC service
"""

import logging
from celery import shared_task
from apps.core.services import OrganizationalSyncService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_organizational_data(self, sync_type='full_sync'):
    """
    Celery task to sync organizational data from Corporate Service
    
    Args:
        sync_type (str): Type of sync to perform ('directorates', 'departments', 
                        'units', 'sections', or 'full_sync')
    """
    try:
        logger.info(f"Starting automated {sync_type} sync")
        sync_service = OrganizationalSyncService()
        
        if sync_type == 'full_sync':
            results = sync_service.sync_all(started_by=None)
            logger.info(f"Full sync completed: {results}")
            return {
                'success': True,
                'sync_type': sync_type,
                'results': results,
                'message': 'Full organizational sync completed successfully'
            }
        elif sync_type == 'directorates':
            processed, created, updated = sync_service.sync_directorates(started_by=None)
            result = {'processed': processed, 'created': created, 'updated': updated}
            logger.info(f"Directorate sync completed: {result}")
            return {
                'success': True,
                'sync_type': sync_type,
                'result': result,
                'message': 'Directorate sync completed successfully'
            }
        elif sync_type == 'departments':
            processed, created, updated = sync_service.sync_departments(started_by=None)
            result = {'processed': processed, 'created': created, 'updated': updated}
            logger.info(f"Department sync completed: {result}")
            return {
                'success': True,
                'sync_type': sync_type,
                'result': result,
                'message': 'Department sync completed successfully'
            }
        elif sync_type == 'units':
            processed, created, updated = sync_service.sync_units(started_by=None)
            result = {'processed': processed, 'created': created, 'updated': updated}
            logger.info(f"Unit sync completed: {result}")
            return {
                'success': True,
                'sync_type': sync_type,
                'result': result,
                'message': 'Unit sync completed successfully'
            }
        elif sync_type == 'sections':
            processed, created, updated = sync_service.sync_sections(started_by=None)
            result = {'processed': processed, 'created': created, 'updated': updated}
            logger.info(f"Section sync completed: {result}")
            return {
                'success': True,
                'sync_type': sync_type,
                'result': result,
                'message': 'Section sync completed successfully'
            }
        else:
            raise ValueError(f"Invalid sync type: {sync_type}")
            
    except Exception as exc:
        logger.error(f"Organizational sync failed: {str(exc)}")
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying sync in {2 ** self.request.retries * 60} seconds")
            raise self.retry(countdown=2 ** self.request.retries * 60, exc=exc)
        
        # Max retries exceeded
        return {
            'success': False,
            'sync_type': sync_type,
            'error': str(exc),
            'message': f'Organizational sync failed after {self.max_retries} retries'
        }


@shared_task
def daily_organizational_sync():
    """Daily task to sync all organizational data"""
    return sync_organizational_data.delay('full_sync')


@shared_task
def hourly_directorate_sync():
    """Hourly task to sync directorate data (lighter sync)"""
    return sync_organizational_data.delay('directorates')


@shared_task
def cleanup_old_sync_logs():
    """Task to clean up old sync logs (keep last 100 records)"""
    try:
        from apps.core.models import OrganizationalSyncLog
        
        # Keep last 100 sync logs, delete older ones
        logs_to_keep = OrganizationalSyncLog.objects.all()[:100]
        keep_ids = [log.id for log in logs_to_keep]
        
        deleted_count = OrganizationalSyncLog.objects.exclude(id__in=keep_ids).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old sync logs")
        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': 'Old sync logs cleaned up successfully'
        }
        
    except Exception as exc:
        logger.error(f"Sync log cleanup failed: {str(exc)}")
        return {
            'success': False,
            'error': str(exc),
            'message': 'Sync log cleanup failed'
        }