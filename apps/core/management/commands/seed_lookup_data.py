"""
Django management command to seed lookup table data for GRC Service
Following FIMS patterns for initial data seeding
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import uuid
from datetime import date

from apps.core.models import (
    FiscalYear, Quarter, AuditSeverity, FindingType, 
    RiskRating, AuditOpinion
)


class Command(BaseCommand):
    help = 'Seed lookup tables with initial data for GRC Service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate all lookup data (deletes existing)',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        if force:
            self.stdout.write('Force mode: Clearing existing lookup data...')
            self._clear_data()
        
        with transaction.atomic():
            self._create_fiscal_years()
            self._create_audit_severity()
            self._create_finding_types()
            self._create_risk_ratings()
            self._create_audit_opinions()
            
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded lookup table data')
        )

    def _clear_data(self):
        """Clear existing lookup data when using --force"""
        FiscalYear.objects.all().delete()
        AuditSeverity.objects.all().delete()
        FindingType.objects.all().delete()
        RiskRating.objects.all().delete()
        AuditOpinion.objects.all().delete()

    def _create_fiscal_years(self):
        """Create fiscal year data"""
        fiscal_years = [
            {
                'year_code': '2023/2024',
                'name': 'Fiscal Year 2023/2024',
                'start_date': date(2023, 7, 1),
                'end_date': date(2024, 6, 30),
            },
            {
                'year_code': '2024/2025',
                'name': 'Fiscal Year 2024/2025',
                'start_date': date(2024, 7, 1),
                'end_date': date(2025, 6, 30),
            },
            {
                'year_code': '2025/2026',
                'name': 'Fiscal Year 2025/2026',
                'start_date': date(2025, 7, 1),
                'end_date': date(2026, 6, 30),
            }
        ]

        created_count = 0
        for fy_data in fiscal_years:
            fiscal_year, created = FiscalYear.objects.get_or_create(
                year_code=fy_data['year_code'],
                defaults={
                    'name': fy_data['name'],
                    'start_date': fy_data['start_date'],
                    'end_date': fy_data['end_date'],
                    'created_by': uuid.uuid4(),  # System user
                }
            )
            
            if created:
                created_count += 1
                
                # Create quarters for this fiscal year
                quarters = [
                    {
                        'quarter_number': 1,
                        'name': 'Q1',
                        'start_date': fy_data['start_date'],
                        'end_date': date(fy_data['start_date'].year, 9, 30),
                    },
                    {
                        'quarter_number': 2,
                        'name': 'Q2',
                        'start_date': date(fy_data['start_date'].year, 10, 1),
                        'end_date': date(fy_data['start_date'].year, 12, 31),
                    },
                    {
                        'quarter_number': 3,
                        'name': 'Q3',
                        'start_date': date(fy_data['end_date'].year, 1, 1),
                        'end_date': date(fy_data['end_date'].year, 3, 31),
                    },
                    {
                        'quarter_number': 4,
                        'name': 'Q4',
                        'start_date': date(fy_data['end_date'].year, 4, 1),
                        'end_date': fy_data['end_date'],
                    },
                ]
                
                for quarter_data in quarters:
                    Quarter.objects.get_or_create(
                        fiscal_year=fiscal_year,
                        quarter_number=quarter_data['quarter_number'],
                        defaults={
                            'name': quarter_data['name'],
                            'start_date': quarter_data['start_date'],
                            'end_date': quarter_data['end_date'],
                            'created_by': uuid.uuid4(),
                        }
                    )

        self.stdout.write(f'Created {created_count} fiscal years with quarters')

    def _create_audit_severity(self):
        """Create audit severity levels"""
        severities = [
            {
                'code': 'CRITICAL',
                'name': 'Critical',
                'description': 'Issues that pose immediate and significant risk',
                'color_code': '#DC2626',  # Red
                'sort_order': 1,
            },
            {
                'code': 'HIGH',
                'name': 'High',
                'description': 'Issues that require urgent attention',
                'color_code': '#EA580C',  # Orange
                'sort_order': 2,
            },
            {
                'code': 'MEDIUM',
                'name': 'Medium',
                'description': 'Issues that should be addressed in reasonable timeframe',
                'color_code': '#D97706',  # Amber
                'sort_order': 3,
            },
            {
                'code': 'LOW',
                'name': 'Low',
                'description': 'Minor issues or opportunities for improvement',
                'color_code': '#65A30D',  # Green
                'sort_order': 4,
            },
        ]

        created_count = 0
        for sev_data in severities:
            severity, created = AuditSeverity.objects.get_or_create(
                code=sev_data['code'],
                defaults={
                    'name': sev_data['name'],
                    'description': sev_data['description'],
                    'color_code': sev_data['color_code'],
                    'sort_order': sev_data['sort_order'],
                    'created_by': uuid.uuid4(),
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'Created {created_count} audit severity levels')

    def _create_finding_types(self):
        """Create finding type categories"""
        finding_types = [
            {
                'code': 'COMPLIANCE',
                'name': 'Compliance Finding',
                'description': 'Non-compliance with laws, regulations, or policies',
                'category': 'REGULATORY',
            },
            {
                'code': 'INTERNAL_CTRL',
                'name': 'Internal Control Deficiency',
                'description': 'Weaknesses in internal control systems',
                'category': 'CONTROL',
            },
            {
                'code': 'FINANCIAL',
                'name': 'Financial Management Issue',
                'description': 'Issues related to financial management and reporting',
                'category': 'FINANCIAL',
            },
            {
                'code': 'OPERATIONAL',
                'name': 'Operational Inefficiency',
                'description': 'Inefficiencies in operations and processes',
                'category': 'OPERATIONAL',
            },
            {
                'code': 'IT_GOVERNANCE',
                'name': 'IT Governance Issue',
                'description': 'Issues in IT governance and systems',
                'category': 'TECHNOLOGY',
            },
            {
                'code': 'FRAUD_RISK',
                'name': 'Fraud Risk Exposure',
                'description': 'Exposures to fraud risk',
                'category': 'RISK',
            },
        ]

        created_count = 0
        for ft_data in finding_types:
            finding_type, created = FindingType.objects.get_or_create(
                code=ft_data['code'],
                defaults={
                    'name': ft_data['name'],
                    'description': ft_data['description'],
                    'category': ft_data['category'],
                    'created_by': uuid.uuid4(),
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'Created {created_count} finding types')

    def _create_risk_ratings(self):
        """Create risk rating scales"""
        risk_ratings = [
            {
                'code': 'VERY_HIGH',
                'name': 'Very High Risk',
                'description': 'Risk level requires immediate action',
                'numerical_value': Decimal('4.5'),
                'color_code': '#991B1B',  # Dark Red
                'sort_order': 1,
            },
            {
                'code': 'HIGH',
                'name': 'High Risk',
                'description': 'Risk level requires prompt action',
                'numerical_value': Decimal('3.5'),
                'color_code': '#DC2626',  # Red
                'sort_order': 2,
            },
            {
                'code': 'MEDIUM_HIGH',
                'name': 'Medium-High Risk',
                'description': 'Risk level requires planned action',
                'numerical_value': Decimal('3.0'),
                'color_code': '#EA580C',  # Orange
                'sort_order': 3,
            },
            {
                'code': 'MEDIUM',
                'name': 'Medium Risk',
                'description': 'Risk level within acceptable range but requires monitoring',
                'numerical_value': Decimal('2.5'),
                'color_code': '#D97706',  # Amber
                'sort_order': 4,
            },
            {
                'code': 'LOW_MEDIUM',
                'name': 'Low-Medium Risk',
                'description': 'Risk level acceptable with regular monitoring',
                'numerical_value': Decimal('2.0'),
                'color_code': '#CA8A04',  # Yellow
                'sort_order': 5,
            },
            {
                'code': 'LOW',
                'name': 'Low Risk',
                'description': 'Risk level minimal and acceptable',
                'numerical_value': Decimal('1.5'),
                'color_code': '#65A30D',  # Green
                'sort_order': 6,
            },
        ]

        created_count = 0
        for risk_data in risk_ratings:
            risk_rating, created = RiskRating.objects.get_or_create(
                code=risk_data['code'],
                defaults={
                    'name': risk_data['name'],
                    'description': risk_data['description'],
                    'numerical_value': risk_data['numerical_value'],
                    'color_code': risk_data['color_code'],
                    'sort_order': risk_data['sort_order'],
                    'created_by': uuid.uuid4(),
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'Created {created_count} risk ratings')

    def _create_audit_opinions(self):
        """Create audit opinion types"""
        opinions = [
            {
                'code': 'UNQUALIFIED',
                'name': 'Unqualified Opinion',
                'description': 'Clean audit opinion - no material issues identified',
            },
            {
                'code': 'QUALIFIED',
                'name': 'Qualified Opinion',
                'description': 'Opinion with specific reservations or limitations',
            },
            {
                'code': 'ADVERSE',
                'name': 'Adverse Opinion',
                'description': 'Opinion indicating material misstatements or control failures',
            },
            {
                'code': 'DISCLAIMER',
                'name': 'Disclaimer of Opinion',
                'description': 'Unable to form an opinion due to insufficient evidence',
            },
            {
                'code': 'SATISFACTORY',
                'name': 'Satisfactory',
                'description': 'Overall performance meets expectations',
            },
            {
                'code': 'NEEDS_IMPROVEMENT',
                'name': 'Needs Improvement',
                'description': 'Areas requiring enhancement identified',
            },
        ]

        created_count = 0
        for opinion_data in opinions:
            opinion, created = AuditOpinion.objects.get_or_create(
                code=opinion_data['code'],
                defaults={
                    'name': opinion_data['name'],
                    'description': opinion_data['description'],
                    'created_by': uuid.uuid4(),
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'Created {created_count} audit opinions')
    

