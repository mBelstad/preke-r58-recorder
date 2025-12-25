/**
 * VDO.Ninja Signaling Server - Universal Room Handler
 * 
 * This server handles room-based signaling for VDO.ninja with support for:
 * - Multiple hash variants (browser hash, salted hash, plain room name)
 * - Publisher discovery (new viewers see existing publishers)
 * - SDP offer/answer relay
 * - ICE candidate relay
 * 
 * Room Normalization:
 * - All room names/hashes are normalized to a common canonical name
 * - This allows publishers with --salt to work with browsers without salt
 */

const https = require("https");
const express = require("express");
const WebSocket = require("ws");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

// Configuration
const HTTPS_PORT = 8443;
const VDO_NINJA_PATH = "/opt/vdo.ninja";

// Room configuration
// All these hashes map to the canonical room "r58studio"
const CANONICAL_ROOM = "r58studio";
const KNOWN_ROOM_HASHES = new Set([
    "r58studio",           // Plain room name
    "61692853ab4b7505",    // VDO.ninja hash of "r58studio"
    "d2869f4ba7cc9ad6",    // Browser hash variant
    "8e27706569be0e92",    // Hash with salt=192.168.1.24
]);

// SSL Certificates
const serverOptions = {
    key: fs.readFileSync(path.join(__dirname, "key.pem")),
    cert: fs.readFileSync(path.join(__dirname, "cert.pem"))
};

// Create Express app
const app = express();
app.use(express.static(VDO_NINJA_PATH));

// Create HTTPS server
const server = https.createServer(serverOptions, app);

// Create WebSocket server
const wss = new WebSocket.Server({ server });

// Connection storage
// connections: Map<connId, { ws, streamId, UUID, isPublisher, roomId }>
const connections = new Map();

// Publisher registry for quick lookup
// publishers: Map<streamId, connId>
const publishers = new Map();

function log(msg, data = null) {
    const ts = new Date().toISOString();
    if (data) {
        console.log(`[${ts}] ${msg}`, typeof data === 'string' ? data : JSON.stringify(data).substring(0, 200));
    } else {
        console.log(`[${ts}] ${msg}`);
    }
}

/**
 * Normalize room ID to canonical name
 * This allows different clients using different hash variants to join the same room
 */
function normalizeRoomId(roomId) {
    if (!roomId) return CANONICAL_ROOM;
    
    // Check if it's a known hash
    if (KNOWN_ROOM_HASHES.has(roomId)) {
        return CANONICAL_ROOM;
    }
    
    // If it contains "r58" or "studio", treat as our room
    if (roomId.toLowerCase().includes('r58') || roomId.toLowerCase().includes('studio')) {
        return CANONICAL_ROOM;
    }
    
    // Return as-is for unknown rooms (allows other rooms to work)
    return roomId;
}

/**
 * Check if a stream ID indicates a publisher (our camera streams)
 */
function isPublisherStreamId(streamId) {
    if (!streamId) return false;
    return streamId.startsWith('r58-cam') || streamId.startsWith('r58-');
}

/**
 * Broadcast message to all connections in a room, optionally excluding sender
 */
function broadcastToRoom(roomId, message, excludeConnId = null) {
    const normalizedRoom = normalizeRoomId(roomId);
    let count = 0;
    
    connections.forEach((conn, connId) => {
        if (connId !== excludeConnId && 
            conn.roomId === normalizedRoom && 
            conn.ws.readyState === WebSocket.OPEN) {
            try {
                conn.ws.send(message);
                count++;
            } catch (err) {
                log(`Error sending to ${connId}:`, err.message);
            }
        }
    });
    
    return count;
}

/**
 * Send message to a specific UUID
 */
function sendToUUID(uuid, message) {
    for (const [connId, conn] of connections.entries()) {
        if (conn.UUID === uuid && conn.ws.readyState === WebSocket.OPEN) {
            try {
                conn.ws.send(message);
                return true;
            } catch (err) {
                log(`Error sending to UUID ${uuid}:`, err.message);
            }
        }
    }
    return false;
}

/**
 * Notify a new viewer about existing publishers
 */
function notifyViewerOfPublishers(viewerConnId, viewerRoomId) {
    const normalizedRoom = normalizeRoomId(viewerRoomId);
    const viewerConn = connections.get(viewerConnId);
    if (!viewerConn) return;
    
    connections.forEach((conn, connId) => {
        if (connId !== viewerConnId && 
            conn.isPublisher && 
            conn.streamId && 
            conn.roomId === normalizedRoom) {
            try {
                // Send publisher info to new viewer
                const publisherInfo = {
                    request: "joinroom",
                    roomid: viewerRoomId, // Use viewer's original room format
                    streamID: conn.streamId,
                    UUID: conn.UUID
                };
                viewerConn.ws.send(JSON.stringify(publisherInfo));
                log(`Notified viewer ${viewerConnId} about publisher: ${conn.streamId}`);
            } catch (err) {
                log(`Error notifying viewer:`, err.message);
            }
        }
    });
}

// WebSocket connection handler
wss.on("connection", (ws, req) => {
    const connId = crypto.randomBytes(4).toString('hex');
    
    // Initialize connection metadata
    connections.set(connId, {
        ws,
        streamId: null,
        UUID: null,
        isPublisher: false,
        roomId: null
    });
    
    log(`New connection: ${connId} (total: ${connections.size})`);
    
    ws.on("message", (message) => {
        try {
            const data = JSON.parse(message.toString());
            const conn = connections.get(connId);
            if (!conn) return;
            
            const streamId = data.streamID || data.streamid;
            const roomId = data.roomid || data.roomId;
            
            // Handle different message types
            switch (data.request) {
                case "joinroom": {
                    const normalizedRoom = normalizeRoomId(roomId);
                    const isPublisher = isPublisherStreamId(streamId);
                    
                    // Update connection metadata
                    conn.streamId = streamId || conn.streamId;
                    conn.UUID = data.UUID || conn.UUID;
                    conn.isPublisher = isPublisher;
                    conn.roomId = normalizedRoom;
                    
                    // Register publisher
                    if (isPublisher && streamId) {
                        publishers.set(streamId, connId);
                    }
                    
                    log(`${isPublisher ? 'Publisher' : 'Viewer'} joined room ${normalizedRoom}: ${streamId || 'director'}`, 
                        { uuid: conn.UUID?.substring(0, 8) });
                    
                    // Normalize roomid in message before broadcasting
                    const broadcastMsg = JSON.stringify({
                        ...data,
                        roomid: normalizedRoom
                    });
                    
                    const count = broadcastToRoom(normalizedRoom, broadcastMsg, connId);
                    log(`Broadcasted joinroom to ${count} peers`);
                    
                    // Notify new viewer about existing publishers
                    if (!isPublisher) {
                        notifyViewerOfPublishers(connId, roomId);
                    }
                    break;
                }
                
                case "seed": {
                    // Publisher announcing availability
                    conn.streamId = streamId || conn.streamId;
                    conn.UUID = data.UUID || conn.UUID;
                    conn.isPublisher = true;
                    
                    if (conn.streamId) {
                        publishers.set(conn.streamId, connId);
                    }
                    
                    log(`Publisher seeding: ${conn.streamId}`);
                    
                    // Broadcast seed to all in room
                    const count = broadcastToRoom(conn.roomId, message.toString(), connId);
                    log(`Broadcasted seed to ${count} peers`);
                    break;
                }
                
                case "play": {
                    // Viewer requesting to play a stream
                    log(`Play request for: ${streamId}`);
                    broadcastToRoom(conn.roomId, message.toString(), connId);
                    break;
                }
                
                default: {
                    // Handle SDP descriptions, ICE candidates, and other messages
                    if (data.description || data.candidate || data.candidates) {
                        // If UUID specified, try direct delivery first
                        if (data.UUID) {
                            const delivered = sendToUUID(data.UUID, message.toString());
                            if (!delivered) {
                                // Fallback to room broadcast
                                broadcastToRoom(conn.roomId, message.toString(), connId);
                            }
                        } else {
                            broadcastToRoom(conn.roomId, message.toString(), connId);
                        }
                    } else {
                        // Unknown message type, broadcast to room
                        broadcastToRoom(conn.roomId, message.toString(), connId);
                    }
                }
            }
        } catch (err) {
            log(`Error processing message from ${connId}:`, err.message);
        }
    });
    
    ws.on("close", () => {
        const conn = connections.get(connId);
        
        // Clean up publisher registry
        if (conn && conn.streamId) {
            publishers.delete(conn.streamId);
        }
        
        connections.delete(connId);
        log(`Connection closed: ${connId} (total: ${connections.size})`);
    });
    
    ws.on("error", (err) => {
        log(`WebSocket error for ${connId}:`, err.message);
        
        const conn = connections.get(connId);
        if (conn && conn.streamId) {
            publishers.delete(conn.streamId);
        }
        connections.delete(connId);
    });
});

// Start server
server.listen(HTTPS_PORT, "0.0.0.0", () => {
    log("VDO.Ninja Universal Signaling Server started");
    console.log(`  HTTPS/WebSocket: https://0.0.0.0:${HTTPS_PORT}`);
    console.log(`  Serving static files from: ${VDO_NINJA_PATH}`);
    console.log(`  Canonical room: ${CANONICAL_ROOM}`);
    console.log(`  Known room hashes: ${Array.from(KNOWN_ROOM_HASHES).join(', ')}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    log('SIGTERM received, closing server...');
    wss.clients.forEach(client => {
        client.close();
    });
    server.close(() => {
        log('Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    log('SIGINT received, closing server...');
    wss.clients.forEach(client => {
        client.close();
    });
    server.close(() => {
        log('Server closed');
        process.exit(0);
    });
});

