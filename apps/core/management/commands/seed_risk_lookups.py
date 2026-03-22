"""
Django management command to seed Risk Management lookup tables.
Follows the same pattern as seed_lookup_data.py.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import uuid

from apps.core.models.lookups import (
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
)


class Command(BaseCommand):
    help = "Seed Risk Management lookup tables with initial data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate all risk lookup data (deletes existing)',
        )

    def handle(self, *args, **options):
        force = options['force']

        if force:
            self.stdout.write('Force mode: Clearing existing risk lookup data...')
            self._clear_data()

        with transaction.atomic():
            self._seed_risk_categories()
            self._seed_risk_likelihood()
            self._seed_risk_impact()
            self._seed_risk_levels()
            self._seed_nc_types()
            self._seed_iso_clauses()

        self.stdout.write(self.style.SUCCESS("Risk lookups seeded."))

    def _clear_data(self):
        ISOClause.objects.all().delete()
        NonConformanceType.objects.all().delete()
        RiskLevel.objects.all().delete()
        RiskImpact.objects.all().delete()
        RiskLikelihood.objects.all().delete()
        RiskCategory.objects.all().delete()

    # ── RiskCategory ─────────────────────────────────────────────────────────

    def _seed_risk_categories(self):
        items = [
            {'code': 'operational',   'name': 'Operational',   'description': 'Risks arising from internal processes, people, systems, or external events', 'sort_order': 1},
            {'code': 'financial',     'name': 'Financial',     'description': 'Risks related to financial loss, budgeting, or fiscal management',           'sort_order': 2},
            {'code': 'strategic',     'name': 'Strategic',     'description': 'Risks that affect the ability to achieve strategic objectives',              'sort_order': 3},
            {'code': 'compliance',    'name': 'Compliance',    'description': 'Risks of non-compliance with laws, regulations, or policies',               'sort_order': 4},
            {'code': 'reputational',  'name': 'Reputational',  'description': 'Risks that may damage institutional reputation or stakeholder trust',       'sort_order': 5},
            {'code': 'technology',    'name': 'Technology',    'description': 'Risks related to ICT systems, cybersecurity, and digital transformation',   'sort_order': 6},
        ]
        ct = 0
        for item in items:
            _, created = RiskCategory.objects.get_or_create(code=item['code'], defaults={**item, 'created_by': uuid.uuid4()})
            if created:
                ct += 1
        self.stdout.write(f'Created {ct} risk categories')

    # ── RiskLikelihood ───────────────────────────────────────────────────────

    def _seed_risk_likelihood(self):
        items = [
            {'code': 'rare',            'name': 'Rare',            'label': 'Rare',            'numerical_value': Decimal('1'), 'description': 'May occur only in exceptional circumstances',             'sort_order': 1},
            {'code': 'unlikely',        'name': 'Unlikely',        'label': 'Unlikely',        'numerical_value': Decimal('2'), 'description': 'Could occur at some time but not expected',               'sort_order': 2},
            {'code': 'possible',        'name': 'Possible',        'label': 'Possible',        'numerical_value': Decimal('3'), 'description': 'Might occur at some time',                               'sort_order': 3},
            {'code': 'likely',          'name': 'Likely',          'label': 'Likely',          'numerical_value': Decimal('4'), 'description': 'Will probably occur in most circumstances',              'sort_order': 4},
            {'code': 'almost_certain',  'name': 'Almost Certain',  'label': 'Almost Certain',  'numerical_value': Decimal('5'), 'description': 'Expected to occur in most circumstances',               'sort_order': 5},
        ]
        ct = 0
        for item in items:
            _, created = RiskLikelihood.objects.get_or_create(code=item['code'], defaults={**item, 'created_by': uuid.uuid4()})
            if created:
                ct += 1
        self.stdout.write(f'Created {ct} risk likelihood levels')

    # ── RiskImpact ───────────────────────────────────────────────────────────

    def _seed_risk_impact(self):
        items = [
            {'code': 'negligible',   'name': 'Negligible',   'label': 'Negligible',   'numerical_value': Decimal('1'), 'description': 'Insignificant impact, easily absorbed',                   'sort_order': 1},
            {'code': 'minor',        'name': 'Minor',        'label': 'Minor',        'numerical_value': Decimal('2'), 'description': 'Minor impact, managed through normal processes',           'sort_order': 2},
            {'code': 'moderate',     'name': 'Moderate',     'label': 'Moderate',     'numerical_value': Decimal('3'), 'description': 'Moderate impact requiring management attention',           'sort_order': 3},
            {'code': 'major',        'name': 'Major',        'label': 'Major',        'numerical_value': Decimal('4'), 'description': 'Major impact affecting strategic objectives',              'sort_order': 4},
            {'code': 'catastrophic', 'name': 'Catastrophic', 'label': 'Catastrophic', 'numerical_value': Decimal('5'), 'description': 'Catastrophic impact threatening organizational survival', 'sort_order': 5},
        ]
        ct = 0
        for item in items:
            _, created = RiskImpact.objects.get_or_create(code=item['code'], defaults={**item, 'created_by': uuid.uuid4()})
            if created:
                ct += 1
        self.stdout.write(f'Created {ct} risk impact levels')

    # ── RiskLevel ────────────────────────────────────────────────────────────

    def _seed_risk_levels(self):
        items = [
            {'code': 'low',      'name': 'Low',      'min_score': Decimal('1'),  'max_score': Decimal('4'),  'color_code': '#22C55E', 'sort_order': 1},
            {'code': 'medium',   'name': 'Medium',   'min_score': Decimal('5'),  'max_score': Decimal('9'),  'color_code': '#EAB308', 'sort_order': 2},
            {'code': 'high',     'name': 'High',     'min_score': Decimal('10'), 'max_score': Decimal('16'), 'color_code': '#F97316', 'sort_order': 3},
            {'code': 'critical', 'name': 'Critical', 'min_score': Decimal('17'), 'max_score': Decimal('25'), 'color_code': '#DC2626', 'sort_order': 4},
        ]
        ct = 0
        for item in items:
            _, created = RiskLevel.objects.get_or_create(code=item['code'], defaults={**item, 'created_by': uuid.uuid4()})
            if created:
                ct += 1
        self.stdout.write(f'Created {ct} risk levels')

    # ── NonConformanceType ───────────────────────────────────────────────────

    def _seed_nc_types(self):
        items = [
            {'code': 'major_nc',                    'name': 'Major Non-Conformance',        'description': 'Absence or total breakdown of a system to meet a requirement',                     'sort_order': 1},
            {'code': 'minor_nc',                    'name': 'Minor Non-Conformance',        'description': 'Single observed lapse in meeting a requirement',                                   'sort_order': 2},
            {'code': 'observation',                 'name': 'Observation',                   'description': 'Issue noted that could lead to a non-conformance if not addressed',                'sort_order': 3},
            {'code': 'opportunity_for_improvement', 'name': 'Opportunity for Improvement',  'description': 'Suggestion for enhancing the effectiveness of the quality management system',     'sort_order': 4},
        ]
        ct = 0
        for item in items:
            _, created = NonConformanceType.objects.get_or_create(code=item['code'], defaults={**item, 'created_by': uuid.uuid4()})
            if created:
                ct += 1
        self.stdout.write(f'Created {ct} non-conformance types')

    # ── ISOClause (ISO 9001:2015 Clauses 4–10) ──────────────────────────────

    def _seed_iso_clauses(self):
        # Top-level clauses 4–10
        top_clauses = [
            {'code': '4',  'clause_number': '4',  'title': 'Context of the Organization', 'sort_order': 40},
            {'code': '5',  'clause_number': '5',  'title': 'Leadership',                  'sort_order': 50},
            {'code': '6',  'clause_number': '6',  'title': 'Planning',                    'sort_order': 60},
            {'code': '7',  'clause_number': '7',  'title': 'Support',                     'sort_order': 70},
            {'code': '8',  'clause_number': '8',  'title': 'Operation',                   'sort_order': 80},
            {'code': '9',  'clause_number': '9',  'title': 'Performance Evaluation',      'sort_order': 90},
            {'code': '10', 'clause_number': '10', 'title': 'Improvement',                 'sort_order': 100},
        ]

        parent_map = {}
        ct = 0
        for item in top_clauses:
            obj, created = ISOClause.objects.get_or_create(
                code=item['code'],
                defaults={
                    'clause_number': item['clause_number'],
                    'title': item['title'],
                    'sort_order': item['sort_order'],
                    'created_by': uuid.uuid4(),
                },
            )
            parent_map[item['code']] = obj
            if created:
                ct += 1

        # Sub-clauses
        sub_clauses = [
            # Clause 4 – Context of the Organization
            {'code': '4.1', 'clause_number': '4.1', 'title': 'Understanding the organization and its context',                    'parent': '4', 'sort_order': 41},
            {'code': '4.2', 'clause_number': '4.2', 'title': 'Understanding the needs and expectations of interested parties',    'parent': '4', 'sort_order': 42},
            {'code': '4.3', 'clause_number': '4.3', 'title': 'Determining the scope of the quality management system',            'parent': '4', 'sort_order': 43},
            {'code': '4.4', 'clause_number': '4.4', 'title': 'Quality management system and its processes',                       'parent': '4', 'sort_order': 44},

            # Clause 5 – Leadership
            {'code': '5.1', 'clause_number': '5.1', 'title': 'Leadership and commitment',           'parent': '5', 'sort_order': 51},
            {'code': '5.2', 'clause_number': '5.2', 'title': 'Policy',                              'parent': '5', 'sort_order': 52},
            {'code': '5.3', 'clause_number': '5.3', 'title': 'Organizational roles, responsibilities and authorities', 'parent': '5', 'sort_order': 53},

            # Clause 6 – Planning
            {'code': '6.1', 'clause_number': '6.1', 'title': 'Actions to address risks and opportunities', 'parent': '6', 'sort_order': 61},
            {'code': '6.2', 'clause_number': '6.2', 'title': 'Quality objectives and planning to achieve them', 'parent': '6', 'sort_order': 62},
            {'code': '6.3', 'clause_number': '6.3', 'title': 'Planning of changes',                       'parent': '6', 'sort_order': 63},

            # Clause 7 – Support
            {'code': '7.1',   'clause_number': '7.1',   'title': 'Resources',                              'parent': '7', 'sort_order': 71},
            {'code': '7.1.1', 'clause_number': '7.1.1', 'title': 'General',                                'parent': '7', 'sort_order': 711},
            {'code': '7.1.2', 'clause_number': '7.1.2', 'title': 'People',                                 'parent': '7', 'sort_order': 712},
            {'code': '7.1.3', 'clause_number': '7.1.3', 'title': 'Infrastructure',                         'parent': '7', 'sort_order': 713},
            {'code': '7.1.4', 'clause_number': '7.1.4', 'title': 'Environment for the operation of processes', 'parent': '7', 'sort_order': 714},
            {'code': '7.1.5', 'clause_number': '7.1.5', 'title': 'Monitoring and measuring resources',     'parent': '7', 'sort_order': 715},
            {'code': '7.1.6', 'clause_number': '7.1.6', 'title': 'Organizational knowledge',               'parent': '7', 'sort_order': 716},
            {'code': '7.2',   'clause_number': '7.2',   'title': 'Competence',                             'parent': '7', 'sort_order': 72},
            {'code': '7.3',   'clause_number': '7.3',   'title': 'Awareness',                              'parent': '7', 'sort_order': 73},
            {'code': '7.4',   'clause_number': '7.4',   'title': 'Communication',                          'parent': '7', 'sort_order': 74},
            {'code': '7.5',   'clause_number': '7.5',   'title': 'Documented information',                 'parent': '7', 'sort_order': 75},

            # Clause 8 – Operation
            {'code': '8.1', 'clause_number': '8.1', 'title': 'Operational planning and control',            'parent': '8', 'sort_order': 81},
            {'code': '8.2', 'clause_number': '8.2', 'title': 'Requirements for products and services',     'parent': '8', 'sort_order': 82},
            {'code': '8.3', 'clause_number': '8.3', 'title': 'Design and development of products and services', 'parent': '8', 'sort_order': 83},
            {'code': '8.4', 'clause_number': '8.4', 'title': 'Control of externally provided processes, products and services', 'parent': '8', 'sort_order': 84},
            {'code': '8.5', 'clause_number': '8.5', 'title': 'Production and service provision',           'parent': '8', 'sort_order': 85},
            {'code': '8.6', 'clause_number': '8.6', 'title': 'Release of products and services',           'parent': '8', 'sort_order': 86},
            {'code': '8.7', 'clause_number': '8.7', 'title': 'Control of nonconforming outputs',           'parent': '8', 'sort_order': 87},

            # Clause 9 – Performance Evaluation
            {'code': '9.1', 'clause_number': '9.1', 'title': 'Monitoring, measurement, analysis and evaluation', 'parent': '9', 'sort_order': 91},
            {'code': '9.2', 'clause_number': '9.2', 'title': 'Internal audit',                                   'parent': '9', 'sort_order': 92},
            {'code': '9.3', 'clause_number': '9.3', 'title': 'Management review',                                'parent': '9', 'sort_order': 93},

            # Clause 10 – Improvement
            {'code': '10.1', 'clause_number': '10.1', 'title': 'General',                    'parent': '10', 'sort_order': 101},
            {'code': '10.2', 'clause_number': '10.2', 'title': 'Nonconformity and corrective action', 'parent': '10', 'sort_order': 102},
            {'code': '10.3', 'clause_number': '10.3', 'title': 'Continual improvement',      'parent': '10', 'sort_order': 103},
        ]

        for item in sub_clauses:
            parent_obj = parent_map.get(item['parent'])
            _, created = ISOClause.objects.get_or_create(
                code=item['code'],
                defaults={
                    'clause_number': item['clause_number'],
                    'title': item['title'],
                    'parent_clause': parent_obj,
                    'sort_order': item['sort_order'],
                    'created_by': uuid.uuid4(),
                },
            )
            if created:
                ct += 1

        self.stdout.write(f'Created {ct} ISO 9001:2015 clauses')
