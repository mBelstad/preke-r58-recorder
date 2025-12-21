const WebSocket = require('ws');
const http = require('http');

const PORT = process.env.PORT || 8080;

// Create HTTP server for health checks
const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      status: 'ok', 
      service: 'r58-relay',
      units: units.size,
      controllers: Array.from(controllers.values()).reduce((sum, arr) => sum + arr.length, 0)
    }));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

// Create WebSocket server
const wss = new WebSocket.Server({ server });

// Store connections
const units = new Map();       // unit-id -> R58 WebSocket
const controllers = new Map(); // unit-id -> [Controller WebSockets]

wss.on('connection', (ws, req) => {
  const path = req.url;
  console.log(`[${new Date().toISOString()}] New connection: ${path}`);
  
  // R58 unit connecting
  if (path.startsWith('/unit/')) {
    const unitId = path.split('/')[2];
    
    // Close existing connection if any
    if (units.has(unitId)) {
      console.log(`[${unitId}] Closing existing connection`);
      units.get(unitId).close();
    }
    
    units.set(unitId, ws);
    console.log(`[${unitId}] R58 unit connected. Total units: ${units.size}`);
    
    // Forward messages from R58 to controllers
    ws.on('message', (data) => {
      const ctrls = controllers.get(unitId) || [];
      console.log(`[${unitId}] Message from R58 -> ${ctrls.length} controllers`);
      ctrls.forEach(ctrl => {
        if (ctrl.readyState === WebSocket.OPEN) {
          ctrl.send(data);
        }
      });
    });
    
    ws.on('close', () => {
      units.delete(unitId);
      console.log(`[${unitId}] R58 unit disconnected. Total units: ${units.size}`);
    });
    
    ws.on('error', (error) => {
      console.error(`[${unitId}] R58 WebSocket error:`, error.message);
    });
    
  } 
  // Remote controller connecting
  else if (path.startsWith('/control/')) {
    const unitId = path.split('/')[2];
    
    if (!controllers.has(unitId)) {
      controllers.set(unitId, []);
    }
    controllers.get(unitId).push(ws);
    
    const ctrlCount = controllers.get(unitId).length;
    console.log(`[${unitId}] Controller connected. Total controllers: ${ctrlCount}`);
    
    // Forward messages from controller to R58
    ws.on('message', (data) => {
      const unit = units.get(unitId);
      if (unit && unit.readyState === WebSocket.OPEN) {
        console.log(`[${unitId}] Message from controller -> R58`);
        unit.send(data);
      } else {
        console.log(`[${unitId}] Controller message dropped: R58 not connected`);
        ws.send(JSON.stringify({ 
          error: 'R58 unit not connected',
          unitId 
        }));
      }
    });
    
    ws.on('close', () => {
      const ctrls = controllers.get(unitId) || [];
      const idx = ctrls.indexOf(ws);
      if (idx > -1) {
        ctrls.splice(idx, 1);
      }
      if (ctrls.length === 0) {
        controllers.delete(unitId);
      }
      console.log(`[${unitId}] Controller disconnected. Remaining: ${ctrls.length}`);
    });
    
    ws.on('error', (error) => {
      console.error(`[${unitId}] Controller WebSocket error:`, error.message);
    });
    
  } else {
    console.log(`Invalid path: ${path}`);
    ws.close(1008, 'Invalid path. Use /unit/{id} or /control/{id}');
  }
});

// Start server
server.listen(PORT, () => {
  console.log(`R58 Relay Server listening on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`WebSocket endpoints:`);
  console.log(`  - R58 units: ws://localhost:${PORT}/unit/{unit-id}`);
  console.log(`  - Controllers: ws://localhost:${PORT}/control/{unit-id}`);
});

// Cleanup on exit
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing connections...');
  wss.close(() => {
    process.exit(0);
  });
});

