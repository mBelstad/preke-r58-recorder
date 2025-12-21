const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// Environment variables
const CF_TURN_ID = process.env.CF_TURN_ID;
const CF_TURN_TOKEN = process.env.CF_TURN_TOKEN;
const PORT = process.env.PORT || 3000;

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'r58-turn-api' });
});

// TURN credentials endpoint
app.get('/turn-credentials', async (req, res) => {
  try {
    if (!CF_TURN_ID || !CF_TURN_TOKEN) {
      return res.status(500).json({ 
        error: 'TURN service not configured',
        message: 'CF_TURN_ID and CF_TURN_TOKEN environment variables are required'
      });
    }

    // Fetch fresh credentials from Cloudflare
    const response = await fetch(
      `https://rtc.live.cloudflare.com/v1/turn/keys/${CF_TURN_ID}/credentials/generate`,
      {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${CF_TURN_TOKEN}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ ttl: 86400 }) // 24 hours
      }
    );

    if (!response.ok) {
      throw new Error(`Cloudflare API error: ${response.status}`);
    }

    const data = await response.json();
    
    // Return in standard WebRTC format
    res.json({ 
      iceServers: data.iceServers,
      expiresAt: new Date(Date.now() + 86400000).toISOString()
    });
    
  } catch (error) {
    console.error('Error fetching TURN credentials:', error);
    res.status(500).json({ 
      error: 'Failed to get TURN credentials',
      message: error.message 
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`R58 TURN API listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`TURN credentials: http://localhost:${PORT}/turn-credentials`);
});

