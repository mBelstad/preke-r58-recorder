# Broadcast Graphics Documentation

## Overview

The R58 Recorder & Mixer includes professional broadcast graphics capabilities for creating lower-thirds, stingers, tickers, timers, and other overlay elements. The system uses GStreamer-native rendering for performance, with HTML/CSS support for complex animations.

## Architecture

### Graphics Rendering

The graphics system consists of two main components:

1. **GStreamer Graphics Renderer** (`src/mixer/graphics.py`)
   - Native GStreamer pipeline generation
   - High performance, low latency
   - Supports: lower-thirds, basic timers, tickers, stingers

2. **HTML/CSS Graphics Renderer** (`src/mixer/html_graphics.py`)
   - Complex graphics with animations
   - Template-based system
   - Supports: advanced stingers, animated tickers, countdown timers

### Template System

Graphics templates are defined in `src/mixer/graphics_templates.py` and provide:
- Pre-configured layouts
- Style presets
- Position presets
- Animation presets

## Lower-Thirds

Lower-thirds are name tags and titles that appear at the bottom of the screen, commonly used in broadcast to identify speakers or provide context.

### Features

- **Two-line text support**: Primary line (name) and secondary line (title/role)
- **Customizable styling**: Fonts, colors, sizes
- **Background with transparency**: Semi-transparent backgrounds
- **Position control**: Bottom-left, bottom-center, bottom-right, top positions
- **Template system**: Pre-built templates for quick creation

### API Usage

#### Create a Lower-Third

```bash
POST /api/graphics/lower_third
Content-Type: application/json

{
  "source_id": "speaker1",
  "line1": "John Doe",
  "line2": "CEO, Acme Corporation",
  "position": "bottom-left",
  "background_color": "#000000",
  "background_alpha": 0.8,
  "text_color": "#FFFFFF",
  "line1_font": "Sans Bold 32",
  "line2_font": "Sans 24",
  "width": 600,
  "height": 120,
  "padding": {"x": 20, "y": 15}
}
```

#### Using a Template

```bash
POST /api/graphics/template/lower_third_standard
Content-Type: application/json

{
  "source_id": "speaker1",
  "line1": "Jane Smith",
  "line2": "Director of Engineering"
}
```

### Available Templates

1. **lower_third_standard** - Classic two-line lower-third with background
2. **lower_third_modern** - Modern design with accent bar
3. **lower_third_minimal** - Clean minimal design
4. **lower_third_centered** - Centered lower-third with rounded background

### Position Presets

- `bottom-left` - Bottom left corner (default)
- `bottom-center` - Bottom center
- `bottom-right` - Bottom right corner
- `top-left` - Top left corner
- `top-center` - Top center
- `top-right` - Top right corner

## Stingers

Stingers are transition graphics used between scenes, typically featuring logos, animations, or branding elements.

### Features

- Transition animations (wipe, fade, slide)
- Logo integration
- Customizable backgrounds
- Text overlays

### API Usage

```bash
POST /api/graphics/graphics
Content-Type: application/json

{
  "source_id": "transition1",
  "type": "stinger",
  "stinger_type": "fade",
  "duration": 1.0,
  "text": "BREAK",
  "background_color": "#1a1a1a",
  "text_color": "#FFFFFF"
}
```

**Note**: Advanced animations require HTML/CSS rendering (Phase 2 implementation).

## Tickers

Tickers are scrolling text overlays, commonly used for news headlines, social media feeds, or breaking news.

### Features

- Horizontal scrolling text
- Top or bottom positioning
- Customizable colors and fonts
- Background with transparency

### API Usage

```bash
POST /api/graphics/graphics
Content-Type: application/json

{
  "source_id": "news_ticker",
  "type": "ticker",
  "text": "Breaking: Important news update...",
  "position": "bottom",
  "background_color": "#000000",
  "background_alpha": 0.8,
  "text_color": "#FFFFFF",
  "font": "Sans 20"
}
```

**Note**: Scrolling animation requires HTML/CSS rendering (Phase 2 implementation). Current implementation creates static ticker bars.

## Timers

Timers display time information, including clocks, countdown timers, and stopwatches.

### Features

- **Clock**: Real-time clock display
- **Countdown**: Countdown timer (requires HTML/CSS)
- **Stopwatch**: Elapsed time display (requires HTML/CSS)

### API Usage

#### Clock

```bash
POST /api/graphics/graphics
Content-Type: application/json

{
  "source_id": "clock1",
  "type": "timer",
  "timer_type": "clock",
  "position": "top-right",
  "text_color": "#FFFFFF",
  "font": "Sans 24"
}
```

#### Countdown (Future)

```bash
POST /api/graphics/graphics
Content-Type: application/json

{
  "source_id": "countdown1",
  "type": "timer",
  "timer_type": "countdown",
  "duration": 300,
  "format": "MM:SS",
  "position": "center",
  "text_color": "#FF0000",
  "font": "Sans Bold 72"
}
```

## Graphics Templates

### Template System

Templates provide pre-configured graphics layouts that can be customized with data.

### List Templates

```bash
GET /api/graphics/templates
```

Response:
```json
{
  "templates": [
    {
      "id": "lower_third_standard",
      "name": "Standard Lower-Third",
      "type": "lower_third",
      "description": "Classic two-line lower-third with background",
      "default_config": { ... }
    }
  ]
}
```

### Get Template

```bash
GET /api/graphics/templates/{template_id}
```

### Apply Template

```bash
POST /api/graphics/template/{template_id}
Content-Type: application/json

{
  "source_id": "my_lower_third",
  "line1": "Custom Name",
  "line2": "Custom Title"
}
```

## Graphics Management

### Get Graphics Source

```bash
GET /api/graphics/{source_id}
```

### Delete Graphics Source

```bash
DELETE /api/graphics/{source_id}
```

## Using Graphics in Mixer Scenes

Graphics sources can be added to mixer scenes as overlay sources. In a scene definition:

```json
{
  "id": "scene_with_lower_third",
  "label": "Scene with Lower-Third",
  "resolution": {"width": 1920, "height": 1080},
  "slots": [
    {
      "source": "cam0",
      "source_type": "camera",
      "x": 0.0,
      "y": 0.0,
      "w": 1.0,
      "h": 1.0
    },
    {
      "source": "lower_third:speaker1",
      "source_type": "lower_third",
      "x": 0.0,
      "y": 0.0,
      "w": 1.0,
      "h": 1.0
    }
  ]
}
```

## GStreamer Pipeline Details

### Lower-Third Pipeline

Lower-thirds are rendered using:
- `videotestsrc` - Background color source
- `textoverlay` - Text rendering
- `videobox` - Positioning on full frame
- `videoconvert` - Format conversion

Example pipeline:
```
videotestsrc pattern=solid-color foreground-color=0x000000 ! 
video/x-raw,width=600,height=120,framerate=30/1 ! 
textoverlay text="John Doe\nCEO" valign=top halign=left 
xpad=20 ypad=15 font-desc="Sans Bold 32" color=0xFFFFFFFF ! 
videobox border-alpha=0 left=100 top=900 ! 
video/x-raw,width=1920,height=1080 ! 
videoconvert ! 
video/x-raw,format=NV12
```

### Timer Pipeline (Clock)

Clocks use GStreamer's `timeoverlay`:
```
videotestsrc pattern=solid-color ! 
video/x-raw,width=1920,height=1080,framerate=30/1 ! 
timeoverlay halign=right valign=top xpad=50 ypad=50 
font-desc="Sans 24" color=0xFFFFFFFFFFFFFF ! 
videoconvert ! 
video/x-raw,format=NV12
```

## Color Format

Colors are specified in hex format (`#RRGGBB`) and converted to GStreamer format (`0xAARRGGBB`):
- `#000000` → `0xFF000000` (black, fully opaque)
- `#FFFFFF` → `0xFFFFFFFF` (white, fully opaque)
- With alpha: `#000000` at 0.8 alpha → `0xCC000000`

## Font Format

Fonts use Pango font description format:
- `Sans 24` - Sans serif, 24pt
- `Sans Bold 32` - Sans serif, bold, 32pt
- `Serif 20` - Serif, 20pt

## Future Enhancements

### Phase 2: HTML/CSS Rendering

- Headless browser rendering for complex graphics
- CSS animations for stingers and tickers
- Template engine (Jinja2) for dynamic content
- Web server integration for real-time updates

### Phase 3: Advanced Features

- Real-time data binding (WebSocket)
- External data sources (REST APIs)
- Custom animation editor
- Brand asset management
- Graphics library/browser
- Export/import templates
- Multi-language support

## Troubleshooting

### Graphics Not Appearing

1. Check that the graphics source is created:
   ```bash
   GET /api/graphics/{source_id}
   ```

2. Verify the source is added to the scene:
   ```bash
   GET /api/scenes/{scene_id}
   ```

3. Check mixer logs for GStreamer errors:
   ```bash
   journalctl -u preke-recorder.service -f
   ```

### Text Not Displaying

- Verify text is not empty
- Check font name is valid (use "Sans", "Serif", "Monospace")
- Ensure text color contrasts with background

### Position Issues

- Position presets are relative to 1920x1080 resolution
- Custom positions can be set using x, y coordinates
- Ensure graphics fit within screen bounds

## Examples

### Example 1: Simple Lower-Third

```bash
curl -X POST http://localhost:8000/api/graphics/lower_third \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "host1",
    "line1": "Sarah Johnson",
    "line2": "News Anchor",
    "position": "bottom-left"
  }'
```

### Example 2: Using Template

```bash
curl -X POST http://localhost:8000/api/graphics/template/lower_third_modern \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "guest1",
    "line1": "Dr. Michael Chen",
    "line2": "Professor of Computer Science"
  }'
```

### Example 3: Clock Timer

```bash
curl -X POST http://localhost:8000/api/graphics/graphics \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "clock",
    "type": "timer",
    "timer_type": "clock",
    "position": "top-right",
    "text_color": "#FFFFFF",
    "font": "Sans 24"
  }'
```

## API Reference

### Graphics Endpoints

- `POST /api/graphics/lower_third` - Create/update lower-third
- `GET /api/graphics/templates` - List templates
- `GET /api/graphics/templates/{id}` - Get template
- `POST /api/graphics/template/{id}` - Apply template
- `GET /api/graphics/{source_id}` - Get graphics source
- `DELETE /api/graphics/{source_id}` - Delete graphics source
- `POST /api/graphics/graphics` - Create graphics source (stinger, ticker, timer, etc.)

## Files

- `src/mixer/graphics.py` - GStreamer graphics renderer
- `src/mixer/graphics_templates.py` - Template definitions
- `src/mixer/html_graphics.py` - HTML/CSS graphics renderer
- `graphics_templates/` - HTML template directory
- `src/main.py` - API endpoints

