"""
Corporate Service Integration Service
Handles synchronization of organizational data from Corporate Service
"""

import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.models import (
    Directorate, Department, Unit, Section, OrganizationalSyncLog
)

logger = logging.getLogger(__name__)


class CorporateServiceClient:
    """Client for interacting with Corporate Service API"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'CORPORATE_SERVICE_URL', 'http://corporate-service:8000')
        self.api_version = 'v1'
        self.timeout = getattr(settings, 'CORPORATE_SERVICE_TIMEOUT', 30)
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Corporate Service"""
        url = f"{self.base_url}/api/{self.api_version}/corporate/{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        # Add service authentication headers if available
        service_token = getattr(settings, 'INTER_SERVICE_TOKEN', None)
        if service_token:
            headers['Authorization'] = f'Bearer {service_token}'
        
        try:
            response = requests.get(url, headers=headers, params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Corporate Service request failed: {url} - {str(e)}")
            return None
    
    def get_directorates(self, is_active: Optional[bool] = True) -> Optional[List[Dict]]:
        """Fetch directorates from Corporate Service"""
        params = {'limit': 1000}  # Get all directorates
        if is_active is not None:
            params['is_active'] = 'true' if is_active else 'false'
        
        result = self._make_request('hr/directorates/', params)
        return result.get('results', []) if result else None
    
    def get_departments(self, is_active: Optional[bool] = True) -> Optional[List[Dict]]:
        """Fetch departments from Corporate Service"""
        params = {'limit': 1000}  # Get all departments
        if is_active is not None:
            params['is_active'] = 'true' if is_active else 'false'
        
        result = self._make_request('hr/departments/', params)
        return result.get('results', []) if result else None
    
    def get_units(self, is_active: Optional[bool] = True) -> Optional[List[Dict]]:
        """Fetch units from Corporate Service"""
        params = {'limit': 1000}  # Get all units
        if is_active is not None:
            params['is_active'] = 'true' if is_active else 'false'
        
        result = self._make_request('hr/units/', params)
        return result.get('results', []) if result else None
    
    def get_sections(self, is_active: Optional[bool] = True) -> Optional[List[Dict]]:
        """Fetch sections from Corporate Service"""
        params = {'limit': 1000}  # Get all sections
        if is_active is not None:
            params['is_active'] = 'true' if is_active else 'false'
        
        result = self._make_request('hr/sections/', params)
        return result.get('results', []) if result else None


class OrganizationalSyncService:
    """Service for synchronizing organizational data from Corporate Service"""
    
    def __init__(self):
        self.client = CorporateServiceClient()
    
    def _log_sync_start(self, sync_type: str, started_by: Optional[str] = None) -> OrganizationalSyncLog:
        """Start a sync operation and create log entry"""
        return OrganizationalSyncLog.objects.create(
            sync_type=sync_type,
            status='in_progress',
            started_by=started_by,
        )
    
    def _log_sync_complete(
        self, 
        sync_log: OrganizationalSyncLog, 
        processed: int = 0, 
        created: int = 0, 
        updated: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Complete a sync operation and update log entry"""
        sync_log.status = 'failed' if error else 'completed'
        sync_log.completed_at = timezone.now()
        sync_log.records_processed = processed
        sync_log.records_created = created
        sync_log.records_updated = updated
        if error:
            sync_log.error_message = error
        sync_log.save()
    
    def sync_directorates(self, started_by: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Sync directorates from Corporate Service
        Returns: (processed, created, updated)
        """
        sync_log = self._log_sync_start('directorates', started_by)
        processed = created = updated = 0
        
        try:
            logger.info("Starting directorate synchronization")
            corp_directorates = self.client.get_directorates()
            
            if corp_directorates is None:
                raise Exception("Failed to fetch directorates from Corporate Service")
            
            with transaction.atomic():
                for corp_dir in corp_directorates:
                    processed += 1
                    
                    # Try to find existing directorate
                    directorate, was_created = Directorate.objects.update_or_create(
                        external_id=corp_dir['id'],
                        defaults={
                            'code': corp_dir['code'],
                            'name': corp_dir['name'],
                            'head_of_directorate': corp_dir.get('director_id'),
                            'is_active': corp_dir.get('is_active', True),
                            'last_sync': timezone.now(),
                        }
                    )
                    
                    if was_created:
                        created += 1
                        logger.debug(f"Created directorate: {directorate.code}")
                    else:
                        updated += 1
                        logger.debug(f"Updated directorate: {directorate.code}")
                        
            self._log_sync_complete(sync_log, processed, created, updated)
            logger.info(f"Directorate sync completed: {processed} processed, {created} created, {updated} updated")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Directorate sync failed: {error_msg}")
            self._log_sync_complete(sync_log, processed, created, updated, error_msg)
            raise
            
        return processed, created, updated
    
    def sync_departments(self, started_by: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Sync departments from Corporate Service
        Returns: (processed, created, updated)
        """
        sync_log = self._log_sync_start('departments', started_by)
        processed = created = updated = 0
        
        try:
            logger.info("Starting department synchronization")
            corp_departments = self.client.get_departments()
            
            if corp_departments is None:
                raise Exception("Failed to fetch departments from Corporate Service")
            
            with transaction.atomic():
                for corp_dept in corp_departments:
                    processed += 1
                    
                    # Find the parent directorate
                    try:
                        directorate = Directorate.objects.get(external_id=corp_dept['directorate'])
                    except Directorate.DoesNotExist:
                        logger.warning(f"Parent directorate not found for department {corp_dept['code']}")
                        continue
                    
                    # Try to find existing department
                    department, was_created = Department.objects.update_or_create(
                        external_id=corp_dept['id'],
                        defaults={
                            'directorate': directorate,
                            'code': corp_dept['code'],
                            'name': corp_dept['name'],
                            'head_of_department': corp_dept.get('head_id'),
                            'is_active': corp_dept.get('is_active', True),
                            'last_sync': timezone.now(),
                        }
                    )
                    
                    if was_created:
                        created += 1
                        logger.debug(f"Created department: {department.code}")
                    else:
                        updated += 1
                        logger.debug(f"Updated department: {department.code}")
                        
            self._log_sync_complete(sync_log, processed, created, updated)
            logger.info(f"Department sync completed: {processed} processed, {created} created, {updated} updated")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Department sync failed: {error_msg}")
            self._log_sync_complete(sync_log, processed, created, updated, error_msg)
            raise
            
        return processed, created, updated
    
    def sync_units(self, started_by: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Sync units from Corporate Service
        Returns: (processed, created, updated)
        """
        sync_log = self._log_sync_start('units', started_by)
        processed = created = updated = 0
        
        try:
            logger.info("Starting unit synchronization")
            corp_units = self.client.get_units()
            
            if corp_units is None:
                raise Exception("Failed to fetch units from Corporate Service")
            
            with transaction.atomic():
                for corp_unit in corp_units:
                    processed += 1
                    
                    # Find the parent directorate and department
                    try:
                        directorate = Directorate.objects.get(external_id=corp_unit['directorate'])
                        department = Department.objects.get(external_id=corp_unit['department'])
                    except (Directorate.DoesNotExist, Department.DoesNotExist):
                        logger.warning(f"Parent organization not found for unit {corp_unit['code']}")
                        continue
                    
                    # Try to find existing unit
                    unit, was_created = Unit.objects.update_or_create(
                        external_id=corp_unit['id'],
                        defaults={
                            'directorate': directorate,
                            'department': department,
                            'code': corp_unit['code'],
                            'name': corp_unit['name'],
                            'head_of_unit': corp_unit.get('head_id'),
                            'is_independent': corp_unit.get('is_independent', False),
                            'is_active': corp_unit.get('is_active', True),
                            'last_sync': timezone.now(),
                        }
                    )
                    
                    if was_created:
                        created += 1
                        logger.debug(f"Created unit: {unit.code}")
                    else:
                        updated += 1
                        logger.debug(f"Updated unit: {unit.code}")
                        
            self._log_sync_complete(sync_log, processed, created, updated)
            logger.info(f"Unit sync completed: {processed} processed, {created} created, {updated} updated")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unit sync failed: {error_msg}")
            self._log_sync_complete(sync_log, processed, created, updated, error_msg)
            raise
            
        return processed, created, updated
    
    def sync_sections(self, started_by: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Sync sections from Corporate Service
        Returns: (processed, created, updated)
        """
        sync_log = self._log_sync_start('sections', started_by)
        processed = created = updated = 0
        
        try:
            logger.info("Starting section synchronization")
            corp_sections = self.client.get_sections()
            
            if corp_sections is None:
                raise Exception("Failed to fetch sections from Corporate Service")
            
            with transaction.atomic():
                for corp_section in corp_sections:
                    processed += 1
                    
                    # Find the parent unit
                    try:
                        unit = Unit.objects.get(external_id=corp_section['unit'])
                    except Unit.DoesNotExist:
                        logger.warning(f"Parent unit not found for section {corp_section['code']}")
                        continue
                    
                    # Try to find existing section
                    section, was_created = Section.objects.update_or_create(
                        external_id=corp_section['id'],
                        defaults={
                            'unit': unit,
                            'code': corp_section['code'],
                            'name': corp_section['name'],
                            'head_of_section': corp_section.get('head_id'),
                            'is_active': corp_section.get('is_active', True),
                            'last_sync': timezone.now(),
                        }
                    )
                    
                    if was_created:
                        created += 1
                        logger.debug(f"Created section: {section.code}")
                    else:
                        updated += 1
                        logger.debug(f"Updated section: {section.code}")
                        
            self._log_sync_complete(sync_log, processed, created, updated)
            logger.info(f"Section sync completed: {processed} processed, {created} created, {updated} updated")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Section sync failed: {error_msg}")
            self._log_sync_complete(sync_log, processed, created, updated, error_msg)
            raise
            
        return processed, created, updated
    
    def sync_all(self, started_by: Optional[str] = None) -> Dict[str, Tuple[int, int, int]]:
        """
        Perform full organizational synchronization
        Returns: Dictionary with sync results for each organizational level
        """
        sync_log = self._log_sync_start('full_sync', started_by)
        results = {}
        
        try:
            logger.info("Starting full organizational synchronization")
            
            # Sync in hierarchical order
            results['directorates'] = self.sync_directorates(started_by)
            results['departments'] = self.sync_departments(started_by)
            results['units'] = self.sync_units(started_by)
            results['sections'] = self.sync_sections(started_by)
            
            # Calculate totals
            total_processed = sum(r[0] for r in results.values())
            total_created = sum(r[1] for r in results.values())
            total_updated = sum(r[2] for r in results.values())
            
            self._log_sync_complete(sync_log, total_processed, total_created, total_updated)
            logger.info(f"Full sync completed: {total_processed} processed, {total_created} created, {total_updated} updated")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Full sync failed: {error_msg}")
            self._log_sync_complete(sync_log, 0, 0, 0, error_msg)
            raise
            
        return results