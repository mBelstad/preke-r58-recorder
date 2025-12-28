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

// Store active connections with metadata
// connections: Map<connectionId, { ws, roomId, streamId, UUID }>
const connections = new Map();

// Store rooms: Map<roomId, Set<connectionId>>
const rooms = new Map();

function log(message, data = null) {
  const timestamp = new Date().toISOString();
  if (data) {
    console.log(`[${timestamp}] ${message}`, JSON.stringify(data, null, 2));
  } else {
    console.log(`[${timestamp}] ${message}`);
  }
}

function addToRoom(roomId, connectionId) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, new Set());
  }
  rooms.get(roomId).add(connectionId);
  log(`Added ${connectionId} to room ${roomId} (room size: ${rooms.get(roomId).size})`);
}

function removeFromRoom(roomId, connectionId) {
  if (rooms.has(roomId)) {
    rooms.get(roomId).delete(connectionId);
    if (rooms.get(roomId).size === 0) {
      rooms.delete(roomId);
      log(`Room ${roomId} is now empty and removed`);
    } else {
      log(`Removed ${connectionId} from room ${roomId} (room size: ${rooms.get(roomId).size})`);
    }
  }
}

function broadcastToRoom(roomId, message, excludeConnectionId = null) {
  if (!rooms.has(roomId)) {
    return;
  }
  
  let sentCount = 0;
  rooms.get(roomId).forEach(connId => {
    if (connId !== excludeConnectionId) {
      const conn = connections.get(connId);
      if (conn && conn.ws.readyState === WebSocket.OPEN) {
        conn.ws.send(message);
        sentCount++;
      }
    }
  });
  
  return sentCount;
}

wss.on('connection', (ws, req) => {
  const connectionId = Math.random().toString(36).substring(7);
  
  // Initialize connection metadata
  connections.set(connectionId, {
    ws: ws,
    roomId: null,
    streamId: null,
    UUID: null
  });
  
  log(`New connection: ${connectionId} (total: ${connections.size})`);
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      const conn = connections.get(connectionId);
      
      // Handle joinroom request
      if (data.request === 'joinroom' && data.roomid) {
        const roomId = data.roomid;
        
        // Remove from old room if exists
        if (conn.roomId) {
          removeFromRoom(conn.roomId, connectionId);
        }
        
        // Update connection metadata
        conn.roomId = roomId;
        conn.streamId = data.streamid || null;
        conn.UUID = data.UUID || null;
        
        // Add to new room
        addToRoom(roomId, connectionId);
        
        log(`Connection ${connectionId} joined room ${roomId}`, {
          streamId: conn.streamId,
          UUID: conn.UUID
        });
        
        // Broadcast join to other room members
        const sentCount = broadcastToRoom(roomId, message, connectionId);
        log(`Broadcasted joinroom to ${sentCount} peers in room ${roomId}`);
      }
      // Handle other signaling messages (offer, answer, candidate, etc.)
      else if (conn.roomId) {
        // Update UUID if present
        if (data.UUID) {
          conn.UUID = data.UUID;
        }
        
        // Broadcast to room members
        const sentCount = broadcastToRoom(conn.roomId, message, connectionId);
        
        if (data.description) {
          log(`Relayed ${data.description.type} from ${connectionId} to ${sentCount} peers in room ${conn.roomId}`);
        } else if (data.candidate) {
          log(`Relayed ICE candidate from ${connectionId} to ${sentCount} peers in room ${conn.roomId}`);
        } else {
          log(`Relayed message from ${connectionId} to ${sentCount} peers in room ${conn.roomId}`, {
            messageType: data.request || data.type || 'unknown'
          });
        }
      } else {
        log(`Message from ${connectionId} without room assignment, ignoring`, {
          hasRequest: !!data.request,
          hasUUID: !!data.UUID
        });
      }
    } catch (err) {
      console.error(`[${new Date().toISOString()}] Error processing message from ${connectionId}:`, err);
    }
  });
  
  ws.on('close', () => {
    const conn = connections.get(connectionId);
    
    // Remove from room
    if (conn && conn.roomId) {
      removeFromRoom(conn.roomId, connectionId);
    }
    
    connections.delete(connectionId);
    log(`Connection closed: ${connectionId} (total: ${connections.size})`);
  });
  
  ws.on('error', (error) => {
    console.error(`[${new Date().toISOString()}] WebSocket error for ${connectionId}:`, error);
    
    const conn = connections.get(connectionId);
    if (conn && conn.roomId) {
      removeFromRoom(conn.roomId, connectionId);
    }
    
    connections.delete(connectionId);
  });
});

// Start server
server.listen(HTTPS_PORT, '0.0.0.0', () => {
  log('VDO.Ninja server started with room-based signaling');
  console.log(`  - HTTPS/WebSocket: https://0.0.0.0:${HTTPS_PORT}`);
  console.log(`  - Serving static files from: ${VDO_NINJA_PATH}`);
  console.log(`  - SSL certificates: ${__dirname}/key.pem, ${__dirname}/cert.pem`);
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

