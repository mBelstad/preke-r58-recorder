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

// Store ALL connections
const connections = new Map();

// Store streamID to connection mapping
const streamIds = new Map();

// Store known room hash variants for "r58studio"
// VDO.ninja browser uses: d2869f4ba7cc9ad6
// raspberry.ninja uses: 8e27706569be0e92 (with salt 192.168.1.24)
// We'll use the browser's hash as the canonical one
let CANONICAL_ROOM_HASH = null;
const ROOM_HASH_ALIASES = new Set();

function log(message, data = null) {
  const timestamp = new Date().toISOString();
  if (data) {
    console.log(`[${timestamp}] ${message}`, JSON.stringify(data, null, 2));
  } else {
    console.log(`[${timestamp}] ${message}`);
  }
}

// Register a room hash and set canonical if from browser
function registerRoomHash(hash, isFromPublisher) {
  ROOM_HASH_ALIASES.add(hash);
  
  // First non-publisher (browser) hash becomes canonical
  if (!CANONICAL_ROOM_HASH && !isFromPublisher) {
    CANONICAL_ROOM_HASH = hash;
    log(`Set canonical room hash: ${CANONICAL_ROOM_HASH}`);
  }
}

// Rewrite roomid to canonical hash
function rewriteRoomId(data, isFromPublisher) {
  if (!data.roomid) return data;
  
  const originalHash = data.roomid;
  registerRoomHash(originalHash, isFromPublisher);
  
  // If we have a canonical hash and this differs, rewrite it
  if (CANONICAL_ROOM_HASH && originalHash !== CANONICAL_ROOM_HASH) {
    log(`Rewriting roomid: ${originalHash} -> ${CANONICAL_ROOM_HASH}`);
    data.roomid = CANONICAL_ROOM_HASH;
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
      
      // Detect if this is a publisher (r58- prefix in streamID)
      const streamId = data.streamID || data.streamid;
      const isPublisher = streamId && streamId.startsWith('r58-');
      
      // REWRITE ROOMID to match browser's hash
      data = rewriteRoomId(data, isPublisher);
      const messageStr = JSON.stringify(data);
      
      // Handle joinroom request
      if (data.request === 'joinroom') {
        conn.streamId = streamId || null;
        conn.UUID = data.UUID || null;
        conn.isPublisher = isPublisher;
        
        if (conn.isPublisher && conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
          log(`Publisher joined: ${conn.streamId}`);
        } else {
          log(`Viewer/Director joined: ${conn.streamId || 'no-streamId'}`);
        }
        
        // Broadcast rewritten message
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted joinroom to ${sentCount} peers`);
        
        // If this is a director/viewer, notify them of existing publishers
        if (!conn.isPublisher && CANONICAL_ROOM_HASH) {
          connections.forEach((c, cid) => {
            if (c.isPublisher && c.streamId && cid !== connectionId) {
              const publisherMsg = JSON.stringify({
                request: 'joinroom',
                roomid: CANONICAL_ROOM_HASH,
                streamID: c.streamId,
                UUID: c.UUID
              });
              ws.send(publisherMsg);
              log(`Sent publisher announcement: ${c.streamId}`);
            }
          });
        }
      }
      // Handle seed request
      else if (data.request === 'seed') {
        conn.streamId = streamId || conn.streamId;
        conn.UUID = data.UUID || conn.UUID;
        conn.isPublisher = true;
        
        if (conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
        }
        
        log(`Publisher seeding: ${conn.streamId}`);
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted seed to ${sentCount} peers`);
      }
      // Handle play request
      else if (data.request === 'play') {
        log(`Play request for: ${streamId}`);
        const sentCount = broadcastToAll(messageStr, connectionId);
        log(`Broadcasted play to ${sentCount} peers`);
      }
      // Handle SDP offers/answers
      else if (data.description) {
        conn.UUID = data.UUID || conn.UUID;
        
        if (data.UUID) {
          const sent = sendToUUID(data.UUID, messageStr);
          if (sent) {
            log(`Routed ${data.description.type} to UUID`);
          } else {
            broadcastToAll(messageStr, connectionId);
          }
        } else {
          broadcastToAll(messageStr, connectionId);
        }
      }
      // Handle ICE candidates
      else if (data.candidate || data.candidates) {
        if (data.UUID) {
          sendToUUID(data.UUID, messageStr) || broadcastToAll(messageStr, connectionId);
        } else {
          broadcastToAll(messageStr, connectionId);
        }
      }
      // Handle all other messages
      else {
        broadcastToAll(messageStr, connectionId);
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
    connections.delete(connectionId);
  });
});

// Start server
server.listen(HTTPS_PORT, '0.0.0.0', () => {
  log('VDO.Ninja server with HASH MATCHING started');
  console.log(`  - HTTPS/WebSocket: https://0.0.0.0:${HTTPS_PORT}`);
  console.log(`  - Serving static files from: ${VDO_NINJA_PATH}`);
  console.log(`  - First browser connection sets canonical room hash`);
  console.log(`  - All subsequent roomids are rewritten to match`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
});

process.on('SIGINT', () => {
  server.close(() => process.exit(0));
});


