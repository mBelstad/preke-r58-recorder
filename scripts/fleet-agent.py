#!/usr/bin/env python3
"""
R58 Fleet Management Agent

This agent runs on R58 devices and communicates with the fleet management server.
It handles:
- Periodic heartbeats with device metrics
- Polling and executing remote commands
- Generating and uploading support bundles
- Automatic updates when requested

Configuration: /opt/r58-app/shared/config/fleet.conf
"""
import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
    import psutil
except ImportError:
    print("Required packages not installed. Run: pip install httpx psutil")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/var/log/r58-fleet-agent.log", mode="a"),
    ]
)
logger = logging.getLogger("fleet-agent")


class FleetAgentConfig:
    """Configuration for the fleet agent"""
    
    def __init__(self, config_path: str = "/opt/r58-app/shared/config/fleet.conf"):
        self.config_path = Path(config_path)
        self._config: Dict[str, str] = {}
        self._load()
    
    def _load(self):
        """Load configuration from file"""
        if self.config_path.exists():
            for line in self.config_path.read_text().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    self._config[key.strip()] = value.strip().strip('"\'')
        else:
            logger.warning(f"Config file not found: {self.config_path}")
    
    @property
    def enabled(self) -> bool:
        return self._config.get("FLEET_ENABLED", "false").lower() == "true"
    
    @property
    def fleet_url(self) -> str:
        return self._config.get("FLEET_URL", "https://fleet.r58.itagenten.no")
    
    @property
    def device_id(self) -> str:
        return self._config.get("DEVICE_ID", f"r58-{platform.node()}")
    
    @property
    def device_token(self) -> str:
        token = self._config.get("DEVICE_TOKEN", "")
        if not token:
            logger.error("DEVICE_TOKEN not configured!")
        return token
    
    @property
    def heartbeat_interval(self) -> int:
        return int(self._config.get("HEARTBEAT_INTERVAL", "60"))
    
    @property
    def command_poll_interval(self) -> int:
        return int(self._config.get("COMMAND_POLL_INTERVAL", "30"))


class FleetAgent:
    """R58 Fleet Management Agent"""
    
    def __init__(self, config: FleetAgentConfig):
        self.config = config
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with device token"""
        return {
            "X-Device-Token": self.config.device_token,
            "Content-Type": "application/json",
            "User-Agent": f"R58-Fleet-Agent/{self._get_version()}",
        }
    
    def _get_version(self) -> str:
        """Get current R58 version"""
        manifest_path = Path("/opt/r58-app/current/manifest.json")
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text())
                return data.get("version", "unknown")
            except Exception:
                pass
        return "unknown"
    
    def _get_temperature(self) -> Optional[float]:
        """Get CPU temperature if available"""
        # Try Linux thermal zone
        try:
            temp_file = Path("/sys/class/thermal/thermal_zone0/temp")
            if temp_file.exists():
                temp = int(temp_file.read_text().strip()) / 1000.0
                return round(temp, 1)
        except Exception:
            pass
        
        # Try psutil
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return round(entries[0].current, 1)
        except Exception:
            pass
        
        return None
    
    async def _get_app_status(self) -> Dict[str, Any]:
        """Get R58 application status from local API"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Check recorder status
                resp = await client.get("http://localhost:8000/api/v1/sessions/status")
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "recording_active": data.get("status") == "recording",
                        "mixer_active": True,  # Assume mixer is part of normal operation
                        "active_inputs": data.get("active_inputs", []),
                        "degradation_level": data.get("degradation_level", 0),
                    }
        except Exception as e:
            logger.debug(f"Could not get app status: {e}")
        
        return {
            "recording_active": False,
            "mixer_active": False,
            "active_inputs": [],
            "degradation_level": 0,
        }
    
    async def send_heartbeat(self) -> Optional[Dict[str, Any]]:
        """Send heartbeat to fleet server"""
        try:
            disk = psutil.disk_usage("/")
            mem = psutil.virtual_memory()
            load = psutil.getloadavg()
            
            app_status = await self._get_app_status()
            
            payload = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "version": self._get_version(),
                "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time()),
                "metrics": {
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "mem_percent": mem.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                    "disk_total_gb": round(disk.total / (1024**3), 2),
                    "temperature_c": self._get_temperature(),
                    "load_avg": list(load),
                },
                "status": app_status,
                "errors": [],
            }
            
            resp = await self._client.post(
                f"{self.config.fleet_url}/api/v1/devices/{self.config.device_id}/heartbeat",
                json=payload,
                headers=self._headers(),
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data.get("commands_pending", 0) > 0:
                    logger.info(f"Commands pending: {data['commands_pending']}")
                
                if data.get("target_version"):
                    logger.info(f"Update available: {data['target_version']}")
                
                return data
            else:
                logger.warning(f"Heartbeat failed: {resp.status_code} {resp.text}")
                
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
        
        return None
    
    async def poll_commands(self) -> List[Dict[str, Any]]:
        """Poll for pending commands"""
        try:
            resp = await self._client.get(
                f"{self.config.fleet_url}/api/v1/devices/{self.config.device_id}/commands",
                params={"status": "pending"},
                headers=self._headers(),
            )
            
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Command poll failed: {resp.status_code}")
                
        except Exception as e:
            logger.error(f"Command poll error: {e}")
        
        return []
    
    async def update_command_status(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """Update command status on fleet server"""
        try:
            payload = {"status": status}
            if result:
                payload["result"] = result
            if error:
                payload["error"] = error
            
            resp = await self._client.patch(
                f"{self.config.fleet_url}/api/v1/commands/{command_id}",
                json=payload,
                headers=self._headers(),
            )
            
            if resp.status_code != 200:
                logger.warning(f"Failed to update command {command_id}: {resp.status_code}")
                
        except Exception as e:
            logger.error(f"Command update error: {e}")
    
    async def execute_command(self, command: Dict[str, Any]):
        """Execute a command from fleet server"""
        cmd_id = command["id"]
        cmd_type = command["type"]
        payload = command.get("payload", {})
        
        logger.info(f"Executing command {cmd_id}: {cmd_type}")
        
        # Acknowledge command
        await self.update_command_status(cmd_id, "acked")
        
        try:
            if cmd_type == "update":
                result = await self._do_update(payload)
            elif cmd_type == "reboot":
                result = await self._do_reboot(payload)
            elif cmd_type == "restart_service":
                result = await self._do_restart_service(payload)
            elif cmd_type == "bundle":
                result = await self._do_bundle(payload)
            elif cmd_type == "config":
                result = await self._do_config(payload)
            elif cmd_type == "custom":
                result = await self._do_custom(payload)
            else:
                raise ValueError(f"Unknown command type: {cmd_type}")
            
            await self.update_command_status(cmd_id, "completed", result=result)
            logger.info(f"Command {cmd_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Command {cmd_id} failed: {e}")
            await self.update_command_status(cmd_id, "failed", error=str(e))
    
    async def _do_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute update command"""
        version = payload.get("version")
        force = payload.get("force", False)
        
        if not version:
            raise ValueError("No version specified")
        
        old_version = self._get_version()
        
        # Run deploy script
        result = subprocess.run(
            ["/opt/r58-app/scripts/deploy.sh", version],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Deploy failed: {result.stderr}")
        
        return {
            "old_version": old_version,
            "new_version": version,
            "output": result.stdout[-1000:],  # Last 1000 chars
        }
    
    async def _do_reboot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute reboot command"""
        delay = payload.get("delay_seconds", 5)
        
        logger.warning(f"Rebooting device in {delay} seconds...")
        
        # Schedule reboot
        subprocess.Popen(
            ["sudo", "shutdown", "-r", f"+{delay // 60 or 1}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        return {"scheduled": True, "delay_seconds": delay}
    
    async def _do_restart_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Restart a systemd service"""
        service = payload.get("service", "r58-api")
        
        # Whitelist of allowed services
        allowed = ["r58-api", "r58-fleet-agent", "mediamtx", "vdoninja"]
        if service not in allowed:
            raise ValueError(f"Service {service} not in allowed list")
        
        result = subprocess.run(
            ["sudo", "systemctl", "restart", service],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        return {
            "service": service,
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr,
        }
    
    async def _do_bundle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create and upload support bundle"""
        bundle_id = payload.get("bundle_id")
        include_logs = payload.get("include_logs", True)
        include_config = payload.get("include_config", True)
        include_recordings = payload.get("include_recordings", False)
        
        if not bundle_id:
            raise ValueError("No bundle_id specified")
        
        # Create temporary bundle
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = Path(tmpdir) / "bundle"
            bundle_dir.mkdir()
            
            # Collect files
            if include_logs:
                log_dir = bundle_dir / "logs"
                log_dir.mkdir()
                
                # System logs
                subprocess.run(
                    ["journalctl", "-u", "r58-api", "--since", "24 hours ago", "-o", "cat"],
                    stdout=open(log_dir / "r58-api.log", "w"),
                    stderr=subprocess.DEVNULL,
                )
                
                # Application logs
                app_logs = Path("/opt/r58-app/shared/logs")
                if app_logs.exists():
                    for log_file in list(app_logs.glob("*.log"))[:10]:
                        shutil.copy(log_file, log_dir)
            
            if include_config:
                config_dir = bundle_dir / "config"
                config_dir.mkdir()
                
                # Copy configs (redact sensitive values)
                config_files = [
                    "/opt/r58-app/shared/config/r58.env",
                    "/opt/r58-app/current/manifest.json",
                ]
                for cf in config_files:
                    if Path(cf).exists():
                        content = Path(cf).read_text()
                        # Redact secrets
                        for secret in ["JWT_SECRET", "DEVICE_TOKEN", "PASSWORD"]:
                            import re
                            content = re.sub(
                                f"{secret}=.*",
                                f"{secret}=REDACTED",
                                content,
                            )
                        (config_dir / Path(cf).name).write_text(content)
            
            # Add system info
            (bundle_dir / "system_info.json").write_text(json.dumps({
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_total_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
                "r58_version": self._get_version(),
                "collected_at": datetime.utcnow().isoformat(),
            }, indent=2))
            
            # Create tarball
            bundle_path = Path(tmpdir) / f"bundle-{bundle_id[:8]}.tar.gz"
            with tarfile.open(bundle_path, "w:gz") as tar:
                tar.add(bundle_dir, arcname="bundle")
            
            # Upload
            with open(bundle_path, "rb") as f:
                resp = await self._client.post(
                    f"{self.config.fleet_url}/api/v1/devices/{self.config.device_id}/bundles/upload",
                    params={"bundle_id": bundle_id},
                    files={"bundle": f},
                    headers={"X-Device-Token": self.config.device_token},
                    timeout=120,
                )
                
                if resp.status_code != 200:
                    raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")
            
            size = bundle_path.stat().st_size
            
        return {"bundle_id": bundle_id, "size_bytes": size}
    
    async def _do_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update device configuration"""
        changes = payload.get("changes", {})
        
        if not changes:
            return {"message": "No changes specified"}
        
        # Only allow certain config keys to be updated remotely
        allowed_keys = [
            "HEARTBEAT_INTERVAL",
            "COMMAND_POLL_INTERVAL",
            "R58_DEBUG",
        ]
        
        config_path = Path("/opt/r58-app/shared/config/fleet.conf")
        if not config_path.exists():
            raise ValueError("Config file not found")
        
        content = config_path.read_text()
        applied = []
        
        for key, value in changes.items():
            if key not in allowed_keys:
                logger.warning(f"Ignoring disallowed config key: {key}")
                continue
            
            # Update or append
            import re
            if re.search(f"^{key}=", content, re.MULTILINE):
                content = re.sub(f"^{key}=.*$", f"{key}={value}", content, flags=re.MULTILINE)
            else:
                content += f"\n{key}={value}\n"
            
            applied.append(key)
        
        config_path.write_text(content)
        
        return {"applied": applied}
    
    async def _do_custom(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a custom script"""
        script = payload.get("script")
        
        if not script:
            raise ValueError("No script specified")
        
        # Only allow scripts in the approved directory
        allowed_dir = Path("/opt/r58-app/scripts/custom")
        script_path = allowed_dir / script
        
        if not script_path.exists() or not script_path.is_file():
            raise ValueError(f"Script not found: {script}")
        
        if not str(script_path.resolve()).startswith(str(allowed_dir)):
            raise ValueError("Script path escape attempt detected")
        
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/opt/r58-app",
        )
        
        return {
            "script": script,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-1000:],
        }
    
    async def _heartbeat_loop(self):
        """Heartbeat loop"""
        while self._running:
            await self.send_heartbeat()
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _command_loop(self):
        """Command polling loop"""
        while self._running:
            commands = await self.poll_commands()
            
            # Sort by priority (lower = higher priority)
            commands.sort(key=lambda c: c.get("priority", 5))
            
            for cmd in commands:
                await self.execute_command(cmd)
            
            await asyncio.sleep(self.config.command_poll_interval)
    
    async def run(self):
        """Main agent loop"""
        if not self.config.enabled:
            logger.warning("Fleet agent is disabled. Set FLEET_ENABLED=true to enable.")
            return
        
        if not self.config.device_token:
            logger.error("DEVICE_TOKEN not configured. Cannot start fleet agent.")
            return
        
        logger.info(f"Starting fleet agent for device: {self.config.device_id}")
        logger.info(f"Fleet server: {self.config.fleet_url}")
        
        self._running = True
        self._client = httpx.AsyncClient(timeout=30)
        
        try:
            # Run heartbeat and command loops concurrently
            await asyncio.gather(
                self._heartbeat_loop(),
                self._command_loop(),
            )
        except asyncio.CancelledError:
            logger.info("Fleet agent stopped")
        except Exception as e:
            logger.exception(f"Fleet agent error: {e}")
        finally:
            self._running = False
            await self._client.aclose()
    
    def stop(self):
        """Stop the agent"""
        self._running = False


async def main():
    """Main entry point"""
    config = FleetAgentConfig()
    agent = FleetAgent(config)
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        agent.stop()
        logger.info("Fleet agent interrupted")


if __name__ == "__main__":
    asyncio.run(main())

