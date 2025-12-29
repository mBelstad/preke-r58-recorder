"""R58 Pipeline Manager - Entry point"""
import asyncio
import logging
import signal
import sys

from .ipc import IPCServer
from .state import PipelineState

# Configure logging for all pipeline_manager modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for pipeline manager"""
    logger.info("Starting pipeline manager...")

    # Load or create state
    state = PipelineState.load()
    logger.info(f"Loaded state: mode={state.current_mode}")

    # Create IPC server
    ipc_server = IPCServer(state)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Shutting down...")
        ipc_server.stop()
        state.save()
        sys.exit(0)

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_handler)

    # Start IPC server
    await ipc_server.start()

    logger.info("Ready and listening on socket")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        shutdown_handler()


if __name__ == "__main__":
    asyncio.run(main())

