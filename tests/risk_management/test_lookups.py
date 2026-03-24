"""
Risk Management Module — Lookup Table Tests (Phase 3)

Coverage:
  - All 6 risk lookup models: creation, unique codes, sort_order, __str__
  - Seed command idempotency (seed_risk_lookups)
  - Lookup API endpoints: 6 individual + 1 combined
  - ISOClause parent/sub-clause hierarchy
  - RiskLevel score range accuracy
  - Config (admin CRUD) endpoint access
"""
import uuid
import datetime
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import IntegrityError

from apps.core.models.lookups import (
    RiskCategory, RiskLikelihood, RiskImpact, RiskLevel,
    NonConformanceType, ISOClause,
    RiskSector, StrategicObjective,
)
from tests.risk_management.conftest import SYSTEM_USER_ID


# ===========================================================================
# RiskCategory Tests
# ===========================================================================

class TestRiskCategoryLookup:

    @pytest.mark.django_db
    def test_creation(self, risk_category):
        assert risk_category.code == 'operational'
        assert risk_category.name == 'Operational'
        assert risk_category.is_active is True

    @pytest.mark.django_db
    def test_unique_code(self, risk_category):
        with pytest.raises(IntegrityError):
            RiskCategory.objects.create(
                code='operational', name='Duplicate',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, risk_category):
        assert 'Operational' in str(risk_category)
        assert 'operational' in str(risk_category)

    @pytest.mark.django_db
    def test_ordering(self, risk_category, risk_category_financial):
        cats = list(RiskCategory.objects.all())
        assert cats[0].sort_order <= cats[1].sort_order


# ===========================================================================
# RiskLikelihood Tests
# ===========================================================================

class TestRiskLikelihoodLookup:

    @pytest.mark.django_db
    def test_creation(self, likelihood_low):
        assert likelihood_low.code == 'rare'
        assert likelihood_low.numerical_value == Decimal('1')

    @pytest.mark.django_db
    def test_unique_code(self, likelihood_low):
        with pytest.raises(IntegrityError):
            RiskLikelihood.objects.create(
                code='rare', name='Duplicate',
                numerical_value=Decimal('1'),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, likelihood_low):
        assert 'Rare' in str(likelihood_low)
        assert '1' in str(likelihood_low)

    @pytest.mark.django_db
    def test_ordering(self, likelihood_low, likelihood_high):
        items = list(RiskLikelihood.objects.all())
        assert items[0].sort_order <= items[-1].sort_order


# ===========================================================================
# RiskImpact Tests
# ===========================================================================

class TestRiskImpactLookup:

    @pytest.mark.django_db
    def test_creation(self, impact_low):
        assert impact_low.code == 'negligible'
        assert impact_low.numerical_value == Decimal('1')

    @pytest.mark.django_db
    def test_unique_code(self, impact_low):
        with pytest.raises(IntegrityError):
            RiskImpact.objects.create(
                code='negligible', name='Duplicate',
                numerical_value=Decimal('1'),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, impact_low):
        assert 'Negligible' in str(impact_low)

    @pytest.mark.django_db
    def test_numerical_value_stored(self, impact_high):
        assert impact_high.numerical_value == Decimal('4')


# ===========================================================================
# RiskLevel Tests
# ===========================================================================

class TestRiskLevelLookup:

    @pytest.mark.django_db
    def test_creation(self, risk_level_low):
        assert risk_level_low.code == 'low'
        assert risk_level_low.min_score == Decimal('1')
        assert risk_level_low.max_score == Decimal('4')
        assert risk_level_low.color_code == '#22C55E'

    @pytest.mark.django_db
    def test_unique_code(self, risk_level_low):
        with pytest.raises(IntegrityError):
            RiskLevel.objects.create(
                code='low', name='Duplicate',
                min_score=Decimal('0'), max_score=Decimal('1'),
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, risk_level_low):
        s = str(risk_level_low)
        assert 'Low' in s
        assert '1' in s
        assert '4' in s

    @pytest.mark.django_db
    def test_score_range_non_overlapping(self, risk_level_low, risk_level_high):
        """Low max_score < High min_score — no overlap."""
        assert risk_level_low.max_score < risk_level_high.min_score


# ===========================================================================
# NonConformanceType Tests
# ===========================================================================

class TestNonConformanceTypeLookup:

    @pytest.mark.django_db
    def test_creation(self, nc_type_major):
        assert nc_type_major.code == 'major_nc'
        assert nc_type_major.name == 'Major Non-Conformance'

    @pytest.mark.django_db
    def test_unique_code(self, nc_type_major):
        with pytest.raises(IntegrityError):
            NonConformanceType.objects.create(
                code='major_nc', name='Duplicate',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, nc_type_major):
        assert 'Major Non-Conformance' in str(nc_type_major)


# ===========================================================================
# ISOClause Tests
# ===========================================================================

class TestISOClauseLookup:

    @pytest.mark.django_db
    def test_parent_creation(self, iso_clause_parent):
        assert iso_clause_parent.code == '9'
        assert iso_clause_parent.title == 'Performance Evaluation'
        assert iso_clause_parent.parent_clause is None

    @pytest.mark.django_db
    def test_sub_clause_creation(self, iso_clause, iso_clause_parent):
        assert iso_clause.code == '9.2'
        assert iso_clause.parent_clause == iso_clause_parent

    @pytest.mark.django_db
    def test_unique_code(self, iso_clause):
        with pytest.raises(IntegrityError):
            ISOClause.objects.create(
                code='9.2', clause_number='9.2', title='Duplicate',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, iso_clause):
        s = str(iso_clause)
        assert '9.2' in s
        assert 'Internal audit' in s

    @pytest.mark.django_db
    def test_parent_sub_clause_relationship(self, iso_clause, iso_clause_parent):
        """Parent has sub_clauses reverse relation."""
        subs = list(iso_clause_parent.sub_clauses.all())
        assert len(subs) == 1
        assert subs[0] == iso_clause


# ===========================================================================
# Seed Command Tests
# ===========================================================================

class TestSeedRiskLookups:

    @pytest.mark.django_db
    def test_seed_creates_data(self):
        """Running seed_risk_lookups populates all 6 lookup tables."""
        call_command('seed_risk_lookups')
        assert RiskCategory.objects.count() == 6
        assert RiskLikelihood.objects.count() == 5
        assert RiskImpact.objects.count() == 5
        assert RiskLevel.objects.count() == 4
        assert NonConformanceType.objects.count() == 4
        assert ISOClause.objects.count() == 41

    @pytest.mark.django_db
    def test_seed_idempotent(self):
        """Running seed twice does not duplicate records."""
        call_command('seed_risk_lookups')
        call_command('seed_risk_lookups')
        assert RiskCategory.objects.count() == 6
        assert RiskLikelihood.objects.count() == 5
        assert ISOClause.objects.count() == 41

    @pytest.mark.django_db
    def test_seed_force_recreates(self):
        """Running with --force clears and re-seeds."""
        call_command('seed_risk_lookups')
        assert RiskCategory.objects.count() == 6
        call_command('seed_risk_lookups', force=True)
        assert RiskCategory.objects.count() == 6

    @pytest.mark.django_db
    def test_seed_iso_clause_hierarchy(self):
        """Seed creates parent-child ISO clause relationships."""
        call_command('seed_risk_lookups')
        top = ISOClause.objects.filter(parent_clause__isnull=True)
        sub = ISOClause.objects.filter(parent_clause__isnull=False)
        assert top.count() == 7
        assert sub.count() == 34

    @pytest.mark.django_db
    def test_seed_risk_level_ranges(self):
        """Seeded risk levels cover score range 1–25 without gaps."""
        call_command('seed_risk_lookups')
        levels = list(RiskLevel.objects.order_by('sort_order'))
        assert levels[0].min_score == Decimal('1')
        assert levels[-1].max_score == Decimal('25')
        for i in range(len(levels) - 1):
            assert levels[i].max_score + 1 == levels[i + 1].min_score

    @pytest.mark.django_db
    def test_seed_likelihood_values_1_to_5(self):
        """Seeded likelihoods have values 1 through 5."""
        call_command('seed_risk_lookups')
        values = sorted(RiskLikelihood.objects.values_list('numerical_value', flat=True))
        assert values == [Decimal(str(i)) for i in range(1, 6)]

    @pytest.mark.django_db
    def test_seed_impact_values_1_to_5(self):
        """Seeded impacts have values 1 through 5."""
        call_command('seed_risk_lookups')
        values = sorted(RiskImpact.objects.values_list('numerical_value', flat=True))
        assert values == [Decimal(str(i)) for i in range(1, 6)]


# ===========================================================================
# Lookup API Endpoint Tests
# ===========================================================================

class TestLookupAPIEndpoints:

    @pytest.mark.django_db
    def test_risk_categories_list(self, rmqam_client, risk_category, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-categories/')
        assert resp.status_code == 200
        assert resp.json()['success'] is True
        assert len(resp.json()['data']) >= 1

    @pytest.mark.django_db
    def test_risk_likelihoods_list(self, rmqam_client, likelihood_low, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-likelihoods/')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['code'] == 'rare'

    @pytest.mark.django_db
    def test_risk_impacts_list(self, rmqam_client, impact_low, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-impacts/')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['code'] == 'negligible'

    @pytest.mark.django_db
    def test_risk_levels_list(self, rmqam_client, risk_level_low, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-levels/')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data[0]['color_code'] == '#22C55E'

    @pytest.mark.django_db
    def test_nc_types_list(self, rmqam_client, nc_type_major, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/non-conformance-types/')
        assert resp.status_code == 200
        assert resp.json()['data'][0]['code'] == 'major_nc'

    @pytest.mark.django_db
    def test_iso_clauses_list(self, rmqam_client, iso_clause, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/iso-clauses/')
        assert resp.status_code == 200
        assert len(resp.json()['data']) >= 1

    @pytest.mark.django_db
    def test_combined_risk_lookups(self, rmqam_client, risk_category, likelihood_low,
                                    impact_low, risk_level_low, nc_type_major,
                                    iso_clause, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk/')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert 'risk_categories' in data
        assert 'risk_likelihoods' in data
        assert 'risk_impacts' in data
        assert 'risk_levels' in data
        assert 'non_conformance_types' in data
        assert 'iso_clauses' in data

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, risk_category):
        resp = anon_client.get('/api/v1/grc/audit/lookups/risk-categories/')
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_no_permissions_returns_403(self, rmqam_client, risk_category, deny_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/audit/lookups/risk-categories/')
        assert resp.status_code == 403


# ===========================================================================
# Config (Admin CRUD) Endpoint Tests
# ===========================================================================

class TestConfigEndpoints:

    @pytest.mark.django_db
    def test_config_risk_categories_list(self, rmqam_client, risk_category, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/config/risk-categories/')
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    @pytest.mark.django_db
    def test_config_risk_categories_create(self, rmqam_client, allow_all_permissions):
        resp = rmqam_client.post('/api/v1/grc/config/risk-categories/', {
            'code': 'environmental',
            'name': 'Environmental',
            'description': 'Environmental risks',
            'sort_order': 10,
        }, format='json')
        assert resp.status_code == 201
        assert RiskCategory.objects.filter(code='environmental').exists()

    @pytest.mark.django_db
    def test_config_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.get('/api/v1/grc/config/risk-categories/')
        assert resp.status_code == 401


# ===========================================================================
# RiskSector Tests
# ===========================================================================

class TestRiskSectorLookup:

    @pytest.mark.django_db
    def test_creation(self, risk_sector):
        assert risk_sector.code == 'health'
        assert risk_sector.name == 'Health'
        assert risk_sector.is_active is True

    @pytest.mark.django_db
    def test_unique_code(self, risk_sector):
        with pytest.raises(IntegrityError):
            RiskSector.objects.create(
                code='health', name='Duplicate',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, risk_sector):
        assert 'Health' in str(risk_sector)
        assert 'health' in str(risk_sector)

    @pytest.mark.django_db
    def test_ordering(self, risk_sector, risk_sector_finance):
        items = list(RiskSector.objects.all())
        assert items[0].sort_order <= items[1].sort_order


# ===========================================================================
# StrategicObjective Tests
# ===========================================================================

class TestStrategicObjectiveLookup:

    @pytest.mark.django_db
    def test_creation(self, strategic_objective):
        assert strategic_objective.code == 'SO-01'
        assert 'compliance' in strategic_objective.name.lower()
        assert strategic_objective.is_active is True

    @pytest.mark.django_db
    def test_unique_code(self, strategic_objective):
        with pytest.raises(IntegrityError):
            StrategicObjective.objects.create(
                code='SO-01', name='Duplicate',
                created_by=SYSTEM_USER_ID,
            )

    @pytest.mark.django_db
    def test_str(self, strategic_objective):
        s = str(strategic_objective)
        assert 'SO-01' in s

    @pytest.mark.django_db
    def test_ordering(self, strategic_objective, strategic_objective_secondary):
        items = list(StrategicObjective.objects.all())
        assert items[0].sort_order <= items[1].sort_order


# ===========================================================================
# Config (Admin CRUD) — RiskSector & StrategicObjective Endpoints
# ===========================================================================

class TestConfigRiskSectorEndpoints:

    @pytest.mark.django_db
    def test_list(self, rmqam_client, risk_sector, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/config/risk-sectors/')
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    @pytest.mark.django_db
    def test_create(self, rmqam_client, allow_all_permissions):
        resp = rmqam_client.post('/api/v1/grc/config/risk-sectors/', {
            'code': 'services',
            'name': 'Services',
            'description': 'Service sector risks',
            'sort_order': 3,
        }, format='json')
        assert resp.status_code == 201
        assert RiskSector.objects.filter(code='services').exists()

    @pytest.mark.django_db
    def test_retrieve(self, rmqam_client, risk_sector, allow_all_permissions):
        resp = rmqam_client.get(f'/api/v1/grc/config/risk-sectors/{risk_sector.id}/')
        assert resp.status_code == 200
        assert resp.json()['data']['code'] == 'health'

    @pytest.mark.django_db
    def test_update(self, rmqam_client, risk_sector, allow_all_permissions):
        resp = rmqam_client.put(
            f'/api/v1/grc/config/risk-sectors/{risk_sector.id}/',
            {'name': 'Health Updated'},
            format='json',
        )
        assert resp.status_code == 200
        risk_sector.refresh_from_db()
        assert risk_sector.name == 'Health Updated'

    @pytest.mark.django_db
    def test_soft_delete(self, rmqam_client, risk_sector, allow_all_permissions):
        resp = rmqam_client.delete(f'/api/v1/grc/config/risk-sectors/{risk_sector.id}/')
        assert resp.status_code == 200
        risk_sector.refresh_from_db()
        assert risk_sector.is_active is False

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.get('/api/v1/grc/config/risk-sectors/')
        assert resp.status_code == 401


class TestConfigStrategicObjectiveEndpoints:

    @pytest.mark.django_db
    def test_list(self, rmqam_client, strategic_objective, allow_all_permissions):
        resp = rmqam_client.get('/api/v1/grc/config/strategic-objectives/')
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    @pytest.mark.django_db
    def test_create(self, rmqam_client, allow_all_permissions):
        resp = rmqam_client.post('/api/v1/grc/config/strategic-objectives/', {
            'code': 'SO-03',
            'name': 'Improve service delivery',
            'description': 'Service delivery objective',
            'sort_order': 3,
        }, format='json')
        assert resp.status_code == 201
        assert StrategicObjective.objects.filter(code='SO-03').exists()

    @pytest.mark.django_db
    def test_retrieve(self, rmqam_client, strategic_objective, allow_all_permissions):
        resp = rmqam_client.get(f'/api/v1/grc/config/strategic-objectives/{strategic_objective.id}/')
        assert resp.status_code == 200
        assert resp.json()['data']['code'] == 'SO-01'

    @pytest.mark.django_db
    def test_update(self, rmqam_client, strategic_objective, allow_all_permissions):
        resp = rmqam_client.put(
            f'/api/v1/grc/config/strategic-objectives/{strategic_objective.id}/',
            {'name': 'Updated objective'},
            format='json',
        )
        assert resp.status_code == 200
        strategic_objective.refresh_from_db()
        assert strategic_objective.name == 'Updated objective'

    @pytest.mark.django_db
    def test_soft_delete(self, rmqam_client, strategic_objective, allow_all_permissions):
        resp = rmqam_client.delete(f'/api/v1/grc/config/strategic-objectives/{strategic_objective.id}/')
        assert resp.status_code == 200
        strategic_objective.refresh_from_db()
        assert strategic_objective.is_active is False

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.get('/api/v1/grc/config/strategic-objectives/')
        assert resp.status_code == 401
