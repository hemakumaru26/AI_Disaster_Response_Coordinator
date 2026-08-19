"""Reusable Folium map generation for shelter allocation recommendations."""

from html import escape
from math import isfinite

import folium


def _valid_coordinate(latitude, longitude):
    """Return normalized coordinates when both values are geographically valid."""
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None

    if not (isfinite(latitude) and isfinite(longitude)):
        return None
    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
        return latitude, longitude
    return None


def _popup_content(shelter):
    """Build an HTML popup from the shelter fields returned by the agent."""
    field_labels = (
        ("name", "Name"),
        ("district", "District"),
        ("address", "Address"),
        ("capacity", "Total Capacity"),
        ("occupancy", "Current Occupancy"),
        ("available_capacity", "Available Capacity"),
        ("distance_km", "Distance (km)"),
        ("suitability_score", "Suitability Score"),
        ("contact", "Contact"),
    )
    lines = ["<strong>Shelter recommendation</strong>"]
    for key, label in field_labels:
        value = shelter.get(key)
        if value is not None:
            lines.append(f"<b>{label}:</b> {escape(str(value))}")
    return "<br>".join(lines)


def create_shelter_allocation_map(incident_coordinates, shelters):
    """Create an OpenStreetMap allocation map, or return ``None`` if invalid.

    ``incident_coordinates`` must contain ``latitude`` and ``longitude``.
    Invalid shelter coordinates are skipped so a partial dataset cannot prevent
    the incident marker or valid recommendations from being displayed.
    """
    if not isinstance(incident_coordinates, dict):
        return None

    incident_point = _valid_coordinate(
        incident_coordinates.get("latitude"),
        incident_coordinates.get("longitude"),
    )
    if incident_point is None:
        return None

    allocation_map = folium.Map(
        location=incident_point,
        zoom_start=12,
        tiles="OpenStreetMap",
    )
    folium.Marker(
        location=incident_point,
        tooltip="Incident location",
        popup=folium.Popup("<strong>Incident location</strong>", max_width=300),
        icon=folium.Icon(color="red", icon="exclamation-sign"),
    ).add_to(allocation_map)

    for shelter in shelters or []:
        if not isinstance(shelter, dict):
            continue
        shelter_point = _valid_coordinate(
            shelter.get("latitude"), shelter.get("longitude")
        )
        if shelter_point is None:
            continue

        folium.Marker(
            location=shelter_point,
            tooltip=escape(str(shelter.get("name", "Shelter"))),
            popup=folium.Popup(_popup_content(shelter), max_width=350),
            icon=folium.Icon(color="green", icon="home"),
        ).add_to(allocation_map)

    return allocation_map
