import yaml
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SectorMapper:
    """
    Handles mapping from EDINET industry names to internal sector names/codes.
    Loads definition from config/sector_definition.yml.
    """

    _instance = None
    _config = None
    _mapping_dict = {}
    _default_sector = "その他"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SectorMapper, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = os.path.join(os.getcwd(), "config", "sector_definition.yml")
        if not os.path.exists(config_path):
            logger.warning(
                f"Sector config not found at {config_path}. Using empty mapping."
            )
            self._config = {}
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)

            self._default_sector = self._config.get("default_sector", "その他")
            mappings = self._config.get("mappings", [])

            # Create dictionary for O(1) lookup
            for item in mappings:
                edinet_name = item.get("edinet_name")
                internal_name = item.get("internal_name")
                if edinet_name and internal_name:
                    self._mapping_dict[edinet_name] = internal_name

            logger.info(
                f"Loaded {len(self._mapping_dict)} sector mappings (Version: {self._config.get('version')})"
            )

        except Exception as e:
            logger.error(f"Failed to load sector config: {e}")

    def get_internal_sector_name(self, edinet_name: str) -> str:
        """
        Resolve EDINET industry name to internal sector name.
        Returns default sector if not found.
        """
        if not edinet_name:
            return self._default_sector

        # Exact match
        if edinet_name in self._mapping_dict:
            return self._mapping_dict[edinet_name]

        # Fallback
        logger.warning(
            f"Unknown EDINET sector '{edinet_name}'. Mapping to default '{self._default_sector}'."
        )
        return self._default_sector
