const https = require('https');
const express = require('express');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuration
const HTTPS_PORT = 8443;
const VDO_NINJA_PATH = '/opt/vdo.ninja';

// UNIFIED ROOM ID - all room IDs are rewritten to this value
// This ensures VDO.ninja browser and raspberry.ninja see each other
const UNIFIED_ROOM = 'r58studio';

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

// Store ALL connections
const connections = new Map();

// Store streamID to connection mapping
const streamIds = new Map();

function log(message, data = null) {
  const timestamp = new Date().toISOString();
  if (data) {
    console.log(`[${timestamp}] ${message}`, JSON.stringify(data, null, 2));
  } else {
    console.log(`[${timestamp}] ${message}`);
  }
}

// Rewrite roomid in message to unified room
function rewriteMessage(data) {
  // Rewrite roomid to unified value if present
  if (data.roomid) {
    log(`Rewriting roomid: ${data.roomid} -> ${UNIFIED_ROOM}`);
    data.roomid = UNIFIED_ROOM;
  }
  return data;
}

// Broadcast to ALL connections
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

// Send to specific UUID
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
    isPublisher: false
  });
  
  log(`New connection: ${connectionId} (total: ${connections.size})`);
  
  ws.on('message', (message) => {
    try {
      let data = JSON.parse(message);
      const conn = connections.get(connectionId);
      
      // REWRITE ROOMID TO UNIFIED VALUE
      data = rewriteMessage(data);
      const messageStr = JSON.stringify(data);
      
      // Handle joinroom request
      if (data.request === 'joinroom') {
        conn.streamId = data.streamID || data.streamid || null;
        conn.UUID = data.UUID || null;
        
        // Check if publisher (has r58- prefix in streamID)
        if (conn.streamId && conn.streamId.startsWith('r58-')) {
          conn.isPublisher = true;
          streamIds.set(conn.streamId, connectionId);
          log(`Publisher joined: ${conn.streamId}`);
        } else {
          log(`Viewer/Director joined: ${conn.streamId || 'no-streamId'}`);
        }
        
        // Broadcast rewritten message to ALL connections
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted joinroom to ${sentCount} peers (roomid rewritten to ${UNIFIED_ROOM})`);
        
        // Send existing publisher streams to this new connection
        if (!conn.isPublisher) {
          connections.forEach((c, cid) => {
            if (c.isPublisher && c.streamId && cid !== connectionId) {
              // Send a joinroom-like message for each publisher
              const publisherMsg = JSON.stringify({
                request: 'joinroom',
                roomid: UNIFIED_ROOM,
                streamID: c.streamId,
                UUID: c.UUID
              });
              ws.send(publisherMsg);
              log(`Notified new viewer of existing publisher: ${c.streamId}`);
            }
          });
        }
      }
      // Handle seed request
      else if (data.request === 'seed') {
        conn.streamId = data.streamID || data.streamid || conn.streamId;
        conn.UUID = data.UUID || conn.UUID;
        conn.isPublisher = true;
        
        if (conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
        }
        
        log(`Publisher seeding: ${conn.streamId}`);
        
        // Broadcast to ALL
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted seed to ${sentCount} peers`);
      }
      // Handle play request
      else if (data.request === 'play') {
        log(`Play request for: ${data.streamID || data.streamid}`);
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted play to ${sentCount} peers`);
      }
      // Handle SDP offers/answers - route by UUID if possible
      else if (data.description) {
        conn.UUID = data.UUID || conn.UUID;
        
        if (data.UUID) {
          const sent = sendToUUID(data.UUID, messageStr);
          if (sent) {
            log(`Routed ${data.description.type} to UUID: ${data.UUID}`);
          } else {
            const sentCount = broadcastToAll(messageStr, connectionId);
            log(`Broadcasted ${data.description.type} to ${sentCount} peers`);
          }
        } else {
          const sentCount = broadcastToAll(messageStr, connectionId);
          log(`Broadcasted ${data.description.type} to ${sentCount} peers`);
        }
      }
      // Handle ICE candidates
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
        log(`Other message from ${connectionId}`, { request: data.request });
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted to ${sentCount} peers`);
      }
    } catch (err) {
      console.error(`[${new Date().toISOString()}] Error:`, err);
    }
  });
  
  ws.on('close', () => {
    const conn = connections.get(connectionId);
    if (conn && conn.streamId) {
      streamIds.delete(conn.streamId);
    }
    connections.delete(connectionId);
    log(`Connection closed: ${connectionId} (total: ${connections.size})`);
  });
  
  ws.on('error', (error) => {
    console.error(`[${new Date().toISOString()}] WebSocket error:`, error);
    const conn = connections.get(connectionId);
    if (conn && conn.streamId) {
      streamIds.delete(conn.streamId);
    }
    connections.delete(connectionId);
  });
});

// Start server
server.listen(HTTPS_PORT, '0.0.0.0', () => {
  log('VDO.Ninja server with ROOMID REWRITING started');
  console.log(`  - HTTPS/WebSocket: https://0.0.0.0:${HTTPS_PORT}`);
  console.log(`  - Serving static files from: ${VDO_NINJA_PATH}`);
  console.log(`  - All roomid fields rewritten to: ${UNIFIED_ROOM}`);
  console.log(`  - This ensures VDO.ninja browser and raspberry.ninja compatibility`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  log('SIGTERM received, closing server...');
  server.close(() => process.exit(0));
});

process.on('SIGINT', () => {
  log('SIGINT received, closing server...');
  server.close(() => process.exit(0));
});

