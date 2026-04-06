"""Universal nodes, city-tier activations, and seasonal overlays."""

from __future__ import annotations

from pathlib import Path

import yaml


# 17 universal nodes — always ON at weight 1.0 for every user
UNIVERSAL_NODES: dict[str, float] = {
    # I2 Cost of Living
    "staple_grains": 1.0,
    "pulses_and_dals": 1.0,
    "dairy_and_eggs": 1.0,
    "edible_oils": 1.0,
    "spices_sugar_salt": 1.0,
    "electricity_tariff": 1.0,
    "lpg_cylinder": 1.0,
    # I3 Mobility
    "road_conditions_and_closures": 1.0,
    # I4 Health
    "hospital_and_medical_care": 1.0,
    "medicines_and_pharmaceuticals": 1.0,
    "respiratory_and_viral_infections": 1.0,
    # I6 Civic
    "identity_and_travel_documents": 1.0,
    "indirect_taxes_gst": 1.0,
    # I7 Habitat
    "air_pollution": 1.0,
    "extreme_heat": 1.0,
    # I8 Digital
    "mobile_tariffs": 1.0,
    "spam_and_scams": 1.0,
}

UNIVERSAL_FLOOR = 0.5  # universal nodes can't be suppressed below this

# City-tier activations — applied automatically based on s0_city answer
CITY_TIER_ACTIVATIONS: dict[str, dict[str, float]] = {
    "metro": {
        "traffic_congestion": 0.8,
        "metro_and_local_train": 0.7,
        "ride_hailing_cabs_bikes": 0.7,
        "food_delivery_services": 0.6,
        "parking_fees": 0.5,
        "residential_rent_and_pg": 0.7,
        "broadband_and_wifi": 0.6,
    },
    "tier2": {
        "auto_e_rickshaw": 0.7,
        "city_bus_transit": 0.6,
        "street_waterlogging": 0.5,
        "road_conditions_and_closures": 0.7,
    },
    "rural": {
        "farm_labor_wages": 0.5,
        "mgnrega_wages": 0.5,
        "water_supply_and_tankers": 0.7,
        "drinking_water_contamination": 0.6,
        "welfare_and_ration_cards": 0.7,
        "piped_natural_gas": 0.0,  # not available rural
    },
}

# Seasonal activations — applied based on city's seasonal flags
SEASONAL_ACTIVATIONS: dict[str, dict[str, float]] = {
    "winter_smog": {"winter_smog": 0.8},
    "extreme_heat": {"extreme_heat": 0.8},
    "street_waterlogging": {"street_waterlogging": 0.7},
    "extreme_cold": {"extreme_cold": 0.8},
}


def load_city_lookup(path: str = "profiling/cities.yaml") -> dict[str, dict]:
    """Load city YAML, return name/alias -> city_info dict (lowercase keys)."""
    with open(Path(path)) as f:
        data = yaml.safe_load(f)

    lookup: dict[str, dict] = {}
    for city in data.get("cities", []):
        info = {
            "name": city["name"],
            "tier": city["tier"],
            "seasonal": city.get("seasonal", {}),
            "state": city.get("state", ""),
        }
        # Index by canonical name
        lookup[city["name"].lower()] = info
        # Index by every alias
        for alias in city.get("aliases", []):
            lookup[alias.lower()] = info

    return lookup
