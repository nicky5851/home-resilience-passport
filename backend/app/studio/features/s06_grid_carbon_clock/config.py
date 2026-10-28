"""Constants for the Grid Carbon Clock (docs/studio/N_20_function.md §S06)."""

CARBON_INTENSITY_BASE = "https://api.carbonintensity.org.uk"
FORECAST_CACHE_MINUTES = 15
MIX_FUELS = ["wind", "solar", "nuclear", "gas", "imports", "biomass", "hydro", "coal", "other"]

# {appliance_id: (label, kwh, duration_half_hour_slots)}
APPLIANCES: dict[str, tuple[str, float, int]] = {
    "washing_machine": ("Washing machine", 1.0, 4),
    "dishwasher": ("Dishwasher", 1.2, 4),
    "tumble_dryer": ("Tumble dryer", 2.5, 3),
    "ev_charge": ("EV charge", 28.0, 8),
    "immersion": ("Immersion heater", 3.0, 2),
    "heat_pump_preheat": ("Heat pump pre-heat", 3.0, 4),
}
