"""
Document Service Client
Handles communication with Document Records Service for FIMS document storage.

Following FIMS Pattern:
1. Create document metadata (POST /api/v1/documents/)
2. Upload file separately (POST /api/v1/documents/{id}/upload/)
3. Store document_id reference in GRC database
"""

import logging
import requests
from typing import Optional, Dict, Any, BinaryIO
from django.conf import settings

logger = logging.getLogger(__name__)


class DocumentServiceError(Exception):
    """Base exception for document service errors"""
    pass


class DocumentServiceClient:
    """
    Client for interacting with Document Records Service.
    Handles document creation, file upload, retrieval, and versioning.
    """
    
    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize Document Service Client.
        
        Args:
            base_url: Base URL for Document Records Service (defaults to settings.DOCUMENT_SERVICE_URL)
            auth_token: JWT token for authentication (will be passed through from request)
        """
        self.base_url = (base_url or settings.DOCUMENT_SERVICE_URL).rstrip('/')
        self.auth_token = auth_token
        self.timeout = 30  # seconds
        
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for requests"""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        return headers
    
    def create_document(
        self,
        title: str,
        description: str,
        document_type: str = 'audit_working_paper',
        classification: str = 'confidential',
        record_type: str = 'non_permanent',
        retention_period: int = 2555,  # 7 years for audit records
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create document metadata in Document Records Service.
        
        This is Step 1 of the two-step document creation process.
        File upload is done separately via upload_file().
        
        Args:
            title: Document title
            description: Document description
            document_type: Document type code (must exist in Document Records Service)
            classification: 'open' or 'confidential'
            record_type: 'permanent' or 'non_permanent'
            retention_period: Retention period in days
            metadata: Additional metadata (service-specific data)
            tags: List of tags
            **kwargs: Additional fields (active_period_days, semi_active_period_days, etc.)
            
        Returns:
            Document data including 'id' field
            
        Raises:
            DocumentServiceError: If document creation fails
        """
        url = f'{self.base_url}/api/v1/documents/'
        
        payload = {
            'title': title,
            'description': description,
            'document_type': document_type,
            'classification': classification,
            'record_type': record_type,
            'retention_period': retention_period,
            'metadata': metadata or {},
            'tags': tags or [],
        }
        
        # Add optional fields
        if 'active_period_days' in kwargs:
            payload['active_period_days'] = kwargs['active_period_days']
        if 'semi_active_period_days' in kwargs:
            payload['semi_active_period_days'] = kwargs['semi_active_period_days']
        
        try:
            logger.info(f"Creating document in Document Records Service: {title}")
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Document created successfully: {data['data']['id']}")
                return data['data']
            else:
                error_msg = f"Document creation failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise DocumentServiceError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to communicate with Document Service: {str(e)}"
            logger.error(error_msg)
            raise DocumentServiceError(error_msg)
    
    def upload_file(
        self,
        document_id: str,
        file_data: BinaryIO,
        file_name: str
    ) -> Dict[str, Any]:
        """
        Upload file to existing document.
        
        This is Step 2 of the two-step document creation process.
        Document metadata must be created first via create_document().
        
        Args:
            document_id: UUID of document (from create_document response)
            file_data: File data (file object or bytes)
            file_name: Name of the file
            
        Returns:
            Updated document data with file information
            
        Raises:
            DocumentServiceError: If file upload fails
        """
        url = f'{self.base_url}/api/v1/documents/{document_id}/upload/'
        
        # Prepare multipart/form-data request
        files = {'file': (file_name, file_data)}
        
        # Use auth token but remove Content-Type (let requests set it for multipart)
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        try:
            logger.info(f"Uploading file to document {document_id}: {file_name}")
            response = requests.post(
                url,
                files=files,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"File uploaded successfully to document {document_id}")
                return data['data']
            else:
                error_msg = f"File upload failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise DocumentServiceError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to upload file to Document Service: {str(e)}"
            logger.error(error_msg)
            raise DocumentServiceError(error_msg)
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieve document metadata.
        
        Args:
            document_id: UUID of document
            
        Returns:
            Document data
            
        Raises:
            DocumentServiceError: If retrieval fails
        """
        url = f'{self.base_url}/api/v1/documents/{document_id}/'
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['data']
            else:
                error_msg = f"Document retrieval failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise DocumentServiceError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to retrieve document from Document Service: {str(e)}"
            logger.error(error_msg)
            raise DocumentServiceError(error_msg)
    
    def get_download_url(self, document_id: str) -> str:
        """
        Get document download URL.
        
        Args:
            document_id: UUID of document
            
        Returns:
            Download URL (relative path)
        """
        return f'/api/v1/documents/{document_id}/download/'
    
    def create_document_version(
        self,
        document_id: str,
        file_data: BinaryIO,
        file_name: str,
        version_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new version of existing document.
        
        Args:
            document_id: UUID of original document
            file_data: File data for new version
            file_name: Name of the file
            version_note: Description of changes in this version
            
        Returns:
            Updated document data
            
        Raises:
            DocumentServiceError: If version creation fails
        """
        url = f'{self.base_url}/api/v1/documents/{document_id}/versions/'
        
        files = {'file': (file_name, file_data)}
        data = {}
        if version_note:
            data['version_note'] = version_note
        
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        try:
            logger.info(f"Creating new version for document {document_id}")
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Document version created successfully: version {data['data']['version']}")
                return data['data']
            else:
                error_msg = f"Version creation failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise DocumentServiceError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to create document version: {str(e)}"
            logger.error(error_msg)
            raise DocumentServiceError(error_msg)
    
    def create_document_with_file(
        self,
        title: str,
        description: str,
        file_data: Optional[BinaryIO] = None,
        file_name: Optional[str] = None,
        document_type: str = 'audit_working_paper',
        classification: str = 'confidential',
        record_type: str = 'non_permanent',
        retention_period: int = 2555,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convenience method: Create document and upload file in one call.
        
        This combines create_document() and upload_file() for common use case.
        
        Args:
            title: Document title
            description: Document description
            file_data: File data (optional - can create metadata-only document)
            file_name: Name of the file
            document_type: Document type code
            classification: 'open' or 'confidential'
            record_type: 'permanent' or 'non_permanent'
            retention_period: Retention period in days
            metadata: Additional metadata
            tags: List of tags
            **kwargs: Additional fields
            
        Returns:
            Document data with file information
            
        Raises:
            DocumentServiceError: If any step fails
        """
        # Step 1: Create document metadata
        document = self.create_document(
            title=title,
            description=description,
            document_type=document_type,
            classification=classification,
            record_type=record_type,
            retention_period=retention_period,
            metadata=metadata,
            tags=tags,
            **kwargs
        )
        
        # Step 2: Upload file if provided
        if file_data and file_name:
            try:
                document = self.upload_file(
                    document_id=document['id'],
                    file_data=file_data,
                    file_name=file_name
                )
            except DocumentServiceError as e:
                # Document created but file upload failed
                logger.warning(f"Document {document['id']} created but file upload failed: {e}")
                # Re-raise to let caller handle
                raise
        
        return document


    def generate_approved_stamp(
        self,
        document_id: str,
        approver_id: str,
        entity_type: str,
        entity_id: str,
        service_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request DRS to embed an approval stamp (CIA signature + QR code) onto a PDF.

        GAP 9 — called by GRC Kafka consumer after CIA approves a formal output
        document (AuditReport, AuditMemo, AuditProgram).

        Args:
            document_id:   DRS Document UUID (str or UUID)
            approver_id:   IAM User UUID of the CIA approver (for signature fetch)
            entity_type:   GRC entity type label, e.g. 'audit_report'
            entity_id:     GRC entity UUID (for QR verification URL)
            service_token: X-Service-Token value; falls back to
                           settings.SERVICE_TO_SERVICE_TOKEN if omitted.

        Returns:
            Dict with 'document_id', 'stamped_document_url', 'entity_type', 'entity_id'

        Raises:
            DocumentServiceError: on any HTTP or connection error
        """
        url = f'{self.base_url}/api/v1/documents/{document_id}/generate-approved-stamp/'

        # Build auth headers — service-to-service calls use X-Service-Token
        headers: Dict[str, str] = {}
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'

        effective_token = service_token or getattr(settings, 'SERVICE_TO_SERVICE_TOKEN', None)
        if effective_token:
            headers['X-Service-Token'] = effective_token

        payload = {
            'approver_id': str(approver_id),
            'entity_type': entity_type,
            'entity_id': str(entity_id),
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            body = response.json()
            return body.get('data', body)

        except requests.exceptions.RequestException as e:
            error_msg = f"Stamp request for document {document_id} failed: {e}"
            logger.error(error_msg)
            raise DocumentServiceError(error_msg) from e


def get_document_client(auth_token: Optional[str] = None) -> DocumentServiceClient:
    """
    Factory function to get Document Service Client instance.
    
    Args:
        auth_token: JWT token for authentication
        
    Returns:
        Configured DocumentServiceClient instance
    """
    return DocumentServiceClient(auth_token=auth_token)
