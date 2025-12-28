"""R58 Pipeline Manager - Entry point"""
import asyncio
import json
import signal
import sys
from pathlib import Path

from .state import PipelineState
from .ipc import IPCServer


async def main():
    """Main entry point for pipeline manager"""
    print("[Pipeline Manager] Starting...")
    
    # Load or create state
    state = PipelineState.load()
    print(f"[Pipeline Manager] Loaded state: {state.current_mode}")
    
    # Create IPC server
    ipc_server = IPCServer(state)
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def shutdown_handler():
        print("[Pipeline Manager] Shutting down...")
        ipc_server.stop()
        state.save()
        sys.exit(0)
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)
    
    # Start IPC server
    await ipc_server.start()
    
    print("[Pipeline Manager] Ready and listening on socket")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        shutdown_handler()


if __name__ == "__main__":
    asyncio.run(main())

