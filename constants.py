"""
constants.py — Shared constants used across all modules.
"""

from defaults import MATRIX_DEFAULTS

LOREM = (
    "Lorem ipsum dolor sit amet consectetur adipiscing elit. "
    "Quisque faucibus ex sapien vitae pellentesque sem placerat. "
    "In id cursus mi pretium tellus duis convallis. "
    "Tempus leo eu aenean sed diam urna tempor. "
    "Pulvinar vivamus fringilla lacus nec metus bibendum egestas. "
    "Iaculis massa nisl malesuada lacinia integer nunc posuere. "
    "Ut hendrerit semper vel class aptent taciti sociosqu. "
    "Ad litora torquent per conubia nostra inceptos himenaeos."
)

SYSTEMS = [
    {"key": "fire_alarm",    "label": "Fire Alarm",    "desc_ph": "fire_alarm_description",      "int_ph": "fire_alarm_integrations",     "matrix_prefix": None,    "tp_prefix": "mon"},
    {"key": "sprinkler",     "label": "Sprinkler",     "desc_ph": "sprinkler_description",        "int_ph": "sprinkler_integrations",      "matrix_prefix": "sprk",  "tp_prefix": "sprk"},
    {"key": "standpipe",     "label": "Standpipe",     "desc_ph": "standpipe_description",        "int_ph": "standpipe_integrations",      "matrix_prefix": "stand", "tp_prefix": "stnd"},
    {"key": "pre_action",    "label": "Pre-Action Sprinkler", "desc_ph": "preaction_description",       "int_ph": "preaction_integrations",     "matrix_prefix": "pact",  "tp_prefix": "pact"},
    {"key": "fire_pump",     "label": "Fire Pump",     "desc_ph": "fire_pump_description",        "int_ph": "fire_pump_integrations",      "matrix_prefix": "fpmp",  "tp_prefix": "fpmp"},
    {"key": "generator",     "label": "Generator",     "desc_ph": "generator_description",        "int_ph": "generator_integrations",      "matrix_prefix": "gen",   "tp_prefix": "gen"},
    {"key": "maglock",       "label": "Maglocks",      "desc_ph": "maglock_description",          "int_ph": "maglock_integrations",        "matrix_prefix": "mglck", "tp_prefix": "mglck"},
    {"key": "door_holders",  "label": "Door Holders",  "desc_ph": "door_holders_description",     "int_ph": "door_holders_integrations",   "matrix_prefix": "dhldr", "tp_prefix": "dhldr"},
    {"key": "ahu",           "label": "AHU/Fan",       "desc_ph": "ahu_description",              "int_ph": "ahu_integrations",            "matrix_prefix": "ahu",   "tp_prefix": "ahu"},
    {"key": "smoke_dampers", "label": "Smoke Dampers", "desc_ph": "smoke_dampers_description",    "int_ph": "smoke_dampers_integrations",  "matrix_prefix": "sdmpr", "tp_prefix": "sdmpr"},
    {"key": "fire_shutters", "label": "Fire Shutters", "desc_ph": "fire_shutters_description",    "int_ph": "fire_shutters_integrations",  "matrix_prefix": "fshtr", "tp_prefix": "fshtr"},
    {"key": "kitchen_hood",  "label": "Kitchen Hood",  "desc_ph": "hood_suppression_description", "int_ph": "hood_suppression_integrations","matrix_prefix": "ktchn", "tp_prefix": "ktchn"},
    {"key": "elevator",      "label": "Elevator",      "desc_ph": "elevator_description",         "int_ph": "elevator_interconnections",   "matrix_prefix": "elev",  "tp_prefix": "elev"},
    {"key": "water_mist",    "label": "Water Mist",    "desc_ph": "water_mist_description",       "int_ph": "water_mist_interconnections",  "matrix_prefix": "watmst", "tp_prefix": "watmst"},
]

MONITORING_MATRIX_DEFAULTS = MATRIX_DEFAULTS["fire_alarm_monitoring"]

CONTACT_TYPES = [
    "Owner/Owner's Representative",
    "Fire Protection Engineer",
    "Integrated Testing Coordinator",
    "Electrical Contractor", "Fire Alarm Contractor", "Sprinkler System Contractor",
    "Mechanical Contractor", "Security Contractor", "General Contractor",
]

OCCUPANCY_TYPES = [
    "Group A, Division 1 - Assembly Occupancies for Production & Viewing of Performing Arts",
    "Group A, Division 2 - Assembly Occupancies (Not Listed Elsewhere)",
    "Group A, Division 3 - Assembly Occupancies (Arena Type)",
    "Group A, Division 4 - Assembly Occupancies (Open Air)",
    "Group B, Division 1 - Detention Occupancies",
    "Group B, Division 2 - Care & Treatment Occupancies",
    "Group B, Division 3 - Care Occupancies",
    "Group C - Residential Occupancies",
    "Group D - Business & Personal Service Occupancies",
    "Group E - Mercantile Occupancies",
    "Group F, Division 1 - High Hazard Industrial Occupancies",
    "Group F, Division 2 - Medium Hazard Industrial Occupancies",
    "Group F, Division 3 - Low Hazard Industrial Occupancies",
]