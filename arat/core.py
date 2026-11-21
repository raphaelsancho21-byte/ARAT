"""Rotinas de diagnóstico local e ADB com autorização prévia."""
from __future__ import annotations
import concurrent.futures
import ipaddress
import json
import platform
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def run(args: list[str], timeout: int = 12) -> tuple[int, str]:
    try:
        r = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return 1, str(e)

def local_networks() -> list[str]:
    found = []
    try:
        host = socket.gethostname()
        ips = {info[4][0] for info in socket.getaddrinfo(host, None, family=socket.AF_INET)}
        for ip in ips:
            addr = ipaddress.ip_address(ip)
            if addr.is_private and not addr.is_loopback and not addr.is_link_local:
                found.append(str(ipaddress.ip_network(f"{ip}/24", strict=False)))
    except OSError:
        pass
    return sorted(set(found))

def ping(host: str, timeout: float = 0.9) -> bool:
    if platform.system() == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(max(100, int(timeout * 1000))), host]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", host]
    return run(cmd, timeout=4)[0] == 0

def arp_entries() -> list[dict[str, str]]:
    code, output = run(["arp", "-a"], timeout=8)
    if code:
        return []
    rows = []
    rx = re.compile(r"(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)\s+(?P<mac>(?:[\da-fA-F]{2}[:-]){5}[\da-fA-F]{2})")
    for line in output.splitlines():
        m = rx.search(line)
        if m:
            try:
                if ipaddress.ip_address(m.group("ip")).is_multicast:
                    continue
            except ValueError:
                continue
            rows.append({"ip": m.group("ip"), "mac": m.group("mac").lower()})
    return sorted({r["ip"]: r for r in rows}.values(), key=lambda x: ipaddress.ip_address(x["ip"]))

def discover(cidr: str, max_hosts: int = 254, workers: int = 24) -> dict:
    net = ipaddress.ip_network(cidr, strict=False)
    if net.version != 4 or not net.is_private:
        raise ValueError("Use uma faixa IPv4 privada de sua rede (ex.: 192.168.1.0/24).")
    if net.num_addresses > max_hosts + 2:
        raise ValueError(f"Faixa muito grande. Máximo: {max_hosts} endereços utilizáveis.")
    hosts = [str(x) for x in net.hosts()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 24)) as pool:
        live = [host for host, result in zip(hosts, pool.map(ping, hosts)) if result]
    seen = {x["ip"]: x for x in arp_entries() if ipaddress.ip_address(x["ip"]) in net}
    for ip in live:
        seen.setdefault(ip, {"ip": ip, "mac": "desconhecido"})
    return {"network": str(net), "scanned": len(hosts), "reachable_ping": live, "devices": sorted(seen.values(), key=lambda x: ipaddress.ip_address(x["ip"])), "timestamp": datetime.now(timezone.utc).isoformat()}

def adb_exists() -> bool:
    return shutil.which("adb") is not None

def adb_devices() -> list[dict[str, str]]:
    if not adb_exists():
        raise RuntimeError("ADB não encontrado. Instale Android SDK Platform-Tools.")
    code, output = run(["adb", "devices", "-l"], timeout=20)
    if code:
        raise RuntimeError(output)
    devices = []
    for line in output.splitlines():
        if "List of devices" in line or not line.strip() or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"serial": parts[0], "status": parts[1], "description": " ".join(parts[2:])})
    return devices

def validated_device(serial: str | None) -> str:
    devices = adb_devices()
    online = [d["serial"] for d in devices if d["status"] == "device"]
    if serial:
        if serial not in online:
            raise ValueError("Dispositivo não autorizado/conectado via ADB.")
        return serial
    if len(online) != 1:
        raise ValueError("Conecte e autorize exatamente um dispositivo ou forneça --serial.")
    return online[0]

def adb_ls(serial: str | None, directory: str) -> str:
    selected = validated_device(serial)
    if not (directory == "/sdcard" or directory.startswith("/sdcard/")):
        raise ValueError("A navegação é limitada a /sdcard e subpastas.")
    code, output = run(["adb", "-s", selected, "shell", "ls", "-la", "--", directory], timeout=30)
    if code:
        raise RuntimeError(output)
    return output

def adb_pull(serial: str | None, remote: str, destination: str) -> str:
    selected = validated_device(serial)
    if not remote.startswith("/sdcard/") or ".." in Path(remote).parts:
        raise ValueError("Use arquivo/pasta dentro de /sdcard/, sem '..'.")
    local = Path(destination).expanduser().resolve()
    if not local.exists() or not local.is_dir():
        raise ValueError("Destino local deve ser uma pasta existente.")
    code, output = run(["adb", "-s", selected, "pull", remote, str(local)], timeout=300)
    if code:
        raise RuntimeError(output)
    return output

def save_report(data: dict, path: str) -> Path:
    dest = Path(path).expanduser().resolve()
    if dest.suffix.lower() != ".json":
        raise ValueError("Relatórios devem usar extensão .json")
    if not dest.parent.is_dir():
        raise ValueError("Pasta de destino inexistente")
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest
