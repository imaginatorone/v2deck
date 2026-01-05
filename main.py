import os
import json
import asyncio
import subprocess
import signal
import urllib.parse
import urllib.request
import socket
import zipfile
import re
import shutil
from typing import Optional, Dict, Any
import decky

PLUGIN_DIR = os.path.dirname(os.path.realpath(__file__))
BIN_DIR = os.path.join(PLUGIN_DIR, "bin")
XRAY_BIN = os.path.join(BIN_DIR, "xray")
TUN2SOCKS_BIN = os.path.join(BIN_DIR, "tun2socks")
CONFIG_DIR = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "profiles")
SETTINGS_FILE = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "settings.json")

XRAY_VERSION = "1.8.24"
TUN2SOCKS_VERSION = "2.5.2"
XRAY_URL = f"https://github.com/XTLS/Xray-core/releases/download/v{XRAY_VERSION}/Xray-linux-64.zip"
TUN2SOCKS_URL = f"https://github.com/xjasonlyu/tun2socks/releases/download/v{TUN2SOCKS_VERSION}/tun2socks-linux-amd64.zip"

DEFAULT_SETTINGS = {
    "mode": "tun",
    "socks_port": 10808,
    "http_port": 10809,
    "dns_port": 10853,
    "log_level": "warning",
    "domain_strategy": "IPIfNonMatch",
    "allow_insecure": False,
    "mux_enabled": False,
    "mux_concurrency": 8,
    "block_ads": True,
    "bypass_lan": True,
    "bypass_cn": False,
    "custom_dns": "1.1.1.1",
    "tun_mtu": 9000,
    "stack": "system"
}


class VLESSProfile:
    """Full VLESS profile with all transport options"""

    def __init__(self):
        self.name: str = ""
        self.uuid: str = ""
        self.address: str = ""
        self.port: int = 443
        self.encryption: str = "none"
        self.flow: str = ""

        self.network: str = "tcp"  # tcp, ws, grpc, http, quic, kcp, httpupgrade, splithttp
        self.security: str = "none"  # none, tls, reality

        self.sni: str = ""
        self.fingerprint: str = "chrome"
        self.alpn: str = ""

        self.public_key: str = ""
        self.short_id: str = ""
        self.spider_x: str = "/"

        self.allow_insecure: bool = False

        self.ws_path: str = "/"
        self.ws_host: str = ""

        self.grpc_service_name: str = ""
        self.grpc_mode: str = "gun"

        self.http_path: str = "/"
        self.http_host: str = ""

        self.quic_security: str = "none"
        self.quic_key: str = ""
        self.quic_header: str = "none"

        self.kcp_seed: str = ""
        self.kcp_header: str = "none"

        self.httpupgrade_path: str = "/"
        self.httpupgrade_host: str = ""

        self.splithttp_path: str = "/"
        self.splithttp_host: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VLESSProfile":
        profile = cls()
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        return profile

    @classmethod
    def from_uri(cls, uri: str) -> "VLESSProfile":
        """Parse VLESS URI: vless://uuid@address:port?params#name"""
        profile = cls()

        if not uri.startswith("vless://"):
            raise ValueError("Invalid VLESS URI")

        uri = uri[8:]

        if "#" in uri:
            uri, name = uri.rsplit("#", 1)
            profile.name = urllib.parse.unquote(name)

        if "?" in uri:
            uri, query = uri.split("?", 1)
            params = urllib.parse.parse_qs(query)

            profile.network = params.get("type", ["tcp"])[0]
            profile.security = params.get("security", ["none"])[0]
            profile.flow = params.get("flow", [""])[0]
            profile.encryption = params.get("encryption", ["none"])[0]

            profile.sni = params.get("sni", params.get("serverName", [""]))[0]
            profile.fingerprint = params.get("fp", ["chrome"])[0]
            profile.alpn = params.get("alpn", [""])[0]

            profile.public_key = params.get("pbk", [""])[0]
            profile.short_id = params.get("sid", [""])[0]
            profile.spider_x = urllib.parse.unquote(params.get("spx", ["/"])[0])

            profile.allow_insecure = params.get("allowInsecure", ["0"])[0] in ["1", "true"]

            profile.ws_path = urllib.parse.unquote(params.get("path", ["/"])[0])
            profile.ws_host = params.get("host", [""])[0]

            profile.grpc_service_name = params.get("serviceName", [""])[0]
            profile.grpc_mode = params.get("mode", ["gun"])[0]

            profile.http_path = urllib.parse.unquote(params.get("path", ["/"])[0])
            profile.http_host = params.get("host", [""])[0]

            profile.quic_security = params.get("quicSecurity", ["none"])[0]
            profile.quic_key = params.get("key", [""])[0]
            profile.quic_header = params.get("headerType", ["none"])[0]

            profile.kcp_seed = params.get("seed", [""])[0]
            profile.kcp_header = params.get("headerType", ["none"])[0]

            profile.httpupgrade_path = urllib.parse.unquote(params.get("path", ["/"])[0])
            profile.httpupgrade_host = params.get("host", [""])[0]
            profile.splithttp_path = urllib.parse.unquote(params.get("path", ["/"])[0])
            profile.splithttp_host = params.get("host", [""])[0]

        if "@" in uri:
            uuid, host = uri.split("@", 1)
            profile.uuid = uuid

            if host.startswith("["):
                match = re.match(r'\[([^\]]+)\]:(\d+)', host)
                if match:
                    profile.address = match.group(1)
                    profile.port = int(match.group(2))
            else:
                if ":" in host:
                    address, port = host.rsplit(":", 1)
                    profile.address = address
                    profile.port = int(port)

        if not profile.name:
            profile.name = f"{profile.address}:{profile.port}"

        return profile


def generate_xray_config(profile: VLESSProfile, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Generate xray-core config with full transport support"""

    user = {
        "id": profile.uuid,
        "encryption": profile.encryption
    }
    if profile.flow:
        user["flow"] = profile.flow

    outbound = {
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": profile.address,
                "port": profile.port,
                "users": [user]
            }]
        },
        "streamSettings": {
            "network": profile.network,
            "security": profile.security
        },
        "tag": "proxy"
    }

    stream = outbound["streamSettings"]

    if profile.security == "reality":
        stream["realitySettings"] = {
            "serverName": profile.sni,
            "fingerprint": profile.fingerprint,
            "publicKey": profile.public_key,
            "shortId": profile.short_id,
            "spiderX": profile.spider_x
        }
    elif profile.security == "tls":
        tls_settings = {
            "serverName": profile.sni,
            "fingerprint": profile.fingerprint,
            "allowInsecure": settings.get("allow_insecure", profile.allow_insecure)
        }
        if profile.alpn:
            tls_settings["alpn"] = profile.alpn.split(",")
        stream["tlsSettings"] = tls_settings

    if profile.network == "ws":
        ws_settings = {"path": profile.ws_path}
        if profile.ws_host:
            ws_settings["headers"] = {"Host": profile.ws_host}
        stream["wsSettings"] = ws_settings

    elif profile.network == "grpc":
        stream["grpcSettings"] = {
            "serviceName": profile.grpc_service_name,
            "multiMode": profile.grpc_mode == "multi"
        }

    elif profile.network == "http" or profile.network == "h2":
        http_settings = {"path": profile.http_path}
        if profile.http_host:
            http_settings["host"] = [profile.http_host]
        stream["httpSettings"] = http_settings

    elif profile.network == "quic":
        stream["quicSettings"] = {
            "security": profile.quic_security,
            "key": profile.quic_key,
            "header": {"type": profile.quic_header}
        }

    elif profile.network == "kcp":
        kcp_settings = {"header": {"type": profile.kcp_header}}
        if profile.kcp_seed:
            kcp_settings["seed"] = profile.kcp_seed
        stream["kcpSettings"] = kcp_settings

    elif profile.network == "httpupgrade":
        httpupgrade_settings = {"path": profile.httpupgrade_path}
        if profile.httpupgrade_host:
            httpupgrade_settings["host"] = profile.httpupgrade_host
        stream["httpupgradeSettings"] = httpupgrade_settings

    elif profile.network == "splithttp":
        splithttp_settings = {"path": profile.splithttp_path}
        if profile.splithttp_host:
            splithttp_settings["host"] = profile.splithttp_host
        stream["splithttpSettings"] = splithttp_settings

    if settings.get("mux_enabled", False):
        outbound["mux"] = {
            "enabled": True,
            "concurrency": settings.get("mux_concurrency", 8)
        }

    rules = []
    if settings.get("bypass_lan", True):
        rules.append({
            "type": "field",
            "ip": ["geoip:private"],
            "outboundTag": "direct"
        })
    if settings.get("block_ads", True):
        rules.append({
            "type": "field",
            "domain": ["geosite:category-ads-all"],
            "outboundTag": "block"
        })
    if settings.get("bypass_cn", False):
        rules.append({
            "type": "field",
            "domain": ["geosite:cn"],
            "outboundTag": "direct"
        })
        rules.append({
            "type": "field",
            "ip": ["geoip:cn"],
            "outboundTag": "direct"
        })

    config = {
        "log": {
            "loglevel": settings.get("log_level", "warning"),
            "access": os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "xray-access.log"),
            "error": os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "xray-error.log")
        },
        "dns": {
            "servers": [
                settings.get("custom_dns", "1.1.1.1"),
                "localhost"
            ]
        },
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": settings.get("socks_port", 10808),
                "protocol": "socks",
                "settings": {"udp": True},
                "tag": "socks-in"
            },
            {
                "listen": "127.0.0.1",
                "port": settings.get("http_port", 10809),
                "protocol": "http",
                "tag": "http-in"
            }
        ],
        "outbounds": [
            outbound,
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ],
        "routing": {
            "domainStrategy": settings.get("domain_strategy", "IPIfNonMatch"),
            "rules": rules
        }
    }

    return config


class Plugin:
    xray_process: Optional[subprocess.Popen] = None
    tun_process: Optional[subprocess.Popen] = None
    current_profile: Optional[VLESSProfile] = None
    is_connected: bool = False
    settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
    _original_route: str = ""

    async def _main(self):
        decky.logger.info("v2deck loaded")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(XRAY_BIN):
            os.chmod(XRAY_BIN, 0o755)
        await self._load_settings()

    async def _unload(self):
        await self.disconnect()

    async def _uninstall(self):
        await self.disconnect()

    async def _load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    saved = json.load(f)
                    self.settings = {**DEFAULT_SETTINGS, **saved}
        except Exception as e:
            decky.logger.error(f"Failed to load settings: {e}")

    async def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            decky.logger.error(f"Failed to save settings: {e}")

    # ============ Settings API ============

    async def get_settings(self) -> Dict[str, Any]:
        return {"success": True, "settings": self.settings}

    async def set_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.settings.update(new_settings)
            await self._save_settings()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def reset_settings(self) -> Dict[str, Any]:
        self.settings = DEFAULT_SETTINGS.copy()
        await self._save_settings()
        return {"success": True, "settings": self.settings}

    # ============ Profile Management ============

    async def parse_vless_uri(self, uri: str) -> Dict[str, Any]:
        try:
            profile = VLESSProfile.from_uri(uri)
            return {"success": True, "profile": profile.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def save_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            profile = VLESSProfile.from_dict(profile_data)
            filename = re.sub(r'[^\w\-_.]', '_', profile.name) + ".json"
            filepath = os.path.join(CONFIG_DIR, filename)
            with open(filepath, "w") as f:
                json.dump(profile.to_dict(), f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def load_profiles(self) -> Dict[str, Any]:
        try:
            profiles = []
            if os.path.exists(CONFIG_DIR):
                for f in os.listdir(CONFIG_DIR):
                    if f.endswith(".json"):
                        with open(os.path.join(CONFIG_DIR, f), "r") as file:
                            profiles.append(json.load(file))
            return {"success": True, "profiles": profiles}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_profile(self, name: str) -> Dict[str, Any]:
        try:
            filename = re.sub(r'[^\w\-_.]', '_', name) + ".json"
            filepath = os.path.join(CONFIG_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def import_from_uri(self, uri: str) -> Dict[str, Any]:
        result = await self.parse_vless_uri(uri)
        if result["success"]:
            return await self.save_profile(result["profile"])
        return result

    async def update_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing profile"""
        return await self.save_profile(profile_data)

    # ============ Connection ============

    async def connect(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.is_connected:
                await self.disconnect()

            profile = VLESSProfile.from_dict(profile_data)
            self.current_profile = profile

            config = generate_xray_config(profile, self.settings)
            config_path = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "xray-config.json")

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            if not os.path.exists(XRAY_BIN):
                return {"success": False, "error": "xray binary not found"}

            self.xray_process = subprocess.Popen(
                [XRAY_BIN, "run", "-config", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            await asyncio.sleep(1)
            if self.xray_process.poll() is not None:
                stderr = self.xray_process.stderr.read().decode() if self.xray_process.stderr else ""
                return {"success": False, "error": f"xray failed: {stderr[:200]}"}

            mode = self.settings.get("mode", "tun")
            if mode == "tun":
                result = await self._setup_tun()
                if not result["success"]:
                    await self.disconnect()
                    return result
            else:
                await self._setup_system_proxy()

            self.is_connected = True
            return {"success": True, "profile": profile.name, "mode": mode}

        except Exception as e:
            await self.disconnect()
            return {"success": False, "error": str(e)}

    async def disconnect(self) -> Dict[str, Any]:
        try:
            if self.tun_process:
                try:
                    os.killpg(os.getpgid(self.tun_process.pid), signal.SIGTERM)
                except:
                    pass
                self.tun_process = None

            await self._cleanup_tun()
            await self._cleanup_system_proxy()

            if self.xray_process:
                try:
                    os.killpg(os.getpgid(self.xray_process.pid), signal.SIGTERM)
                except:
                    pass
                self.xray_process = None

            self.is_connected = False
            self.current_profile = None
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "mode": self.settings.get("mode", "tun"),
            "profile": self.current_profile.to_dict() if self.current_profile else None
        }

    # ============ TUN ============

    async def _setup_tun(self) -> Dict[str, Any]:
        try:
            tun2socks_bin = os.path.join(PLUGIN_DIR, "bin", "tun2socks")
            if not os.path.exists(tun2socks_bin):
                return {"success": False, "error": "tun2socks not found"}

            os.chmod(tun2socks_bin, 0o755)

            subprocess.run(["ip", "tuntap", "add", "mode", "tun", "dev", "tun0"], check=True)
            subprocess.run(["ip", "addr", "add", "198.18.0.1/15", "dev", "tun0"], check=True)
            subprocess.run(["ip", "link", "set", "dev", "tun0", "up"], check=True)
            subprocess.run(["ip", "link", "set", "dev", "tun0", "mtu", str(self.settings.get("tun_mtu", 9000))], check=False)

            result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
            self._original_route = result.stdout.strip()

            server_ip = self.current_profile.address
            try:
                server_ip = socket.gethostbyname(self.current_profile.address)
            except:
                pass

            if self._original_route:
                match = re.search(r'via\s+([\d.]+)', self._original_route)
                if match:
                    gateway = match.group(1)
                    subprocess.run(["ip", "route", "add", f"{server_ip}/32", "via", gateway], check=False)

            socks_port = self.settings.get("socks_port", 10808)
            self.tun_process = subprocess.Popen(
                [tun2socks_bin, "-device", "tun0", "-proxy", f"socks5://127.0.0.1:{socks_port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            await asyncio.sleep(0.5)
            subprocess.run(["ip", "route", "add", "default", "dev", "tun0", "metric", "1"], check=True)

            return {"success": True}
        except Exception as e:
            await self._cleanup_tun()
            return {"success": False, "error": str(e)}

    async def _cleanup_tun(self) -> Dict[str, Any]:
        try:
            subprocess.run(["ip", "route", "del", "default", "dev", "tun0"], check=False, capture_output=True)
            if self.current_profile:
                try:
                    server_ip = socket.gethostbyname(self.current_profile.address)
                    subprocess.run(["ip", "route", "del", f"{server_ip}/32"], check=False, capture_output=True)
                except:
                    pass
            subprocess.run(["ip", "link", "set", "dev", "tun0", "down"], check=False, capture_output=True)
            subprocess.run(["ip", "tuntap", "del", "mode", "tun", "dev", "tun0"], check=False, capture_output=True)
            return {"success": True}
        except:
            return {"success": True}

    # ============ System Proxy ============

    async def _setup_system_proxy(self) -> Dict[str, Any]:
        try:
            http_port = self.settings.get("http_port", 10809)
            socks_port = self.settings.get("socks_port", 10808)

            proxy_file = "/etc/profile.d/v2deck_proxy.sh"
            content = f"""#!/bin/bash
export http_proxy="http://127.0.0.1:{http_port}"
export https_proxy="http://127.0.0.1:{http_port}"
export HTTP_PROXY="http://127.0.0.1:{http_port}"
export HTTPS_PROXY="http://127.0.0.1:{http_port}"
export all_proxy="socks5://127.0.0.1:{socks_port}"
export ALL_PROXY="socks5://127.0.0.1:{socks_port}"
"""
            with open(proxy_file, "w") as f:
                f.write(content)
            os.chmod(proxy_file, 0o644)
            return {"success": True}
        except:
            return {"success": True}

    async def _cleanup_system_proxy(self) -> Dict[str, Any]:
        try:
            proxy_file = "/etc/profile.d/v2deck_proxy.sh"
            if os.path.exists(proxy_file):
                os.remove(proxy_file)
            return {"success": True}
        except:
            return {"success": True}

    # ============ Utility ============

    async def test_connection(self) -> Dict[str, Any]:
        try:
            if not self.is_connected:
                return {"success": False, "error": "Not connected"}

            socks_port = self.settings.get("socks_port", 10808)
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "--proxy", f"socks5://127.0.0.1:{socks_port}",
                 "--connect-timeout", "10", "https://www.google.com"],
                capture_output=True, text=True
            )

            if result.stdout.strip() == "200":
                return {"success": True}
            return {"success": False, "error": f"HTTP {result.stdout.strip()}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_public_ip(self) -> Dict[str, Any]:
        try:
            socks_port = self.settings.get("socks_port", 10808)
            if self.is_connected:
                result = subprocess.run(
                    ["curl", "-s", "--proxy", f"socks5://127.0.0.1:{socks_port}",
                     "--connect-timeout", "10", "https://api.ipify.org?format=json"],
                    capture_output=True, text=True
                )
            else:
                result = subprocess.run(
                    ["curl", "-s", "--connect-timeout", "10", "https://api.ipify.org?format=json"],
                    capture_output=True, text=True
                )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {"success": True, "ip": data.get("ip", "Unknown")}
            return {"success": False, "error": "Failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_logs(self, lines: int = 50) -> Dict[str, Any]:
        """Get recent xray logs"""
        try:
            log_file = os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "xray-error.log")
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    all_lines = f.readlines()
                    return {"success": True, "logs": "".join(all_lines[-lines:])}
            return {"success": True, "logs": "No logs yet"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============ Dependencies Installation ============

    async def check_dependencies(self) -> Dict[str, Any]:
        """Check if xray and tun2socks are installed"""
        xray_installed = os.path.exists(XRAY_BIN) and os.access(XRAY_BIN, os.X_OK)
        tun2socks_installed = os.path.exists(TUN2SOCKS_BIN) and os.access(TUN2SOCKS_BIN, os.X_OK)

        return {
            "success": True,
            "xray_installed": xray_installed,
            "tun2socks_installed": tun2socks_installed,
            "all_installed": xray_installed and tun2socks_installed,
            "xray_version": XRAY_VERSION,
            "tun2socks_version": TUN2SOCKS_VERSION
        }

    async def install_dependencies(self) -> Dict[str, Any]:
        """Download and install xray-core and tun2socks"""
        try:
            os.makedirs(BIN_DIR, exist_ok=True)

            xray_result = await self._install_xray()
            if not xray_result["success"]:
                return xray_result

            tun2socks_result = await self._install_tun2socks()
            if not tun2socks_result["success"]:
                return tun2socks_result

            return {"success": True, "message": "All dependencies installed"}
        except Exception as e:
            decky.logger.error(f"Failed to install dependencies: {e}")
            return {"success": False, "error": str(e)}

    async def _install_xray(self) -> Dict[str, Any]:
        """Download and extract xray-core"""
        try:
            decky.logger.info(f"Downloading xray-core v{XRAY_VERSION}...")

            temp_dir = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "temp_xray")
            os.makedirs(temp_dir, exist_ok=True)

            zip_path = os.path.join(temp_dir, "xray.zip")

            urllib.request.urlretrieve(XRAY_URL, zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            xray_src = os.path.join(temp_dir, "xray")
            shutil.copy2(xray_src, XRAY_BIN)
            os.chmod(XRAY_BIN, 0o755)

            for dat_file in ["geoip.dat", "geosite.dat"]:
                dat_src = os.path.join(temp_dir, dat_file)
                if os.path.exists(dat_src):
                    shutil.copy2(dat_src, os.path.join(BIN_DIR, dat_file))

            shutil.rmtree(temp_dir, ignore_errors=True)

            decky.logger.info("xray-core installed successfully")
            return {"success": True}
        except Exception as e:
            decky.logger.error(f"Failed to install xray: {e}")
            return {"success": False, "error": f"Failed to install xray: {e}"}

    async def _install_tun2socks(self) -> Dict[str, Any]:
        """Download and extract tun2socks"""
        try:
            decky.logger.info(f"Downloading tun2socks v{TUN2SOCKS_VERSION}...")

            temp_dir = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, "temp_tun2socks")
            os.makedirs(temp_dir, exist_ok=True)

            zip_path = os.path.join(temp_dir, "tun2socks.zip")

            urllib.request.urlretrieve(TUN2SOCKS_URL, zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if "tun2socks" in f.lower() and not f.endswith(".zip"):
                        src = os.path.join(root, f)
                        shutil.copy2(src, TUN2SOCKS_BIN)
                        os.chmod(TUN2SOCKS_BIN, 0o755)
                        break

            shutil.rmtree(temp_dir, ignore_errors=True)

            decky.logger.info("tun2socks installed successfully")
            return {"success": True}
        except Exception as e:
            decky.logger.error(f"Failed to install tun2socks: {e}")
            return {"success": False, "error": f"Failed to install tun2socks: {e}"}

    async def uninstall_dependencies(self) -> Dict[str, Any]:
        """Remove installed binaries"""
        try:
            if os.path.exists(BIN_DIR):
                shutil.rmtree(BIN_DIR, ignore_errors=True)
            os.makedirs(BIN_DIR, exist_ok=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _migration(self):
        decky.migrate_logs(os.path.join(decky.DECKY_USER_HOME, ".v2deck", "logs"))
        decky.migrate_settings(os.path.join(decky.DECKY_USER_HOME, ".v2deck", "settings"))
        decky.migrate_runtime(os.path.join(decky.DECKY_USER_HOME, ".v2deck", "runtime"))
