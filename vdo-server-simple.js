//
// Official VDO.Ninja Websocket Server (simplified)
// Based on https://github.com/steveseguin/websocket_server
//
// This is the SIMPLE broadcast-all version that VDO.ninja expects
//

"use strict";
const fs = require("fs");
const https = require("https");
const express = require("express");
const path = require("path");
const WebSocket = require("ws");

const app = express();

// SSL certificates
const SSL_KEY = "/opt/vdo-signaling/ssl/key.pem";
const SSL_CERT = "/opt/vdo-signaling/ssl/cert.pem";

let key, cert;
try {
    key = fs.readFileSync(SSL_KEY);
    cert = fs.readFileSync(SSL_CERT);
} catch (err) {
    console.error("Failed to load SSL certificates:", err.message);
    process.exit(1);
}

// Serve static VDO.ninja files
app.use(express.static('/opt/vdo.ninja'));

const server = https.createServer({ key, cert }, app);
const wss = new WebSocket.Server({ server });

// Connection tracking for logging
let connectionCount = 0;

function log(msg) {
    console.log(`[${new Date().toISOString()}] ${msg}`);
}

wss.on('connection', (ws, req) => {
    connectionCount++;
    const clientIP = req.socket.remoteAddress;
    log(`New connection from ${clientIP} (total: ${wss.clients.size})`);

    ws.on('message', (message) => {
        // Simple broadcast to ALL other connected clients
        // This is how the official VDO.ninja websocket server works
        wss.clients.forEach(client => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message.toString());
            }
        });
    });

    ws.on('close', () => {
        log(`Connection closed (remaining: ${wss.clients.size})`);
    });

    ws.on('error', (err) => {
        log(`WebSocket error: ${err.message}`);
    });
});

const PORT = 8443;
server.listen(PORT, () => {
    log(`VDO.Ninja Simple Websocket Server running on port ${PORT}`);
    log(`Static files served from /opt/vdo.ninja`);
    log(`This server broadcasts ALL messages to ALL clients (official behavior)`);
});

