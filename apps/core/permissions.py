"""
GRC Service Permission Definitions.
Loaded from config/permissions/grc-service.json and published to IAM via Kafka.
"""
from __future__ import annotations

import json
import logging
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from django.conf import settings

    BASE_DIR = Path(settings.BASE_DIR)
except Exception:  # pragma: no cover - used before Django loads
    BASE_DIR = Path(__file__).resolve().parents[2]


CONFIG_PATH = BASE_DIR / "config" / "permissions" / "grc-service.json"
logger = logging.getLogger(__name__)


class PermissionConfigLoader:
    """Load and validate the declarative permission configuration."""

    REQUIRED_SERVICE_FIELDS = ("name", "version", "description")
    REQUIRED_PERMISSION_FIELDS = (
        "permission_code",
        "name",
        "description",
        "resource_type",
        "action",
        "category",
    )

    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(f"Permission config not found: {self.path}")

        try:
            with self.path.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except json.JSONDecodeError as exc:  # pragma: no cover - configuration error
            raise ValueError(f"Permission config is not valid JSON: {exc}") from exc

        service = payload.get("service") or {}
        missing_service = [field for field in self.REQUIRED_SERVICE_FIELDS if field not in service]
        if missing_service:
            raise ValueError(
                f"Missing service fields in permission config: {missing_service}"
            )

        permissions = payload.get("permissions") or []
        if not permissions:
            raise ValueError("Permission config must include at least one permission.")

        validated_permissions: List[Dict[str, Any]] = []
        seen_codes = set()
        for raw in permissions:
            missing = [field for field in self.REQUIRED_PERMISSION_FIELDS if field not in raw]
            if missing:
                raise ValueError(
                    f"Permission '{raw}' is missing required fields: {missing}"
                )
            code = raw["permission_code"]
            if code in seen_codes:
                raise ValueError(f"Duplicate permission_code detected: {code}")
            seen_codes.add(code)
            validated_permissions.append(raw)

        roles = payload.get("roles") or []

        return {
            "service": service,
            "permissions": validated_permissions,
            "roles": roles,
        }


class GrcServicePermissions:
    """Permission registry facade backed by the JSON configuration."""

    _CONFIG = PermissionConfigLoader().load()

    SERVICE_NAME = _CONFIG["service"]["name"]
    SERVICE_VERSION = _CONFIG["service"]["version"]
    SERVICE_DESCRIPTION = _CONFIG["service"]["description"]

    PERMISSIONS: List[Dict[str, Any]] = _CONFIG["permissions"]
    _PERMISSION_INDEX: Dict[str, Dict[str, Any]] = {
        perm["permission_code"]: perm for perm in PERMISSIONS
    }

    @classmethod
    def get_permission_registration_data(cls) -> Dict[str, Any]:
        """Payload used by the Kafka publisher."""

        return {
            "service_name": cls.SERVICE_NAME,
            "service_version": cls.SERVICE_VERSION,
            "service_description": cls.SERVICE_DESCRIPTION,
            "registration_timestamp": None,
            "permissions": cls.PERMISSIONS,
            "total_permissions": len(cls.PERMISSIONS),
            "permission_hash": cls.get_permission_hash(),
        }

    @classmethod
    def get_permission_by_code(cls, permission_code: str) -> Optional[Dict[str, Any]]:
        """Return a specific permission by its code."""

        return cls._PERMISSION_INDEX.get(permission_code)

    @classmethod
    def get_permissions_by_category(cls, category: str) -> List[Dict[str, Any]]:
        """Return all permissions in a specific category."""

        return [perm for perm in cls.PERMISSIONS if perm.get("category") == category]

    @classmethod
    def get_permissions_by_resource_type(cls, resource_type: str) -> List[Dict[str, Any]]:
        """Return all permissions for a specific resource type."""

        return [
            perm for perm in cls.PERMISSIONS if perm.get("resource_type") == resource_type
        ]

    @classmethod
    def get_permission_hash(cls) -> str:
        """Deterministic hash of the current permission set (service + version + codes)."""

        digest_payload = {
            "service_name": cls.SERVICE_NAME,
            "service_version": cls.SERVICE_VERSION,
            "permissions": sorted(cls._PERMISSION_INDEX.keys()),
        }
        return sha256(json.dumps(digest_payload, sort_keys=True).encode("utf-8")).hexdigest()


GRC_SERVICE_ROLES: List[Dict[str, Any]] = []  # Roles are curated inside IAM
