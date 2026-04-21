#!/usr/bin/env python3

import argparse
import concurrent.futures
import ipaddress
import json
import shutil
import socket
import subprocess
from typing import List, Optional

import requests

DEFAULT_PORTS = [11434]


# ----------------------------
# Utility / Logging
# ----------------------------
def log(msg: str, verbose: bool):
    if verbose:
        print(msg)


# ----------------------------
# ARP Scan (fast discovery)
# ----------------------------
def arp_discover(subnet: str, interface: Optional[str], verbose: bool) -> List[str]:
    """Use arp-scan to find live hosts (requires sudo)."""
    if not shutil.which("arp-scan"):
        print("[!] arp-scan not found, falling back to full scan")
        return []

    cmd = ["arp-scan", subnet]
    if interface:
        cmd.insert(1, f"--interface={interface}")

    print("[*] Running arp-scan (may require sudo)...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("[!] arp-scan failed:", e)
        return []

    hosts = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 1:
            ip = parts[0]
            try:
                ipaddress.ip_address(ip)
                hosts.append(ip)
            except ValueError:
                continue

    print(f"[*] arp-scan found {len(hosts)} live hosts")
    return hosts


# ----------------------------
# TCP Port Check
# ----------------------------
def is_tcp_open(host: str, port: int, timeout=0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ----------------------------
# Ollama Verification
# ----------------------------
def probe_ollama(host: str, port: int, verbose: bool) -> Optional[dict]:
    base = f"http://{host}:{port}"

    try:
        r = requests.get(f"{base}/api/version", timeout=1.5)
        if r.ok:
            data = r.json()
            if "version" in data:
                return {
                    "host": host,
                    "port": port,
                    "version": data["version"],
                    "method": "api/version",
                }
    except Exception:
        pass

    try:
        r = requests.get(f"{base}/api/tags", timeout=1.5)
        if r.ok:
            return {
                "host": host,
                "port": port,
                "version": "unknown",
                "method": "api/tags",
            }
    except Exception:
        pass

    return None


# ----------------------------
# Per-host scan
# ----------------------------
def scan_host(host: str, ports, verbose: bool):
    results = []

    log(f"[SCAN] {host}", verbose)

    for port in ports:
        if is_tcp_open(host, port):
            log(f"  [+] {host}:{port} OPEN", verbose)

            res = probe_ollama(host, port, verbose)
            if res:
                print(
                    f"[FOUND] Ollama at {host}:{port} "
                    f"(version={res['version']}, via {res['method']})"
                )
                results.append(res)
        else:
            log(f"  [-] {host}:{port} closed", verbose)

    return results


# ----------------------------
# Main
# ----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("subnet", help="CIDR subnet (e.g. 192.168.1.0/24)")
    parser.add_argument("--ports", nargs="+", type=int, default=DEFAULT_PORTS)
    parser.add_argument("--workers", type=int, default=64)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--arp", action="store_true", help="Use arp-scan (needs sudo)")
    parser.add_argument("--interface", help="Network interface for arp-scan")

    args = parser.parse_args()

    # ----------------------------
    # Host discovery
    # ----------------------------
    if args.arp:
        hosts = arp_discover(args.subnet, args.interface, args.verbose)
    else:
        network = ipaddress.ip_network(args.subnet, strict=False)
        hosts = [str(ip) for ip in network.hosts()]
        print(f"[*] No ARP scan, brute forcing {len(hosts)} hosts")

    if not hosts:
        print("[!] No hosts found to scan")
        return

    print(f"[*] Scanning {len(hosts)} hosts on ports {args.ports}")

    # ----------------------------
    # Scanning
    # ----------------------------
    found = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(scan_host, host, args.ports, args.verbose)
            for host in hosts
        ]

        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            res = future.result()
            found.extend(res)

            if i % 50 == 0:
                print(f"[*] Progress: {i}/{len(hosts)} hosts scanned")

    # ----------------------------
    # Summary
    # ----------------------------
    print("\n--- SUMMARY ---")
    if found:
        for f in found:
            print(f"{f['host']}:{f['port']} (version={f['version']})")
    else:
        print("No Ollama instances found")


if __name__ == "__main__":
    main()
