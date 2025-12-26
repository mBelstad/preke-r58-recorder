// R58 Documentation Wiki - Main JavaScript

// Initialize Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true
    }
});

// Global state
let fuse = null;
let currentSection = 'welcome';
let darkMode = localStorage.getItem('darkMode') === 'true';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeDarkMode();
    initializeSearch();
    initializeNavigation();
    loadSection('welcome');
    setupEventListeners();
});

// Dark Mode
function initializeDarkMode() {
    if (darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
    }
    
    // Update Mermaid theme
    mermaid.initialize({
        theme: darkMode ? 'dark' : 'default'
    });
}

function toggleDarkMode() {
    darkMode = !darkMode;
    localStorage.setItem('darkMode', darkMode);
    initializeDarkMode();
    
    // Re-render current section to update diagrams
    loadSection(currentSection);
}

// Search Functionality
function initializeSearch() {
    // Prepare search index from wiki content
    const searchData = [];
    
    for (const [sectionId, section] of Object.entries(wikiContent)) {
        // Add section to search index
        searchData.push({
            id: sectionId,
            title: section.title,
            content: section.simple + ' ' + section.technical,
            tags: section.tags || []
        });
    }
    
    // Initialize Fuse.js
    fuse = new Fuse(searchData, {
        keys: [
            { name: 'title', weight: 0.4 },
            { name: 'content', weight: 0.3 },
            { name: 'tags', weight: 0.3 }
        ],
        threshold: 0.3,
        includeMatches: true,
        minMatchCharLength: 2
    });
}

function performSearch(query) {
    if (!query || query.length < 2) {
        hideSearchResults();
        return;
    }
    
    const results = fuse.search(query);
    displaySearchResults(results, query);
}

function displaySearchResults(results, query) {
    const resultsContainer = document.getElementById('searchResults');
    
    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="search-result-item"><div class="search-result-excerpt">No results found</div></div>';
        resultsContainer.classList.add('active');
        return;
    }
    
    resultsContainer.innerHTML = results.slice(0, 8).map(result => {
        const item = result.item;
        const excerpt = getExcerpt(item.content, query);
        
        return `
            <div class="search-result-item" data-section="${item.id}">
                <div class="search-result-title">${item.title}</div>
                <div class="search-result-excerpt">${excerpt}</div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    resultsContainer.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            const sectionId = item.getAttribute('data-section');
            loadSection(sectionId);
            hideSearchResults();
            document.getElementById('searchInput').value = '';
        });
    });
    
    resultsContainer.classList.add('active');
}

function getExcerpt(content, query) {
    const lowerContent = content.toLowerCase();
    const lowerQuery = query.toLowerCase();
    const index = lowerContent.indexOf(lowerQuery);
    
    if (index === -1) {
        return content.substring(0, 150) + '...';
    }
    
    const start = Math.max(0, index - 50);
    const end = Math.min(content.length, index + query.length + 100);
    let excerpt = content.substring(start, end);
    
    if (start > 0) excerpt = '...' + excerpt;
    if (end < content.length) excerpt = excerpt + '...';
    
    // Highlight the query
    const regex = new RegExp(`(${query})`, 'gi');
    excerpt = excerpt.replace(regex, '<span class="search-highlight">$1</span>');
    
    return excerpt;
}

function hideSearchResults() {
    document.getElementById('searchResults').classList.remove('active');
}

// Navigation
function initializeNavigation() {
    // Set up nav link click handlers
    document.querySelectorAll('.nav-list a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.getAttribute('data-section');
            loadSection(sectionId);
        });
    });
}

function loadSection(sectionId) {
    if (!wikiContent[sectionId]) {
        console.error('Section not found:', sectionId);
        return;
    }
    
    currentSection = sectionId;
    const section = wikiContent[sectionId];
    const contentDiv = document.getElementById('wikiContent');
    
    // Update active nav link
    document.querySelectorAll('.nav-list a').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-section') === sectionId) {
            link.classList.add('active');
        }
    });
    
    // Render content
    let html = `<h1>${section.title}</h1>`;
    
    // Add simple explanation
    if (section.simple) {
        html += `
            <div class="callout callout-info">
                <div class="callout-title">📝 Simple Explanation</div>
                ${marked.parse(section.simple)}
            </div>
        `;
    }
    
    // Add diagram if present
    if (section.diagram) {
        html += `
            <div class="diagram-container">
                <div class="mermaid">
${section.diagram}
                </div>
            </div>
        `;
    }
    
    // Add technical details
    if (section.technical) {
        html += `
            <div class="callout callout-success">
                <div class="callout-title">🔧 Technical Details</div>
                ${marked.parse(section.technical)}
            </div>
        `;
    }
    
    // Add main content
    if (section.content) {
        html += marked.parse(section.content);
    }
    
    // Add key points if present
    if (section.keyPoints && section.keyPoints.length > 0) {
        html += `
            <div class="callout callout-warning">
                <div class="callout-title">💡 Key Points</div>
                <ul>
                    ${section.keyPoints.map(point => `<li>${point}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    contentDiv.innerHTML = html;
    
    // Render Mermaid diagrams
    if (section.diagram) {
        mermaid.run({
            querySelector: '.mermaid'
        });
    }
    
    // Scroll to top
    contentDiv.scrollIntoView({ behavior: 'smooth' });
    
    // Update URL hash
    window.location.hash = sectionId;
}

// Event Listeners
function setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
        performSearch(e.target.value);
    });
    
    // Click outside search results to close
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            hideSearchResults();
        }
    });
    
    // Dark mode toggle
    document.getElementById('darkModeToggle').addEventListener('click', toggleDarkMode);
    
    // Print button
    document.getElementById('printBtn').addEventListener('click', () => {
        window.print();
    });
    
    // Handle hash navigation
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.substring(1);
        if (hash && wikiContent[hash]) {
            loadSection(hash);
        }
    });
    
    // Load from hash if present
    const hash = window.location.hash.substring(1);
    if (hash && wikiContent[hash]) {
        loadSection(hash);
    }
}

// Utility: Copy code blocks
document.addEventListener('click', (e) => {
    if (e.target.closest('pre code')) {
        const code = e.target.closest('pre code');
        navigator.clipboard.writeText(code.textContent).then(() => {
            // Show feedback
            const feedback = document.createElement('div');
            feedback.textContent = 'Copied!';
            feedback.style.cssText = 'position: fixed; top: 20px; right: 20px; background: var(--success-color); color: white; padding: 0.5rem 1rem; border-radius: 6px; z-index: 9999;';
            document.body.appendChild(feedback);
            setTimeout(() => feedback.remove(), 2000);
        });
    }
});

