# Reveal.js Integration Guide

## Local Setup

Reveal.js is now set up locally at:
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

The graphics app (`/graphics`) currently uses Reveal.js from CDN. To integrate a customized local version:

### Option 1: Copy Customized Reveal.js to Project

1. **Customize Reveal.js locally:**
   - Make your changes in `reveal.js-local/`
   - Test them at `http://localhost:8000`

2. **Build the customized version:**
   ```bash
   cd reveal.js-local
   npm run build
   ```

3. **Copy to project:**
   ```bash
   # Copy dist files to your project
   cp -r reveal.js-local/dist/* preke-r58-recorder/src/static/reveal.js/
   ```

4. **Update graphics.html:**
   - Change CDN links to local files:
   ```html
   <!-- Instead of CDN -->
   <link rel="stylesheet" href="/static/reveal.js/reveal.css">
   <script src="/static/reveal.js/reveal.js"></script>
   ```

### Option 2: Fork and Customize (Recommended)

1. **Fork Reveal.js repository:**
   - Create your own fork on GitHub
   - Make customizations
   - Build and use your version

2. **Integrate with switcher:**
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
- Location: `reveal.js-local/css/theme/`
- Create custom theme or modify existing
- Update `graphics.html` to use your theme

### 2. Plugins
- Location: `reveal.js-local/plugin/`
- Available plugins: Markdown, Notes, Highlight, etc.
- Add custom plugins for switcher integration

### 3. Configuration
- Modify `index.html` or create custom HTML
- Configure transitions, controls, keyboard shortcuts
- Add custom CSS for switcher-specific styling

### 4. API Extensions
- Add custom methods for switcher control
- Create WebSocket server for real-time control
- Add REST API wrapper for HTTP control

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

- `reveal.js-local/index.html` - Main demo presentation
- `reveal.js-local/demo.html` - Extended demo
- `reveal.js-local/examples/` - Various examples
- `reveal.js-local/js/reveal.js` - Core library (source)
- `reveal.js-local/css/theme/` - Available themes

## Useful Commands

```bash
# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# View at http://localhost:8000
```

