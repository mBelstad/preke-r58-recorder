"""Template definitions for broadcast graphics."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class GraphicsTemplate:
    """Graphics template definition."""
    id: str
    name: str
    type: str  # "lower_third", "stinger", "ticker", "timer", etc.
    description: str
    default_config: Dict[str, Any]
    preview_image: str = ""  # Path to preview image (optional)


# Lower-Third Templates
LOWER_THIRD_TEMPLATES: List[GraphicsTemplate] = [
    GraphicsTemplate(
        id="lower_third_standard",
        name="Standard Lower-Third",
        type="lower_third",
        description="Classic two-line lower-third with background",
        default_config={
            "line1": "Name",
            "line2": "Title/Role",
            "position": "bottom-left",
            "background_color": "#000000",
            "background_alpha": 0.8,
            "text_color": "#FFFFFF",
            "line1_font": "Sans Bold 32",
            "line2_font": "Sans 24",
            "padding": {"x": 20, "y": 15},
            "width": 600,
            "height": 120,
        }
    ),
    GraphicsTemplate(
        id="lower_third_modern",
        name="Modern Lower-Third",
        type="lower_third",
        description="Modern design with accent bar",
        default_config={
            "line1": "Name",
            "line2": "Title/Role",
            "position": "bottom-left",
            "background_color": "#1a1a1a",
            "background_alpha": 0.9,
            "accent_color": "#3b82f6",
            "accent_width": 4,
            "text_color": "#FFFFFF",
            "line1_font": "Sans Bold 30",
            "line2_font": "Sans 22",
            "padding": {"x": 24, "y": 18},
            "width": 650,
            "height": 130,
        }
    ),
    GraphicsTemplate(
        id="lower_third_minimal",
        name="Minimal Lower-Third",
        type="lower_third",
        description="Clean minimal design",
        default_config={
            "line1": "Name",
            "line2": "Title/Role",
            "position": "bottom-left",
            "background_color": "#000000",
            "background_alpha": 0.7,
            "text_color": "#FFFFFF",
            "line1_font": "Sans Bold 28",
            "line2_font": "Sans 20",
            "padding": {"x": 16, "y": 12},
            "width": 550,
            "height": 100,
        }
    ),
    GraphicsTemplate(
        id="lower_third_centered",
        name="Centered Lower-Third",
        type="lower_third",
        description="Centered lower-third with rounded background",
        default_config={
            "line1": "Name",
            "line2": "Title/Role",
            "position": "bottom-center",
            "background_color": "#000000",
            "background_alpha": 0.85,
            "text_color": "#FFFFFF",
            "line1_font": "Sans Bold 32",
            "line2_font": "Sans 24",
            "padding": {"x": 30, "y": 20},
            "width": 700,
            "height": 140,
            "border_radius": 8,
        }
    ),
]

# Position presets
POSITION_PRESETS = {
    "bottom-left": {"x": 100, "y": 900, "anchor": "left"},
    "bottom-center": {"x": 960, "y": 900, "anchor": "center"},
    "bottom-right": {"x": 1820, "y": 900, "anchor": "right"},
    "top-left": {"x": 100, "y": 100, "anchor": "left"},
    "top-center": {"x": 960, "y": 100, "anchor": "center"},
    "top-right": {"x": 1820, "y": 100, "anchor": "right"},
}

# Animation presets
ANIMATION_PRESETS = {
    "slide_in_left": {
        "type": "slide",
        "direction": "left",
        "duration": 0.5,
    },
    "slide_in_right": {
        "type": "slide",
        "direction": "right",
        "duration": 0.5,
    },
    "slide_in_bottom": {
        "type": "slide",
        "direction": "bottom",
        "duration": 0.5,
    },
    "fade_in": {
        "type": "fade",
        "duration": 0.3,
    },
    "scale_in": {
        "type": "scale",
        "duration": 0.4,
    },
}


def get_template(template_id: str) -> Optional[GraphicsTemplate]:
    """Get a template by ID."""
    for template in LOWER_THIRD_TEMPLATES:
        if template.id == template_id:
            return template
    return None


def list_templates(template_type: Optional[str] = None) -> List[GraphicsTemplate]:
    """List all templates, optionally filtered by type."""
    if template_type:
        return [t for t in LOWER_THIRD_TEMPLATES if t.type == template_type]
    return LOWER_THIRD_TEMPLATES.copy()


def get_position_config(position: str, width: int, height: int, output_width: int = 1920, output_height: int = 1080) -> Dict[str, int]:
    """Get position configuration for a given position preset."""
    if position not in POSITION_PRESETS:
        position = "bottom-left"  # Default
    
    preset = POSITION_PRESETS[position]
    x = preset["x"]
    y = preset["y"]
    anchor = preset["anchor"]
    
    # Adjust based on anchor point
    if anchor == "center":
        x = x - (width // 2)
    elif anchor == "right":
        x = x - width
    
    # Ensure within bounds
    x = max(0, min(x, output_width - width))
    y = max(0, min(y, output_height - height))
    
    return {"x": x, "y": y, "anchor": anchor}

