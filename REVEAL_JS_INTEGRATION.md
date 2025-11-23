# Reveal.js Integration Guide

## Installation on Mekotronics R58

Reveal.js is installed as a full development setup within the project directory at:
```
preke-r58-recorder/reveal.js/
```

### Installation Steps

1. **Prerequisites:**
   - Node.js 18.0.0 or higher
   - npm (comes with Node.js)
   - git (for cloning the repository)

2. **Clone and Install:**
   ```bash
   cd preke-r58-recorder
   git clone https://github.com/hakimel/reveal.js.git
   cd reveal.js
   npm install
   npm run build
   ```

3. **Verify Installation:**
   - Check that `dist/` directory exists with built files
   - Verify `node_modules/` is installed

### Running on R58 Device

**Development Server (Port 8001):**
```bash
cd preke-r58-recorder/reveal.js
npm run start:dev
```
Access at: `http://192.168.1.104:8001` (or device IP)

**Production (via FastAPI):**
The built files are automatically served by FastAPI at `/reveal.js/` endpoint.
- CSS: `http://192.168.1.104:8000/reveal.js/reveal.css`
- JS: `http://192.168.1.104:8000/reveal.js/reveal.js`
- Themes: `http://192.168.1.104:8000/reveal.js/theme/{theme-name}.css`

### Port Configuration

- **FastAPI**: Port 8000 (main application)
- **Reveal.js Dev Server**: Port 8001 (development only)
- The production build is served via FastAPI static file mounting

### File Structure

```
preke-r58-recorder/
├── reveal.js/              # Full Reveal.js installation
│   ├── dist/               # Built files (served by FastAPI)
│   │   ├── reveal.css
│   │   ├── reveal.js
│   │   └── theme/          # Theme CSS files
│   ├── js/                 # Source files (for customization)
│   ├── css/                # Styles and themes (source)
│   ├── plugin/             # Plugins
│   ├── package.json        # Dependencies
│   └── gulpfile.js         # Build configuration
└── src/
    └── main.py             # FastAPI app (mounts reveal.js/dist)
```

## Local Development Setup

For local development on macOS, Reveal.js is also available at:
```
/Users/mariusbelstad/R58 app/reveal.js-local
```

### Running Locally

1. **Start the development server:**
   ```bash
   cd "/Users/mariusbelstad/R58 app/reveal.js-local"
   npm start
   ```

2. **Access the presentation:**
   Open your browser to: `http://localhost:8000`

3. **Edit the presentation:**
   - Main demo: `index.html`
   - Examples: `examples/` directory
   - Custom presentations: Create new HTML files in the root

## Integration with Switcher

### Current Implementation

The graphics app (`/graphics`) can use Reveal.js from:
1. **CDN** (current default) - Online, no local setup needed
2. **Local installation** - Served via FastAPI at `/reveal.js/`

### Using Local Reveal.js Installation

The built Reveal.js files are automatically available via FastAPI. To use them in your HTML:

```html
<!-- Use local installation instead of CDN -->
<link rel="stylesheet" href="/reveal.js/reveal.css">
<link rel="stylesheet" href="/reveal.js/theme/black.css" id="theme">
<script src="/reveal.js/reveal.js"></script>
```

### Customizing Reveal.js

1. **Make changes to source files:**
   - Edit files in `reveal.js/js/` for JavaScript changes
   - Edit files in `reveal.js/css/` for styling changes
   - Modify themes in `reveal.js/css/theme/`

2. **Rebuild after changes:**
   ```bash
   cd preke-r58-recorder/reveal.js
   npm run build
   ```

3. **Restart FastAPI** to serve updated files (if needed)

### Building and Testing

1. **Development workflow:**
   ```bash
   cd preke-r58-recorder/reveal.js
   npm run start:dev  # Runs on port 8001
   ```

2. **Production build:**
   ```bash
   npm run build  # Creates optimized files in dist/
   ```

3. **Integration with switcher:**
   - Add presentation control buttons in switcher UI
   - Use Reveal.js API for remote control
   - Sync presentation state with mixer

## Reveal.js API for Switcher Control

### Remote Control Methods

```javascript
// Navigate slides
Reveal.next();
Reveal.prev();
Reveal.slide(index);
Reveal.left();
Reveal.right();
Reveal.up();
Reveal.down();

// Get current state
Reveal.getIndices(); // { h: 0, v: 0, f: 0 }
Reveal.getTotalSlides();
Reveal.getSlidePastCount();
Reveal.getProgress();

// Events
Reveal.on('slidechanged', (event) => {
    console.log('Slide changed:', event.indexh, event.indexv);
});
```

### Integration Points

1. **Switcher UI:**
   - Add "Presentation" source type
   - Show current slide number
   - Navigation controls (prev/next)
   - Slide preview thumbnails

2. **API Endpoints:**
   - `POST /api/graphics/presentation/control` - Navigate slides
   - `GET /api/graphics/presentation/status` - Get current slide
   - `POST /api/graphics/presentation/goto/{slide}` - Go to specific slide

3. **Mixer Integration:**
   - Render Reveal.js presentation as video source
   - Use headless browser (Puppeteer/Playwright) to capture slides
   - Stream to mixer compositor

## Customization Areas

### 1. Themes
- Location: `reveal.js/css/theme/` (source) or `reveal.js/dist/theme/` (built)
- Create custom theme or modify existing
- Available themes: black, white, league, beige, sky, night, serif, simple, solarized
- Update `graphics.html` to use your theme

### 2. Plugins
- Location: `reveal.js/plugin/`
- Available plugins: Markdown, Notes, Highlight, Math, Search, Zoom
- Add custom plugins for switcher integration
- Plugins are included in the build automatically

### 3. Configuration
- Modify `reveal.js/index.html` or create custom HTML
- Configure transitions, controls, keyboard shortcuts
- Add custom CSS for switcher-specific styling
- Configuration is done in JavaScript when initializing Reveal.js

### 4. API Extensions
- Add custom methods for switcher control
- Create WebSocket server for real-time control
- Add REST API wrapper for HTTP control
- Extend `src/mixer/graphics.py` for video source integration

## Next Steps

1. **Review Reveal.js locally:**
   - Open `http://localhost:8000`
   - Explore examples in `examples/` directory
   - Test different themes and configurations

2. **Identify customizations needed:**
   - What features to add/remove?
   - What styling changes?
   - What API extensions?

3. **Design switcher integration:**
   - How should presentations appear in switcher?
   - What controls are needed?
   - How to sync with mixer?

4. **Implement:**
   - Make customizations to Reveal.js
   - Build and integrate
   - Add switcher controls
   - Test end-to-end

## Files to Review

- `reveal.js/index.html` - Main demo presentation
- `reveal.js/demo.html` - Extended demo
- `reveal.js/examples/` - Various examples
- `reveal.js/js/reveal.js` - Core library (source)
- `reveal.js/css/theme/` - Available themes (source)
- `reveal.js/dist/` - Built files (production)

## Useful Commands

```bash
# Navigate to reveal.js directory
cd preke-r58-recorder/reveal.js

# Start development server (port 8001)
npm run start:dev

# Start development server (port 8000, may conflict with FastAPI)
npm start

# Build for production
npm run build

# Run tests
npm test

# View development server
# http://localhost:8001 (or device IP:8001)

# Access via FastAPI (production)
# http://localhost:8000/reveal.js/reveal.css
# http://localhost:8000/reveal.js/reveal.js
```

## Future Integration Points

### Video Source Conversion

The existing `GraphicsRenderer.create_presentation_source()` method in `src/mixer/graphics.py` will need to:

1. **Serve Reveal.js HTML files** from the installed location
2. **Use headless browser** (Chromium) or GStreamer's `souphttpsrc` to capture rendered HTML
3. **Convert to video stream** for mixer compositor

### Serving Strategy

- **Option 1 (Current)**: FastAPI serves `reveal.js/dist/` as static files at `/reveal.js/`
- **Option 2**: Reveal.js dev server runs on port 8001, accessed via HTTP
- **Option 3**: Hybrid - built files in static, dev server for development

Current implementation uses Option 1, which is the most efficient for production use.

## Troubleshooting

### Port Conflicts
- If port 8000 is already in use, Reveal.js dev server will fail
- Use `npm run start:dev` which uses port 8001
- Or specify custom port: `gulp serve --port 8002`

### Node.js Version
- Requires Node.js 18.0.0 or higher
- Check version: `node --version`
- Install/update Node.js if needed

### Build Issues
- Ensure all dependencies are installed: `npm install`
- Clear node_modules and reinstall if build fails: `rm -rf node_modules && npm install`
- Check for errors in build output

### FastAPI Not Serving Files
- Verify `reveal.js/dist/` directory exists
- Check that `src/main.py` has the reveal.js mount (should be automatic)
- Restart FastAPI application after building reveal.js

