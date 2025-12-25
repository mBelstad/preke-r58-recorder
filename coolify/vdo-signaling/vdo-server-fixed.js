const https = require('https');
const express = require('express');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Configuration
const HTTPS_PORT = 8443;
const VDO_NINJA_PATH = '/opt/vdo.ninja';

// GLOBAL ROOM - all connections join this room to ensure compatibility
// between VDO.ninja browser and raspberry.ninja which use different room hashing
const GLOBAL_ROOM = '__global__';

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

// Store streamIDs: Map<streamId, connectionId>
const streamIds = new Map();

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
    return 0;
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

// Broadcast to all connections in the global room
function broadcastGlobal(message, excludeConnectionId = null) {
  return broadcastToRoom(GLOBAL_ROOM, message, excludeConnectionId);
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
  
  // Add all connections to the global room for compatibility
  addToRoom(GLOBAL_ROOM, connectionId);
  
  log(`New connection: ${connectionId} (total: ${connections.size})`);
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      const conn = connections.get(connectionId);
      const messageStr = typeof message === 'string' ? message : message.toString();
      
      // Handle joinroom request
      if (data.request === 'joinroom') {
        const roomId = data.roomid || GLOBAL_ROOM;
        
        // Update connection metadata
        conn.roomId = roomId;
        conn.streamId = data.streamID || data.streamid || null;
        conn.UUID = data.UUID || null;
        
        // Add to specific room (in addition to global room)
        if (roomId !== GLOBAL_ROOM) {
          addToRoom(roomId, connectionId);
        }
        
        // Track streamID
        if (conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
          log(`Registered streamID: ${conn.streamId}`);
        }
        
        log(`Connection ${connectionId} joined room ${roomId}`, {
          streamId: conn.streamId,
          UUID: conn.UUID
        });
        
        // Broadcast join to all in global room (for compatibility)
        const sentCount = broadcastGlobal(messageStr, connectionId);
        log(`Broadcasted joinroom to ${sentCount} peers`);
      }
      // Handle seed request (publisher announcing stream)
      else if (data.request === 'seed') {
        conn.streamId = data.streamID || data.streamid || conn.streamId;
        conn.UUID = data.UUID || conn.UUID;
        
        // Track streamID
        if (conn.streamId) {
          streamIds.set(conn.streamId, connectionId);
          log(`Publisher seeding: ${conn.streamId}`);
        }
        
        // Broadcast to all in global room
        const sentCount = broadcastGlobal(messageStr, connectionId);
        log(`Broadcasted seed to ${sentCount} peers`);
      }
      // Handle play request (viewer requesting stream)
      else if (data.request === 'play') {
        const targetStreamId = data.streamID || data.streamid;
        log(`Play request for streamID: ${targetStreamId}`);
        
        // Broadcast to all in global room
        const sentCount = broadcastGlobal(messageStr, connectionId);
        log(`Broadcasted play to ${sentCount} peers`);
      }
      // Handle targeted messages (with UUID)
      else if (data.UUID) {
        // Update UUID if present
        if (!conn.UUID) {
          conn.UUID = data.UUID;
        }
        
        // Broadcast to global room for now (works for local setup)
        const sentCount = broadcastGlobal(messageStr, connectionId);
        
        if (data.description) {
          log(`Relayed ${data.description.type} from ${connectionId} to ${sentCount} peers`);
        } else if (data.candidate) {
          log(`Relayed ICE candidate from ${connectionId} to ${sentCount} peers`);
        } else if (data.candidates) {
          log(`Relayed ${data.candidates.length} ICE candidates from ${connectionId} to ${sentCount} peers`);
        } else {
          log(`Relayed message from ${connectionId} to ${sentCount} peers`, {
            messageType: data.request || 'signaling'
          });
        }
      }
      // Handle other messages
      else {
        log(`Other message from ${connectionId}`, {
          request: data.request,
          hasDescription: !!data.description,
          hasCandidate: !!data.candidate
        });
        
        // Broadcast to global room
        const sentCount = broadcastGlobal(messageStr, connectionId);
        log(`Broadcasted to ${sentCount} peers`);
      }
    } catch (err) {
      console.error(`[${new Date().toISOString()}] Error processing message from ${connectionId}:`, err);
    }
  });
  
  ws.on('close', () => {
    const conn = connections.get(connectionId);
    
    // Remove from global room
    removeFromRoom(GLOBAL_ROOM, connectionId);
    
    // Remove from specific room
    if (conn && conn.roomId && conn.roomId !== GLOBAL_ROOM) {
      removeFromRoom(conn.roomId, connectionId);
    }
    
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
    if (conn) {
      removeFromRoom(GLOBAL_ROOM, connectionId);
      if (conn.roomId && conn.roomId !== GLOBAL_ROOM) {
        removeFromRoom(conn.roomId, connectionId);
      }
      if (conn.streamId) {
        streamIds.delete(conn.streamId);
      }
    }
    
    connections.delete(connectionId);
  });
});

// Start server
server.listen(HTTPS_PORT, '0.0.0.0', () => {
  log('VDO.Ninja server started with GLOBAL ROOM for cross-client compatibility');
  console.log(`  - HTTPS/WebSocket: https://0.0.0.0:${HTTPS_PORT}`);
  console.log(`  - Serving static files from: ${VDO_NINJA_PATH}`);
  console.log(`  - SSL certificates: ${__dirname}/key.pem, ${__dirname}/cert.pem`);
  console.log(`  - All connections join global room for VDO.ninja + raspberry.ninja compatibility`);
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


