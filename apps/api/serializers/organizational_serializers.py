"""
Serializers for organizational data models
"""

from rest_framework import serializers
from apps.core.models import Directorate, Department, Unit, Section, OrganizationalSyncLog


class DirectorateSerializer(serializers.ModelSerializer):
    """Serializer for Directorate model"""
    
    department_count = serializers.SerializerMethodField()
    departments = serializers.SerializerMethodField()
    
    class Meta:
        model = Directorate
        fields = [
            'id', 'external_id', 'code', 'name', 'head_of_directorate',
            'is_active', 'last_sync', 'created_at', 'updated_at',
            'department_count', 'departments'
        ]
        read_only_fields = ['id', 'external_id', 'last_sync', 'created_at', 'updated_at']
    
    def get_department_count(self, obj):
        """Get count of departments in this directorate"""
        return obj.departments.filter(is_active=True).count() if hasattr(obj, 'departments') else 0
    
    def get_departments(self, obj):
        """Get departments if hierarchy is requested"""
        include_hierarchy = self.context.get('include_hierarchy', False)
        if include_hierarchy and hasattr(obj, 'departments'):
            return DepartmentSerializer(
                obj.departments.filter(is_active=True), 
                many=True, 
                context={'include_hierarchy': True}
            ).data
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    
    directorate_name = serializers.CharField(source='directorate.name', read_only=True)
    directorate_code = serializers.CharField(source='directorate.code', read_only=True)
    full_code = serializers.ReadOnlyField()
    unit_count = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'external_id', 'directorate', 'directorate_name', 'directorate_code',
            'code', 'name', 'full_code', 'head_of_department',
            'is_active', 'last_sync', 'created_at', 'updated_at',
            'unit_count', 'units'
        ]
        read_only_fields = ['id', 'external_id', 'last_sync', 'created_at', 'updated_at']
    
    def get_unit_count(self, obj):
        """Get count of units in this department"""
        return obj.units.filter(is_active=True).count() if hasattr(obj, 'units') else 0
    
    def get_units(self, obj):
        """Get units if hierarchy is requested"""
        include_hierarchy = self.context.get('include_hierarchy', False)
        if include_hierarchy and hasattr(obj, 'units'):
            return UnitSerializer(
                obj.units.filter(is_active=True), 
                many=True, 
                context={'include_hierarchy': True}
            ).data
        return None


class UnitSerializer(serializers.ModelSerializer):
    """Serializer for Unit model"""
    
    directorate_name = serializers.CharField(source='directorate.name', read_only=True)
    directorate_code = serializers.CharField(source='directorate.code', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_code = serializers.CharField(source='department.code', read_only=True)
    full_code = serializers.ReadOnlyField()
    section_count = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    
    class Meta:
        model = Unit
        fields = [
            'id', 'external_id', 'directorate', 'directorate_name', 'directorate_code',
            'department', 'department_name', 'department_code',
            'code', 'name', 'full_code', 'head_of_unit', 'is_independent',
            'is_active', 'last_sync', 'created_at', 'updated_at',
            'section_count', 'sections'
        ]
        read_only_fields = ['id', 'external_id', 'last_sync', 'created_at', 'updated_at']
    
    def get_section_count(self, obj):
        """Get count of sections in this unit"""
        return obj.sections.filter(is_active=True).count() if hasattr(obj, 'sections') else 0
    
    def get_sections(self, obj):
        """Get sections if hierarchy is requested"""
        include_hierarchy = self.context.get('include_hierarchy', False)
        if include_hierarchy and hasattr(obj, 'sections'):
            return SectionSerializer(
                obj.sections.filter(is_active=True), 
                many=True
            ).data
        return None


class SectionSerializer(serializers.ModelSerializer):
    """Serializer for Section model"""
    
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_code = serializers.CharField(source='unit.code', read_only=True)
    department_name = serializers.CharField(source='unit.department.name', read_only=True)
    directorate_name = serializers.CharField(source='unit.directorate.name', read_only=True)
    full_code = serializers.ReadOnlyField()
    
    class Meta:
        model = Section
        fields = [
            'id', 'external_id', 'unit', 'unit_name', 'unit_code',
            'department_name', 'directorate_name',
            'code', 'name', 'full_code', 'head_of_section',
            'is_active', 'last_sync', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'external_id', 'last_sync', 'created_at', 'updated_at']


class OrganizationalSyncLogSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationalSyncLog model"""
    
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationalSyncLog
        fields = [
            'id', 'sync_type', 'status', 'started_by', 'started_at', 'completed_at',
            'records_processed', 'records_created', 'records_updated', 
            'error_message', 'duration'
        ]
        read_only_fields = ['id']
    
    def get_duration(self, obj):
        """Calculate sync duration in seconds"""
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            return round(delta.total_seconds(), 2)
        return None


# Simplified serializers for dropdown/lookup use
class DirectorateSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for directorate dropdowns"""
    
    class Meta:
        model = Directorate
        fields = ['id', 'code', 'name']


class DepartmentSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for department dropdowns"""
    
    directorate_name = serializers.CharField(source='directorate.name', read_only=True)
    
    class Meta:
        model = Department
        fields = ['id', 'code', 'name', 'directorate', 'directorate_name']


class UnitSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for unit dropdowns"""
    
    department_name = serializers.CharField(source='department.name', read_only=True)
    directorate_name = serializers.CharField(source='directorate.name', read_only=True)
    
    class Meta:
        model = Unit
        fields = ['id', 'code', 'name', 'department', 'department_name', 'directorate_name']


class SectionSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for section dropdowns"""
    
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    
    class Meta:
        model = Section
        fields = ['id', 'code', 'name', 'unit', 'unit_name']