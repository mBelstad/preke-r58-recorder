const https = require('https');
const express = require('express');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuration
const HTTPS_PORT = 8443;
const VDO_NINJA_PATH = '/opt/vdo.ninja';

// Load SSL certificates
const serverOptions = {
  key: fs.readFileSync(path.join(__dirname, 'key.pem')),
  cert: fs.readFileSync(path.join(__dirname, 'cert.pem'))
};

// Create Express app
const app = express();

// Serve VDO.Ninja static files
app.use(express.static(VDO_NINJA_PATH));

// Create HTTPS server
const server = https.createServer(serverOptions, app);

// Create WebSocket server for signaling
const wss = new WebSocket.Server({ server });

// Store ALL connections (no room filtering - full broadcast)
const connections = new Map();

// Store streamID to connection mapping for targeted messages
const streamIds = new Map();

function log(message, data = null) {
  const timestamp = new Date().toISOString();
  if (data) {
    console.log(`[${timestamp}] ${message}`, JSON.stringify(data, null, 2));
  } else {
    console.log(`[${timestamp}] ${message}`);
  }
}

// Broadcast to ALL connections (unified room approach)
function broadcastToAll(message, excludeConnectionId = null) {
  let sentCount = 0;
  connections.forEach((conn, connId) => {
    if (connId !== excludeConnectionId && conn.ws.readyState === WebSocket.OPEN) {
      conn.ws.send(message);
      sentCount++;
    }
  });
  return sentCount;
}

// Send to specific connection by UUID
function sendToUUID(uuid, message) {
  for (const [connId, conn] of connections.entries()) {
    if (conn.UUID === uuid && conn.ws.readyState === WebSocket.OPEN) {
      conn.ws.send(message);
      return true;
    }
  }
  return false;
}

wss.on('connection', (ws, req) => {
  const connectionId = Math.random().toString(36).substring(7);
  
  // Initialize connection metadata
  connections.set(connectionId, {
    ws: ws,
    streamId: null,
    UUID: null,
    isPublisher: false,
    isDirector: false
  });
  
  log(`New connection: ${connectionId} (total: ${connections.size})`);
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      const conn = connections.get(connectionId);
      const messageStr = typeof message === 'string' ? message : message.toString();
      
      // Handle joinroom request - broadcast to everyone
      if (data.request === 'joinroom') {
        conn.streamId = data.streamID || data.streamid || null;
        conn.UUID = data.UUID || null;
        
        // Track streamID
        if (conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
        }
        
        // Check if this is a director (has streamID with specific patterns)
        if (conn.streamId && (conn.streamId.length > 10 || !conn.streamId.startsWith('r58-'))) {
          conn.isDirector = true;
          log(`Director joined: ${conn.streamId}`);
        }
        
        log(`Connection ${connectionId} joinroom`, {
          streamId: conn.streamId,
          UUID: conn.UUID
        });
        
        // Broadcast to ALL connections
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted joinroom to ${sentCount} peers`);
        
        // If this is a new director, send them all existing seeds
        if (conn.isDirector) {
          connections.forEach((c, cid) => {
            if (c.isPublisher && c.streamId && cid !== connectionId) {
              const seedMsg = JSON.stringify({
                request: 'seed',
                streamID: c.streamId,
                UUID: c.UUID
              });
              ws.send(seedMsg);
              log(`Sent existing seed to director: ${c.streamId}`);
            }
          });
        }
      }
      // Handle seed request (publisher announcing stream)
      else if (data.request === 'seed') {
        conn.streamId = data.streamID || data.streamid || conn.streamId;
        conn.UUID = data.UUID || conn.UUID;
        conn.isPublisher = true;
        
        // Track streamID
        if (conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
        }
        
        log(`Publisher seeding: ${conn.streamId}`);
        
        // Broadcast to ALL connections
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted seed to ${sentCount} peers`);
      }
      // Handle play request (viewer requesting stream)
      else if (data.request === 'play') {
        const targetStreamId = data.streamID || data.streamid;
        log(`Play request for streamID: ${targetStreamId}`);
        
        // Broadcast to ALL connections
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted play to ${sentCount} peers`);
      }
      // Handle SDP offer/answer - try to route by UUID first, then broadcast
      else if (data.description) {
        conn.UUID = data.UUID || conn.UUID;
        
        // Try to send to specific UUID first
        if (data.UUID) {
          const sent = sendToUUID(data.UUID, messageStr);
          if (sent) {
            log(`Routed ${data.description.type} to UUID: ${data.UUID}`);
          } else {
            // Fallback to broadcast
            const sentCount = broadcastToAll(messageStr, connectionId);
            log(`Broadcasted ${data.description.type} to ${sentCount} peers`);
          }
        } else {
          const sentCount = broadcastToAll(messageStr, connectionId);
          log(`Broadcasted ${data.description.type} to ${sentCount} peers`);
        }
      }
      // Handle ICE candidates - try to route by UUID first
      else if (data.candidate || data.candidates) {
        if (data.UUID) {
          const sent = sendToUUID(data.UUID, messageStr);
          if (sent) {
            log(`Routed ICE to UUID: ${data.UUID}`);
          } else {
            broadcastToAll(messageStr, connectionId);
          }
        } else {
          broadcastToAll(messageStr, connectionId);
        }
      }
      // Handle all other messages
      else {
        log(`Other message from ${connectionId}`, {
          request: data.request,
          hasUUID: !!data.UUID
        });
        
        // Broadcast to all
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted to ${sentCount} peers`);
      }
    } catch (err) {
      console.error(`[${new Date().toISOString()}] Error processing message from ${connectionId}:`, err);
    }
  });
  
  ws.on('close', () => {
    const conn = connections.get(connectionId);
    
    // Remove streamID mapping
    if (conn && conn.streamId) {
      streamIds.delete(conn.streamId);
    }
    
    connections.delete(connectionId);
    log(`Connection closed: ${connectionId} (total: ${connections.size})`);
  });
  
  ws.on('error', (error) => {
    console.error(`[${new Date().toISOString()}] WebSocket error for ${connectionId}:`, error);
    
    const conn = connections.get(connectionId);
    if (conn && conn.streamId) {
      streamIds.delete(conn.streamId);
    }
    
    connections.delete(connectionId);
  });
});

// Start server
server.listen(HTTPS_PORT, '0.0.0.0', () => {
  log('VDO.Ninja UNIFIED signaling server started');
  console.log(`  - HTTPS/WebSocket: https://0.0.0.0:${HTTPS_PORT}`);
  console.log(`  - Serving static files from: ${VDO_NINJA_PATH}`);
  console.log(`  - SSL certificates: ${__dirname}/key.pem, ${__dirname}/cert.pem`);
  console.log(`  - Mode: FULL BROADCAST (no room filtering)`);
  console.log(`  - Compatible with: VDO.ninja browser + raspberry.ninja`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  log('SIGTERM received, closing server...');
  server.close(() => {
    log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  log('SIGINT received, closing server...');
  server.close(() => {
    log('Server closed');
    process.exit(0);
  });
});

