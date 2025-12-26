# How to Use Reveal.js in the Graphics App

## Quick Start

1. **Access the App**: Open `http://192.168.1.104:8000/graphics` in your browser

2. **Create a New Presentation**:
   - Enter a **Name** (e.g., "Conference Opening")
   - Enter an **ID** (e.g., "conference_opening") - must be unique, lowercase, no spaces
   - Select a **Theme** (Black, White, League, Beige, Sky, Night, Serif, Simple, Solarized)
   - Click **Save**

3. **Add Slides**: Click **"Add Slide"** button

4. **Edit Slide Content**: Use the textarea to write Markdown or HTML

5. **Update Slide**: Click **"Update Slide"** to save changes

6. **Navigate**: Use ◀ ▶ buttons or keyboard shortcuts

---

## Markdown Examples

### Basic Slide
```markdown
# Welcome

This is a simple slide
```

### Bullet Points
```markdown
# Agenda

- Introduction
- Main Topic
- Q&A
```

### Code Blocks
````markdown
# Code Example

```python
def hello():
    print("Hello, World!")
```
````

### Images
```markdown
# Image Slide

![Description](image-url.jpg)
```

### Two Columns
```markdown
# Two Column Layout

<div style="display: grid; grid-template-columns: 1fr 1fr;">
  <div>
    Left column content
  </div>
  <div>
    Right column content
  </div>
</div>
```

### Speaker Notes
```markdown
# Slide Title

Content here

Note:
This is a speaker note - only visible in presenter mode
```

---

## HTML Examples

### Styled Content
```html
<h1 style="color: #3b82f6;">Blue Title</h1>
<p style="font-size: 24px;">Large text</p>
```

### Embedded Video
```html
<iframe src="https://www.youtube.com/embed/VIDEO_ID"></iframe>
```

### Custom Layout
```html
<div style="display: flex; align-items: center; justify-content: center; height: 100%;">
  <div>
    <h1>Centered Content</h1>
  </div>
</div>
```

---

## Keyboard Shortcuts

- **Space** or **Arrow Right**: Next slide
- **Arrow Left**: Previous slide
- **F**: Fullscreen mode
- **ESC**: Overview mode (see all slides)
- **S**: Speaker notes view
- **B**: Pause/black screen
- **O**: Overview toggle

---

## Themes

Choose from 9 built-in themes:
- **Black** (default) - Dark background, white text
- **White** - Light background, dark text
- **League** - Dark with blue accents
- **Beige** - Warm, light theme
- **Sky** - Light blue theme
- **Night** - Very dark theme
- **Serif** - Classic serif fonts
- **Simple** - Minimalist design
- **Solarized** - Eye-friendly color scheme

---

## Workflow

### Creating a Presentation

1. **Start Fresh**: Select "New Presentation..." from dropdown
2. **Fill Details**: Name, ID, Theme
3. **Add First Slide**: Click "Add Slide"
4. **Write Content**: Enter Markdown/HTML in textarea
5. **Update**: Click "Update Slide"
6. **Save**: Click "Save" to persist to server

### Editing Existing Presentation

1. **Load**: Select presentation from dropdown
2. **Navigate**: Use ◀ ▶ to find slide
3. **Edit**: Modify content in textarea
4. **Update**: Click "Update Slide"
5. **Save**: Click "Save"

### Adding More Slides

1. **Navigate** to where you want to add (before/after current slide)
2. **Click "Add Slide"**
3. **Edit** the new slide content
4. **Update** and **Save**

---

## Integration with Mixer

### Export to Mixer (Future Feature)

Once implemented, you'll be able to:
1. Create your presentation
2. Click **"Export to Mixer"**
3. Presentation becomes available as a graphics source in the mixer
4. Use it in mixer scenes like any other source

### Use Cases

- **Lower Thirds**: Create slides with speaker names/titles
- **Title Cards**: Opening/closing slides
- **Information Graphics**: Charts, stats, announcements
- **Speaker Notes**: Display talking points
- **Live Updates**: Modify slides in real-time during production

---

## Tips & Best Practices

1. **Keep Slides Simple**: One main idea per slide
2. **Use Markdown**: Easier to write and maintain
3. **Test Navigation**: Use keyboard shortcuts for smooth presentations
4. **Save Frequently**: Click Save after major changes
5. **Preview**: Use Reveal.js viewer to see how slides look
6. **Speaker Notes**: Add notes for presenter reference
7. **Theme Consistency**: Stick to one theme per presentation

---

## Troubleshooting

### Presentation Not Saving
- Check that Name and ID are filled
- ID must be unique (lowercase, no spaces)
- Check browser console for errors

### Slides Not Updating
- Click "Update Slide" after editing
- Click "Save" to persist changes
- Refresh page if needed

### Reveal.js Not Loading
- Check internet connection (CDN required)
- Check browser console for errors
- Try refreshing the page

---

## Advanced Features (Coming Soon)

- **Animations**: Slide transitions and element animations
- **Background Images**: Custom slide backgrounds
- **Video Backgrounds**: Video as slide background
- **Live Updates**: Real-time slide modifications
- **Remote Control**: Control from mobile device
- **Export Options**: PDF, HTML export

---

## Example: Conference Presentation

```markdown
# Welcome to R58 Conference

## Day 1 - November 23, 2025

---

# Agenda

- Opening Remarks
- Keynote Presentation
- Technical Sessions
- Q&A

---

# Keynote: Video Production

## With the R58 Mixer

- Multi-camera switching
- Live graphics overlay
- Real-time recording

---

# Questions?

## Thank you!
```

---

## Need Help?

- Check the browser console (F12) for errors
- Verify API endpoints are responding
- Check service status: `systemctl status preke-recorder.service`
- Review logs: `journalctl -u preke-recorder.service -f`

