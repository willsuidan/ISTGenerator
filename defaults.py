# defaults.py
# Default system description and integration text for IST reports.
# Use \n\n to separate paragraphs within a single field.
# Placeholders like {{facp_room}} are resolved at report generation time.

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

SYSTEM_DEFAULTS = {

    "fire_alarm": {
        "description": (
            "The building is protected by an addressable, single-stage fire alarm system. "
            "The fire alarm control panel is located in the {{facp_room}} on the {{facp_floor}} of the building. "
            "The fire alarm annunciator panel is located in the {{faap_room}} on the {{faap_floor}} of the building."
            "\n\n"
            "Fire alarm initiating devices include {{fa_initiating_devices}}."
            "\n\n"
            "The fire alarm supervises various fire protection systems within the building. "
            "Supervisory devices include {{fa_supervisory_devices}}."
            "\n\n"
            "Occupant notification of a fire alarm condition is provided via horns and strobes "
            "installed throughout the building."
        ),
        "integrations": (
            "The fire alarm system is integrated with {{fa_integrations}}. "
            "Refer to individual systems for detailed description of the fire alarm integrations "
            "to each of these systems."
            "\n\n"
            "Additionally, the fire alarm system is integrated to a central monitoring station for "
            "remote monitoring of alarm, trouble, and supervisory conditions. "
            "The monitoring station connection is monitored for integrity."
        ),
    },

    "sprinkler": {
        "description": "",
        "integrations": "",
    },

    "standpipe": {
        "description": (
            "The building is protected by wet-pipe standpipe and hose system located throughout the building. "
            "Control valves and flow switches which supervise the standpipe system are located throughout the building, "
            "as well as the following locations:\n"
            "{{stnd_vlv_locs}}"
        ),
        "integrations": (
            "The standpipe and hose system are interconnected to the fire alarm for monitoring of water flow "
            "via flow switches and for movement of valves controlling water supplies via tamper switches."
        ),
    },

    "pre_action": {
        "description": (
            "The {{preac_protec_areas}} {{preac_area_verb}} protected by a {{preac_type}} pre-action sprinkler system. "
            "This system requires the activation of a fire alarm initiating device, and opening of a sprinkler "
            "in order to activate the sprinkler system. "
            "Control valves for the pre-action sprinkler system are located in:\n"
            "{{preac_vlv_locs}}"
        ),
        "integrations": (
            "The pre-action sprinkler system is interconnected to the {{preac_pan_or_fa}} for monitoring of "
            "water flow via flow switches, for movement of valves controlling water supply via tamper switches, "
            "monitoring of system pressure (for low pressure annunciation) via pressure switches, and supervising "
            "the pre-action sprinkler system solenoid position."
        ),
    },

    "fire_pump": {
        "description": (
            "A diesel fire pump is located within the {{fp_room}} on the {{fp_level}}. "
            "The fire pump serves the building sprinkler systems. "
            "Motorized combustion air intake louver for the diesel fire pump engine is monitored by a dedicated "
            "Combustion Air Damper Alarm Panel, which provides local \"DAMPER FAIL\" indication (red light and audible horn)."
        ),
        "integrations": (
            "The diesel fire pump is interconnected to the fire alarm system for monitoring of fire pump running, "
            "fire pump trouble, controller not in auto, pump room low temperature, and engine/over-pressure fault conditions."
            "\n\n"
            "The fire pump controller sends a pump running signal to the alarm panel, which opens the intake louver. "
            "The louver fully opens within 30 seconds, proven by auxiliary end-switch."
            "\n\n"
            "If louvers fail to prove open within 30 seconds, the alarm panel activates local \"DAMPER FAIL\" indication "
            "and sends a dry contact signal to the fire alarm system, generating a unique latching supervisory condition. "
            "The fire alarm system monitors the louver fail condition only (no control function)."
        ),
    },

    "generator": {
        "description_emergency": (
            "Emergency power for the building is provided via {{gen_count_txt}} ({{gen_count_num}}) "
            "{{gen_type}} {{generator_s}}. The {{generator_s}} {{generator_verb}} located in the "
            "{{gen_room}} on the {{gen_floor}}. The {{generator_s}} {{gen_serve_s}} the following "
            "fire and life safety systems:\n{{gen_served_list}}"
        ),
        "integrations_emergency": (
            "The emergency {{generator_s}} {{generator_verb}} interconnected to the fire alarm for "
            "monitoring of generator running and various generator fault conditions as well as "
            "monitoring the Automatic Transfer Switch (ATS) for an \"ENGAGED\" condition via "
            "monitoring output contacts on the emergency generator controller and ATS."
        ),
        "description_nonemergency": (
            "Non-emergency power for the building is provided via {{gen_count_txt}} ({{gen_count_num}}) "
            "{{gen_type}} {{generator_s}}. The {{generator_s}} {{generator_verb}} located in the "
            "{{gen_room}} on the {{gen_floor}}. The {{generator_s}} exclusively {{gen_serve_s}} "
            "Non-Fire-and-Life-Safety systems."
        ),
        "integrations_nonemergency": (
            "The non-emergency {{generator_s}} {{generator_verb}} interconnected to the fire alarm for "
            "monitoring of generator running and various generator fault conditions as well as "
            "monitoring the Automatic Transfer Switch (ATS) for an \"ENGAGED\" condition via "
            "monitoring output contacts on the non-emergency generator controller and ATS."
        ),
    },

    "maglock": {
        "description": (
            "Electromagnetic locks are provided throughout the building. "
            "These devices restrict access to secure areas via a card access system."
        ),
        "integrations": (
            "The electromagnetic locks are integrated with the fire alarm system. "
            "They are released upon activation of the fire alarm system alarm, loss of power to the "
            "fire alarm control panel, or local manual station operation."
        ),
    },

    "door_holders": {
        "description": (
            "Door holders are installed on doors throughout the building."
        ),
        "integrations": (
            "The door holders are integrated with the fire alarm system. They are released upon activation "
            "of the fire alarm system alarm signal or loss of power to the building."
        ),
    },

    "ahu": {
        "description": (
            "Air handling units are provided to supply tempered air to dedicated areas of the building "
            "via duct work ventilation system that are interconnected with the fire alarm system."
        ),
        "integrations": (
            "The air handling units are interconnected to the fire alarm for local fan shutdown on specific "
            "fire alarm signals to prevent the re-circulation of smoke in the building."
        ),
    },

    "smoke_dampers": {
        "description": (
            "Smoke dampers are provided throughout the building in the ventilation ductwork. "
            "These dampers are interconnected to the fire alarm system for closure upon smoke detection activation."
        ),
        "integrations": (
            "Smoke dampers are interconnected to the fire alarm for closure upon activation of the adjacent "
            "smoke detector to prevent smoke penetration into the occupant areas."
        ),
    },

    "fire_shutters": {
        "description": (
            "Fire shutters are located throughout the building and are interconnected to the fire alarm system. "
            "The fire shutters will release upon fire alarm activation."
        ),
        "integrations": (
            "The fire shutters are interconnected to the fire alarm for release upon activation of an adjacent "
            "fire alarm smoke detector to drop the fire shutter and prevent fire/smoke from spreading into adjacent areas."
        ),
    },

    "kitchen_hood": {
        "description": (
            "Cooking equipment fire suppression systems are installed in kitchens throughout the building. "
            "The system is equipped with a wet chemical agent that will be released when activated to suppress a cooking fire. "
            "The system is activated by a fusible link located above the cooking area, or by the manual pull release."
        ),
        "integrations": (
            "The cooking equipment fire suppression system is monitored by the fire alarm for activation of the "
            "suppression system via the suppression system control panel."
        ),
    },

    "water_mist": {
        "description": (
            "The {{watmist_protec_area}} {{watmist_area_verb}} protected by a water-mist system. "
            "This system requires the activation of a fire alarm initiating device in order to activate "
            "the water-mist system which disperses a fine mist of water over the protected area."
        ),
        "integrations": (
            "The water mist system is interconnected to the fire alarm through a pre-action releasing panel. "
            "The pre-action release panel will provide an alarm, supervisory, or trouble signal to the fire alarm system "
            "and monitors detection, system activation and water flow via alarm switches."
        ),
    },

    "elevator": {
        "description": (
            "{{elev_count_txt}} ({{elev_count_num}}) {{elevator_s}} {{elevator_verb}} provided in the building. "
            "The {{elevator_s}} will recall to the {{elev_prim_rcl}} or {{elev_alt_rcl}} "
            "upon activation of the fire alarm system."
        ),
        "integrations": (
            "The {{elevator_s}} {{elevator_verb}} interconnected to the fire alarm for emergency elevator recall control functions."
        ),
    },

}


# ---------------------------------------------------------------------------
# Sprinkler system sub-type text
# Only the opening sentence of the description changes based on selected types.
# Everything else is static and left for the user to edit.
# ---------------------------------------------------------------------------

SPRINKLER_SUBTYPE_ORDER = [
    "Wet Pipe",
    "Dry Pipe",
]

PRE_ACTION_SUBTYPE_ORDER = [
    "Pre-Action (Single Interlock)",
    "Pre-Action (Double Interlock)",
]

_SPR_STATIC_DESC = (
    "Control valves, flow switches, and low pressure switches which supervise the sprinkler "
    "system are located throughout the building, as well as the following locations:\n"
    "{{sprk_vlv_locs}}"
)

_SPR_STATIC_INT = (
    "The automatic sprinkler system is interconnected to the fire alarm for monitoring of "
    "water flow via flow switches, for movement of valves controlling water supply via "
    "supervised valves, and for monitoring of system pressure via pressure switches."
)

# Label fragments used to build the opening sentence
_SUBTYPE_LABELS = {
    "Wet Pipe":  "wet-pipe",
    "Dry Pipe":  "dry-pipe",
}


def get_sprinkler_text(active_subtypes):
    """
    Return (description, integrations) for the selected sub-types.
    Only the opening sentence of the description changes.
    """
    selected = [s for s in SPRINKLER_SUBTYPE_ORDER if s in active_subtypes]

    if not selected:
        desc = f"The building is protected by a {{{{sprk_type}}}} automatic sprinkler system.  {_SPR_STATIC_DESC}"
        return desc, _SPR_STATIC_INT

    # Build "wet-pipe and dry-pipe" style label
    labels = [_SUBTYPE_LABELS[s] for s in selected]
    if len(labels) == 1:
        type_str = labels[0]
    elif len(labels) == 2:
        type_str = f"{labels[0]} and {labels[1]}"
    else:
        type_str = ", ".join(labels[:-1]) + f", and {labels[-1]}"

    # Use {{sprk_type}} placeholder — substituted live in UI and by replace_all in Word
    opening = "The building is protected by a {{sprk_type}} automatic sprinkler system."
    desc = f"{opening}  {_SPR_STATIC_DESC}"

    return desc, _SPR_STATIC_INT


# ---------------------------------------------------------------------------
# Integrations Matrix defaults
# Each system key maps to a list of row tuples: (integration, normal_mode, fire_mode)
# Monitoring station is under fire_alarm.
# ---------------------------------------------------------------------------

MATRIX_DEFAULTS = {
    "fire_alarm_monitoring": [
        (
            "Alarm Condition",
            "No alarm on the fire alarm system, no signal at monitoring station.",
            "Alarm on the fire alarm system, alarm signal transmitted to and received by monitoring station.",
        ),
        (
            "Supervisory Condition",
            "No supervisory condition on the fire alarm system, no signal at monitoring station.",
            "Supervisory condition on the fire alarm system, supervisory signal transmitted to and received by monitoring station.",
        ),
        (
            "Trouble Condition",
            "No trouble condition on the fire alarm system, no signal at monitoring station.",
            "Trouble condition on the fire alarm system, trouble signal transmitted to and received by monitoring station.",
        ),
        (
            "Connection Integrity",
            "Signal Receiving Centre disconnect not activated, no signal at monitoring station.",
            "Signal Receiving Center disconnect activated, trouble transmission signal at monitoring station.",
        ),
    ],
    "sprinkler": [
        (
            "Water Flow",
            "No water flowing through sprinkler system, no off-normal condition on fire alarm system.",
            "Water flowing through sprinkler system activates water flow switch, unique alarm condition on fire alarm system.",
        ),
        (
            "Valve Supervision",
            "Valve in open position, no off-normal condition on fire alarm system.",
            "Valve closed (two turns of valve handle or 10% of valve stem), unique alarm condition on fire alarm system.",
        ),
        (
            "Low Pressure",
            "System pressure above minimum threshold, no off-normal condition on fire alarm system.",
            "System pressure below minimum threshold, unique supervisory condition on fire alarm system.",
        ),
    ],
    "standpipe": [
        (
            "Water Flow",
            "No water flowing through standpipe system, no off-normal condition on fire alarm system.",
            "Water flowing through standpipe system activates water flow switch, unique alarm condition on fire alarm system.",
        ),
        (
            "Valve Supervision",
            "Valve in open position, no off-normal condition on fire alarm system.",
            "Valve closed (two turns of valve handle or 10% of valve stem), unique alarm condition on fire alarm system.",
        ),
    ],
    # pre_action: Pre-Action Sprinkler tab — WF/VS/LP and Actuator integrations
    "pre_action": [
        (
            "Water Flow",
            "No water flowing through sprinkler system, no off-normal condition on fire alarm system.",
            "Water flowing through sprinkler system activates water flow switch, unique alarm condition on fire alarm system.",
        ),
        (
            "Valve Supervision",
            "Valve in open position, no off-normal condition on fire alarm system.",
            "Valve closed (two turns of valve handle or 20% of valve stem), unique supervisory condition on fire alarm system.",
        ),
        (
            "Low Pressure",
            "System pressure above minimum threshold, no off-normal condition on fire alarm system.",
            "System pressure below minimum threshold, unique supervisory condition on fire alarm system.",
        ),
        (
            "Actuator Position (Solenoid)",
            "Pre-action system solenoid in closed position, no off-normal condition on fire alarm system.",
            "Pre-action system solenoid removed/disconnected, unique supervisory condition on fire alarm system.",
        ),
        (
            "Actuator Activation (Solenoid)",
            "Pre-action system solenoid in normal state, no off-normal condition on pre-action panel.",
            "Pre-action system panel alarm activated, pre-action system solenoid in activated state (energized).",
        ),
    ],
    # pre_action_panel: Pre-Action Panel tab — Alarm/Supervisory/Trouble to fire alarm
    "pre_action_panel": [
        (
            "Alarm Condition",
            "No alarm condition on the pre-action sprinkler system panel, no off-normal condition on fire alarm system.",
            "Alarm condition on pre-action sprinkler system panel, unique alarm condition on fire alarm system.",
        ),
        (
            "Supervisory Condition",
            "No supervisory condition on the pre-action sprinkler system panel, no off-normal condition on fire alarm system.",
            "Supervisory condition on pre-action sprinkler system panel, unique supervisory condition on fire alarm system.",
        ),
        (
            "Trouble Condition",
            "No trouble condition on the pre-action sprinkler system panel, no off-normal condition on fire alarm system.",
            "Trouble condition on pre-action sprinkler system panel, unique supervisory condition on fire alarm system.",
        ),
    ],
    "fire_pump": [
        (
            "Fire Pump Running",
            "Fire pump not running, no off-normal condition on fire alarm system.",
            "Fire pump running, unique non-latching supervisory condition on fire alarm system.",
        ),
        (
            "Fire Pump Trouble",
            "Fire pump in normal operating condition, no off-normal condition on fire alarm system.",
            "Fire pump in trouble condition, unique non-latching supervisory condition on fire alarm system.",
        ),
        (
            "Fire Pump Off Auto Position",
            "Fire pump in normal auto operating condition, no off-normal condition on fire alarm system.",
            "The main switch shifted from the auto position to either OFF or manual position, unique supervisory condition on fire alarm.",
        ),
        (
            "Pump Room Low Temperature",
            "Enclosure temperature is above minimum threshold, no off-normal condition on fire alarm system.",
            "Enclosure temperature below threshold, unique supervisory condition on fire alarm system.",
        ),
        (
            "Fire Pump Controller, Engine, Over-Pressure and Room Trouble",
            "Fire pump controller, engine, over-pressure system, and pump room in normal operating condition, no off-normal condition on fire alarm system.",
            "Trouble condition on fire pump controller, engine, over-pressure, or pump room, unique supervisory condition on fire alarm system.",
        ),
        (
            "Intake Louver Operation",
            "Fire pump not running, no signal to open louvers. Louvers closed, louver alarm panel normal, no off-normal condition on fire alarm system.",
            "Fire pump running, louver opens fully within 30 s, louver alarm panel normal (no DAMPER FAIL light or horn).",
        ),
        (
            "Intake Louver Fail to Open",
            "Louvers in normal (closed) position, alarm panel normal, no off-normal condition on fire alarm system.",
            "Louvers fail to fully open within 30 seconds of pump running signal. Louver alarm panel activates red DAMPER FAIL light and audible horn, unique supervisory condition on fire alarm system.",
        ),
    ],
    "generator": [
        (
            "Generator Running",
            "Generator not running, no off-normal condition on fire alarm system.",
            "Generator running, unique alarm condition on fire alarm system.",
        ),
        (
            "ATS Engaged",
            "ATS not engaged, no off-normal condition on fire alarm system.",
            "ATS engaged, unique supervisory condition on fire alarm system.",
        ),
    ],
    "maglock": [
        (
            "Global Release",
            "No alarm condition on fire alarm system, electromagnetic locks energized.",
            "Alarm condition on fire alarm system, electromagnetic locks de-energized and doors open.",
        ),
        (
            "Local Release",
            "No alarm condition on fire alarm system, electromagnetic locks energized.",
            "Alarm condition on fire alarm system, local electromagnetic lock de-energized and door opens.",
        ),
        (
            "Secondary Release",
            "No alarm condition on fire alarm system, electromagnetic locks energized.",
            "Loss of power or fault condition, electromagnetic locks de-energized and doors open.",
        ),
    ],
    "door_holders": [
        (
            "Release",
            "No alarm condition on fire alarm system, door holders energized.",
            "Alarm condition on fire alarm system, door holders de-energized, doors close.",
        ),
    ],
    "ahu": [
        (
            "Shutdown",
            "No alarm condition on fire alarm system, air handling unit and return fan not in fire mode shutdown.",
            "Alarm condition on fire alarm system, air handling unit and return fan in fire mode shutdown. Unique alarm signal on fire alarm system.",
        ),
    ],
    "smoke_dampers": [
        (
            "Smoke Damper Relay",
            "No alarm condition on fire alarm system and local smoke detector, fire dampers held open.",
            "Alarm condition on fire alarm, or local smoke detector detects smoke, fire damper will release and close shut.",
        ),
    ],
    "fire_shutters": [
        (
            "Fire Shutter Release",
            "No alarm condition on fire alarm system, fire shutters in open position.",
            "Alarm condition on fire alarm system, fire shutters released and closed.",
        ),
    ],
    "kitchen_hood": [
        (
            "Activate",
            "No alarm condition on fire alarm system, suppression system not activated.",
            "Alarm condition on fire alarm system, suppression system activated.",
        ),
    ],
    "water_mist": [
        (
            "System Flow",
            "No water flowing through the water mist system, no off-normal condition on fire alarm system.",
            "Water flowing through the water mist system activates flow switch, unique alarm condition on fire alarm system.",
        ),
    ],
    "elevator": [
        (
            "Elevator Primary Recall",
            "No alarm condition on fire alarm system, elevators not in fire mode recall.",
            "Alarm condition on fire alarm system. Relay activated for primary recall fire alarm condition.",
        ),
        (
            "Elevator Alternate Recall",
            "No alarm condition on fire alarm system, elevators not in fire mode recall.",
            "Alarm condition on fire alarm system on floor of primary recall. Relay activated for alternate recall fire alarm condition.",
        ),
        (
            "Elevator Firefighter Warning Recall",
            "No alarm condition on fire alarm system, elevators not in fire mode recall.",
            "Alarm condition on fire alarm system in elevator shaft or machine room. Relay activated for firefighter warning recall condition.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Test Procedure defaults
# Each key maps to a list of row tuples matching MATRIX_DEFAULTS order:
# (normal_mode_bullets, fire_mode_bullets)
# Bullets are separated by \n for display; app shows with - prefix
# ---------------------------------------------------------------------------

TP_DEFAULTS = {
    "fire_alarm_monitoring": [
        (
            "- Review signal transmitting unit installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause an alarm condition on the fire alarm system.\n- Via telephone or receipt of date/time stamped report, confirm receipt of the alarm condition signal by the monitoring station.\n- Return fire alarm system to normal condition.",
        ),
        (
            "- Review signal transmitting unit installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause a supervisory condition on the fire alarm system.\n- Via telephone or receipt of date/time stamped report, confirm receipt of the supervisory condition signal by the monitoring station.\n- Return fire alarm system to normal condition.",
        ),
        (
            "- Review signal transmitting unit installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause a trouble condition on the fire alarm system.\n- Via telephone or receipt of date/time stamped report, confirm receipt of the trouble condition signal by the monitoring station.\n- Return fire alarm system to normal condition.",
        ),
        (
            "- Review signal transmitting unit installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Disconnect the alarm signal connection circuit between the fire alarm control panel and the signal transmitting unit.\n- Via telephone or receipt of date/time stamped report, confirm receipt of the trouble condition signal by the monitoring station.\n- Return alarm signal connection circuit between the fire alarm control panel and the signal transmitting unit to normal condition.",
        ),
    ],
    "sprinkler": [
        (
            "- Review flow switch installation.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Flow water from the Inspectors Test Connection of the sprinkler system associated with the flow switch being tested.\n- Record time between operation of Inspectors Test Connection and activation of alarm signal at the fire alarm system. Time to be 90 seconds or less.\n- Close Inspectors Test Connection upon activation of fire alarm system.\n- Confirm correct fire alarm system annunciation.\n- Return sprinkler system and fire alarm system to normal condition.",
        ),
        (
            "- Review valve and valve supervision installation.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Operate the valve being tested by operating the handle two full turns for butterfly style valves or closing at least 10% of the valve stem for OS&Y style valves.\n- Confirm correct fire alarm system annunciation.\n- Return valve and fire alarm system to normal condition.",
        ),
        (
            "- Review pressure switch installation.\n- Confirm fire alarm system is reset and clear of any off-normal conditions.",
            "- Operate the pressure switch being tested by reducing the pressure of the sprinkler system via operation of drain valve to below the pre-determined pressure threshold.\n- Confirm correct fire alarm system annunciation.\n- Return system to adequate pressure and fire alarm system to normal condition.",
        ),
    ],
    "standpipe": [
        (
            "- Review flow switch installation.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Flow water from the standpipe system associated with the flow switch being tested.\n- Confirm correct fire alarm system annunciation.\n- Return standpipe system and fire alarm system to normal condition.",
        ),
        (
            "- Review valve and valve supervision installation.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Operate the valve being tested by operating the handle two full turns for butterfly style valves or closing at least 10% of the valve stem for OS&Y style valves.\n- Confirm correct fire alarm system annunciation.\n- Return valve and fire alarm system to normal condition.",
        ),
    ],
    "pre_action": [
        (
            "- Review flow switch installation.\n- Confirm pre-action system panel reset and clear of any off-normal conditions.",
            "- Flow water for the pre-action sprinkler system via opening test valve.\n- Close test valve upon activation of pre-action system panel alarm condition.\n- Confirm correct pre-action system panel annunciation.\n- Return pre-action sprinkler system and pre-action sprinkler system panel to normal condition.",
        ),
        (
            "- Review valve and valve supervision installation.\n- Confirm pre-action system panel reset and clear of any off-normal conditions.",
            "- Operate the valve being tested by operating the handle two full turns for butterfly style valves or closing at least 20% of the valve stem for OS&Y style valves.\n- Confirm correct pre-action system panel annunciation.\n- Return valve and pre-action system panel to normal condition.",
        ),
        (
            "- Review pressure switch installation.\n- Confirm pre-action system panel is reset and clear of any off-normal conditions.",
            "- Operate the pressure switch being tested by reducing the pressure of the pre-action sprinkler system via operation of drain valve to below the pre-determined pressure threshold.\n- Confirm correct pre-action system panel annunciation.\n- Return pre-action system to adequate pressure and pre-action system panel to normal condition.",
        ),
        (
            "- Review installation of electric actuator (solenoid) and connection to pre-action system panel.\n- Confirm electric actuator is in proper position.\n- Confirm pre-action system panel is reset and clear of any off-normal conditions.",
            "- Remove/disconnect the electric actuator.\n- Confirm correct pre-action system panel annunciation.\n- Return electric actuator and pre-action system panel to normal condition.",
        ),
        (
            "- Review installation of electric actuator (solenoid) and connection to pre-action system panel.\n- Confirm pre-action system panel is reset and clear of any off-normal conditions.",
            "- Pre-action system panel alarm activated, pre-action system solenoid in activated state (energized).\n- Confirm correct pre-action system panel annunciation.\n- Return pre-action system panel to normal condition.",
        ),
    ],
    "pre_action_panel": [
        (
            "- Review pre-action system panel installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause an alarm condition on the pre-action sprinkler system.\n- Confirm correct fire alarm system annunciation.\n- Return pre-action system panel and fire alarm system to normal condition.",
        ),
        (
            "- Review pre-action system panel installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause a supervisory condition on the pre-action sprinkler system.\n- Confirm correct fire alarm system annunciation.\n- Return pre-action system panel and fire alarm system to normal condition.",
        ),
        (
            "- Review pre-action system panel installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause a trouble condition on the pre-action sprinkler system.\n- Confirm correct fire alarm system annunciation.\n- Return pre-action system panel and fire alarm system to normal condition.",
        ),
    ],
    "fire_pump": [
        (
            "- Review fire pump installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Start the fire pump for non-flow condition.\n- Confirm correct fire alarm system annunciation.\n- Return fire pump and fire alarm system to normal condition.",
        ),
        (
            "- Review fire pump installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Create trouble condition on fire pump.\n- Confirm correct fire alarm system annunciation.\n- Return fire pump and fire alarm system to normal condition.",
        ),
        (
            "- Review fire pump installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Turn fire pump controller main switch to OFF or HAND (manual) position.\n- Confirm correct fire alarm system annunciation.\n- Return fire pump and fire alarm system to normal condition.",
        ),
        (
            "- Review temperature monitor installation.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Simulate temperature of 4°C.\n- Confirm correct fire alarm system annunciation.\n- Return fire pump and fire alarm system to normal condition.",
        ),
        (
            "- Review fire pump installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Create a trouble condition on the fire pump controller, engine, over-pressure system, or pump room.\n- Confirm correct fire alarm system annunciation.\n- Return fire pump and fire alarm system to normal condition.",
        ),
        (
            "- Review intake louver installation and connection to the combustion air damper alarm panel and fire alarm system.\n- Confirm fire pump not running.\n- Confirm louvers in closed position, louver alarm panel normal, and no off-normal condition on fire alarm system.",
            "- Start fire pump for non-flow condition.\n- Confirm louvers fully open within 30 seconds.\n- Confirm louver alarm panel remains normal (no red DAMPER FAIL light or audible horn).\n- Confirm no \"Louver Failed to Open\" supervisory condition on fire alarm system.\n- Return fire pump and fire alarm system to normal condition.",
        ),
        (
            "- Review intake louver installation and connection to the louver alarm panel and fire alarm system.\n- Confirm fire pump not running.\n- Confirm louvers in closed position, louver alarm panel normal, and no off-normal condition on fire alarm system.",
            "- Start fire pump for non-flow condition.\n- Simulate louver failure to prove fully open (e.g., prevent/delay end-switch closure beyond 30 seconds or use panel TEST pushbutton if applicable).\n- Confirm louver alarm panel activates red DAMPER FAIL light and audible horn within timing period.\n- Confirm unique supervisory condition on fire alarm system.\n- Return fire pump and fire alarm system to normal condition.",
        ),
    ],
    "generator": [
        (
            "- Review generator installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Start the emergency generator.\n- Confirm correct fire alarm system annunciation.\n- Return generator and fire alarm system to normal condition.",
        ),
        (
            "- Review ATS installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Engage the ATS.\n- Confirm correct fire alarm system annunciation.\n- Return ATS and fire alarm system to normal condition.",
        ),
    ],
    "maglock": [
        (
            "- Review installation of fire alarm relay connection to Maglocks.\n- Confirm fire alarm system reset and clear of an off-normal conditions.\n- Confirm Maglocks operating normally.",
            "- Activate a fire detector (not a manual station adjacent a door equipped with a maglock).\n- Confirm correct fire alarm annunciation.\n- Confirm all maglocks de-energizes.\n- Return maglocks and fire alarm system to normal condition.",
        ),
        (
            "- Review installation of local manual station with auxiliary connection to local maglock.\n- Confirm fire alarm system reset and clear of an off-normal conditions.\n- Confirm maglock operating normally.",
            "- Disable global maglock relay on fire alarm system.\n- Activate local manual station adjacent the door equipped with a maglock.\n- Confirm correct fire alarm annunciation.\n- Confirm local maglock de-energizes.\n- Return maglock and fire alarm system to normal condition.",
        ),
        (
            "- Review installation of fire alarm interconnection to maglocks.\n- Confirm fire alarm system reset and clear of an off-normal conditions.\n- Confirm Maglocks operating normally.",
            "- Confirm all maglocks release upon each the following.\n- Loss of power to fire alarm control panel or maglock controller.\n- Operation of maglock release adjacent to the main fire alarm annunciator.\n- Fault detected on the circuit between the fire alarm panel and maglock controller.\n- Confirm correct fire alarm system annunciation.\n- Return maglocks and fire alarm system to normal condition.",
        ),
    ],
    "door_holders": [
        (
            "- Review door holder installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause an alarm condition on the fire alarm system.\n- Confirm door holders de-energize and doors close.\n- Return fire alarm system to normal condition and confirm door holders re-energize.",
        ),
    ],
    "ahu": [
        (
            "- Review air handling unit installation and connection to fire alarm system.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Cause an alarm condition on the fire alarm system.\n- Confirm air handling unit shuts down.\n- Return fire alarm system to normal condition and confirm air handling unit returns to normal operation.",
        ),
    ],
    "smoke_dampers": [
        (
            "- Review installation of fire alarm relay connection to smoke dampers.\n- Confirm fire alarm system reset and clear of any off-normal conditions.\n- Confirm smoke damper is latched in an open position.",
            "- Activate local smoke detector.\n- Confirm correct fire alarm system annunciation.\n- Confirm fire/smoke damper shuts closed.\n- Return fire/smoke damper, and reset fire alarm system to normal condition.",
        ),
    ],
    "fire_shutters": [
        (
            "- Review installation of fire alarm relay connection to local smoke detector.\n- Confirm fire alarm reset and clear of any off-normal conditions.\n- Confirm fire shutter operating normally.",
            "- Activate local smoke detector.\n- Confirm fire shutter closes.\n- Confirm correct fire alarm system annunciation.\n- Return fire shutter and fire alarm system to normal condition.",
        ),
    ],
    "kitchen_hood": [
        (
            "- Review cooking equipment suppression system installation and connection to the fire alarm.\n- Confirm fire alarm system reset and clear of any off-normal conditions.",
            "- Remove suppression system's gas cartridge.\n- Simulate fire condition to activate suppression system (e.g. activate manual dump station).\n- Confirm shutdown of gas/fuel to kitchen equipment (where applicable).\n- Confirm fire alarm system annunciation.\n- Return suppression system back to normal condition.",
        ),
    ],
    "water_mist": [
        (
            "- Review water-mist system installation.\n- Confirm fire alarm system is reset and clear of any off-normal conditions.",
            "- Remove water-mist system solenoid to ensure system discharge in secured area does not occur.\n- Activate initiating devices from the water-mist system.\n- Confirm solenoid activates.\n- Confirm correct fire alarm system annunciation.\n- Return water-mist system and fire alarm system to normal condition.",
        ),
    ],
    "elevator": [
        (
            "- Review installation of fire alarm elevator relay connection to elevator system.\n- Confirm fire alarm reset and clear of any off-normal conditions.\n- Confirm elevators on a floor other than the primary recall level (ground floor).",
            "- Activate a fire detector located on a floor other than the ground floor.\n- Confirm correct fire alarm annunciation.\n- Confirm elevators recall to the ground floor and remain at the elevator lobby.\n- Confirm in-car buttons do not operate in each elevator car.\n- Confirm the in-car recall light is illuminated steady in each elevator car.\n- Return elevator system and fire alarm system to normal condition.",
        ),
        (
            "- Review installation of fire alarm elevator relay connection to elevator system.\n- Confirm fire alarm reset and clear of any off-normal conditions.\n- Confirm elevators are in operating condition.",
            "- Activate a fire detector located at elevator lobby of recall level.\n- Confirm correct fire alarm annunciation.\n- Confirm elevators recall to the alternate floor and remains at the elevator lobby.\n- Confirm in-car buttons do not operate in each elevator car.\n- Confirm in-car buttons do not operate in designated firefighter elevator car.\n- Return elevator system and fire alarm system to normal condition.",
        ),
        (
            "- Review installation of fire alarm elevator relay connection to elevator system.\n- Confirm fire alarm reset and clear of any off-normal conditions.\n- Confirm elevators on a floor other than the primary recall level (ground floor).",
            "- Activate a fire detector located within the elevator shaft and/or elevator machine room.\n- Confirm correct fire alarm system annunciation.\n- Confirm elevators recall to the ground floor and remain.\n- Confirm in-car buttons do not operate in each elevator car.\n- Confirm the in-car recall light is intermittently illuminated (flashing) in each elevator car.\n- Activate emergency firefighter elevator override.\n- Confirm in-car buttons do not operate in designated firefighter elevator.\n- Return elevator system and fire alarm system to normal condition.",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Appendix B defaults
# APPB_DEFAULTS: pre-seeded integration row names per system
# APPB_DESC_DEFAULTS: (normal_mode_description, fire_mode_description) per system
# ---------------------------------------------------------------------------

APPB_DEFAULTS = {
    "fire_alarm": [
        "Alarm Condition",
        "Supervisory Condition",
        "Trouble Condition",
        "Connection Integrity",
    ],
    "sprinkler": [
        "Water Flow",
        "Valve Supervision",
        "Low Pressure",
    ],
    "standpipe": [
        "Water Flow",
        "Valve Supervision",
    ],
    "pre_action": [
        "Water Flow",
        "Valve Supervision",
        "Low Pressure",
        "Actuator Position (Solenoid)",
        "Actuator Activation (Solenoid)",
    ],
    "pre_action_panel": [
        "Alarm Condition",
        "Supervisory Condition",
        "Trouble Condition",
    ],
    "fire_pump": [
        "Fire Pump Running",
        "Fire Pump Trouble",
        "Fire Pump Off Auto Position",
        "Pump Room Low Temperature",
        "Fire Pump Controller, Engine, Over-Pressure and Room Trouble",
        "Intake Louver Operation",
        "Intake Louver Fail to Open",
    ],
    "generator": [
        "Generator Running",
        "ATS Engaged",
    ],
    "maglock": [
        "Global Release",
        "Local Release",
        "Secondary Release",
    ],
    "door_holders": [
        "Release",
    ],
    "ahu": [
        "Shutdown",
    ],
    "smoke_dampers": [
        "Smoke Damper Relay",
    ],
    "fire_shutters": [
        "Fire Shutter Release",
    ],
    "kitchen_hood": [
        "Kitchen Hood",
    ],
    "water_mist": [
        "System Flow",
    ],
    "elevator": [
        "Elevator Primary Recall",
        "Elevator Alternate Recall",
        "Elevator Firefighter Warning Recall",
    ],
}

APPB_DESC_DEFAULTS = {
    "fire_alarm": (
        "Review monitoring system installation and confirm correct fire alarm system status.",
        "Cause associated condition on fire alarm system and confirm correct receipt of signal at monitoring station.",
    ),
    "sprinkler": (
        "Review device installation and confirm correct fire alarm system status.",
        "Open valve (two turns or 10% of valve stem) or test flow switch (flow water) and confirm correct operation and fire alarm annunciation.",
    ),
    "standpipe": (
        "Review device installation and confirm correct fire alarm system status.",
        "Open valve (two turns or 10% of valve stem) or test flow switch (flow water) and confirm correct operation and fire alarm annunciation.",
    ),
    "pre_action_panel": (
        "Review device installation and confirm correct fire alarm system status.",
        "Flow water, confirm correct operation and fire alarm annunciation.",
    ),
    "pre_action": (
        "Review device installation and confirm correct fire alarm system status.",
        "Open valve (two turns or 10% of valve stem) or test flow switch (flow water) and confirm correct operation and fire alarm annunciation.",
    ),
    "fire_pump": (
        "Review fire pump installation and confirm correct fire alarm system status.",
        "Operate device (run fire pump, simulate failure, and close diesel fuel supply) and confirm operation and fire alarm annunciation.",
    ),
    "generator": (
        "Review generator installation and confirm correct fire alarm system status.",
        "Operate device (run generator, simulate failure, and close {{gen_fuel}} supply) and confirm operation and fire alarm annunciation.",
    ),
    "generator_served": (
        "Review generator installation and power feeds.",
        "Run devices, simulate power failure, confirm generator starts within 15 seconds and confirm device operation.",
    ),
    "maglock": (
        "Review device installation and confirm correct fire alarm system status.",
        "Initiate an alarm condition on fire alarm, door holders in fire mode, ensure locks de-energize and door opens.",
    ),
    "door_holders": (
        "No alarm condition on fire alarm system, door holders energized.",
        "Alarm condition on fire alarm system, door holders de-energized, doors close.",
    ),
    "ahu": (
        "No alarm condition on fire alarm system, review air handling unit installation and running.",
        "Alarm condition on fire alarm system, confirm air handling unit in fire mode shutdown.",
    ),
    "smoke_dampers": (
        "Review device installation and confirm correct fire alarm system status.",
        "Activate a fire alarm, ensure smoke damper operates and fully closes.",
    ),
    "fire_shutters": (
        "Review device installation and confirm correct fire alarm system status.",
        "Initiate an alarm condition on fire alarm, ensure fire shutters initiate and fully close.",
    ),
    "kitchen_hood": (
        "Review kitchen hood suppression system installation and confirm normal status on fire alarm system.",
        "Simulate system activation and confirm signals received on fire alarm system.",
    ),
    "water_mist": (
        "Review device installation and confirm correct fire alarm system status.",
        "Flow water, confirm correct operation and fire alarm annunciation.",
    ),
    "elevator": (
        "Review elevator installation and confirm correct fire alarm system status. Confirm elevators not at recall level.",
        "Activate fire detector and confirm correct elevator operation.",
    ),
    # Section 3.6 — Emergency Generator Power Integrations
    "generator_conns_diesel": (
        "Review generator installation and power feeds.",
        "Run devices, simulate power failure, confirm generator starts within 15 seconds and confirm device operation.",
    ),
    "generator_conns_natural_gas": (
        "Review generator installation and power feeds.",
        "Run devices, simulate power failure, confirm generator starts within 15 seconds and confirm device operation.",
    ),
}

# ---------------------------------------------------------------------------
# Generator Served Systems defaults
# Text for each served system integration in the Generator Served Systems tab.
# {system} is replaced with the served system name (e.g. "Door Holders").
# ---------------------------------------------------------------------------

GEN_SERVED_NORMAL  = "Emergency generator in normal mode, {{connected_system}} supplied through primary (normal) power."
GEN_SERVED_GENMODE = "Generator running, {{connected_system}} operating on emergency generator power."
GEN_SERVED_TP_NORMAL  = "- Confirm {{connected_system}} operates on normal power."
GEN_SERVED_TP_GENMODE = "- Confirm {{connected_system}} operates on emergency generator power."