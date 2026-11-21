"""Interface de terminal ARAT."""
from __future__ import annotations
import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from . import __version__
from .core import local_networks, discover, arp_entries, adb_exists, adb_devices, adb_ls, adb_pull, save_report

console = Console()
BANNER = r"""
     ___    ____  ___  ______
    /   |  / __ \/   |/_  __/
   / /| | / /_/ / /| | / /
  / ___ |/ _, _/ ___ |/ /
 /_/  |_/_/ |_/_/  |_/_/
"""

def header():
    console.print(BANNER, style="bold cyan")
    console.print(f"[bold]ARAT[/bold] / Acesso Remoto Ao Telefone  [dim]v{__version__}[/dim]")
    console.print("[dim]Diagnóstico autorizado de rede • Android • arquivos via ADB[/dim]\n")

def devices_table(devices):
    table = Table(title="Dispositivos encontrados", show_lines=False)
    table.add_column("IP", style="cyan")
    table.add_column("MAC", style="green")
    for dev in devices:
        table.add_row(dev["ip"], dev.get("mac", "desconhecido"))
    console.print(table)
    console.print("[yellow]Identificar um IP/MAC não concede acesso ao aparelho.[/yellow]")

def scan(cidr, report=None):
    console.print(f"[cyan]Verificando[/cyan] {cidr} (somente rede privada autorizada)...")
    data = discover(cidr)
    console.print(f"Hosts verificados: {data['scanned']} | Responderam ping: {len(data['reachable_ping'])}")
    devices_table(data["devices"])
    if report:
        console.print(f"[green]Relatório:[/green] {save_report(data, report)}")

def panel():
    header()
    while True:
        console.print(Panel("[1] Interfaces de rede  [2] Descobrir dispositivos\n[3] Tabela ARP        [4] Dispositivos ADB\n[5] Listar arquivos     [6] Copiar arquivos\n[0] Sair", title="[bold cyan]CENTRAL ARAT[/bold cyan]", border_style="cyan"))
        choice = Prompt.ask("ARAT", choices=[str(n) for n in range(7)], default="0")
        try:
            if choice == "0":
                break
            if choice == "1":
                console.print("Redes IPv4 locais prováveis:", local_networks() or "nenhuma detectada")
            elif choice == "2":
                suggestions = local_networks()
                cidr = Prompt.ask("Faixa IPv4 privada da SUA rede", default=suggestions[0] if suggestions else "192.168.1.0/24")
                if Prompt.ask("Confirma que administra ou tem autorização para analisar esta rede?", choices=["s", "n"], default="n") != "s":
                    continue
                scan(cidr)
            elif choice == "3":
                devices_table(arp_entries())
            elif choice == "4":
                if not adb_exists():
                    console.print("[yellow]ADB indisponível. Instale Platform-Tools.[/yellow]")
                    continue
                console.print(adb_devices())
            elif choice == "5":
                console.print(adb_ls(None, Prompt.ask("Caminho Android autorizado", default="/sdcard/Download")))
            elif choice == "6":
                remote = Prompt.ask("Arquivo/pasta Android", default="/sdcard/Download")
                local = Prompt.ask("Pasta local de destino", default=".")
                console.print(adb_pull(None, remote, local))
        except (RuntimeError, ValueError, OSError) as ex:
            console.print(f"[red]Erro:[/red] {ex}")
        console.print()

def make_parser():
    parser = argparse.ArgumentParser(prog="arat", description="ARAT: acesso autorizado e diagnóstico CLI")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("networks", help="Mostrar possíveis redes IPv4 locais")
    scan_p = sub.add_parser("scan", help="Descobrir hosts em sua rede privada autorizada")
    scan_p.add_argument("cidr", help="ex.: 192.168.1.0/24")
    scan_p.add_argument("--report", help="Salvar relatório JSON")
    sub.add_parser("arp", help="Mostrar vizinhos da tabela ARP")
    sub.add_parser("devices", help="Listar dispositivos ADB previamente autorizados")
    ls = sub.add_parser("ls", help="Listar arquivos de dispositivo ADB autorizado")
    ls.add_argument("path", nargs="?", default="/sdcard")
    ls.add_argument("--serial")
    pull = sub.add_parser("pull", help="Copiar arquivos de dispositivo ADB autorizado")
    pull.add_argument("remote")
    pull.add_argument("destination")
    pull.add_argument("--serial")
    return parser

def main():
    parser = make_parser()
    args = parser.parse_args()
    try:
        if args.command is None:
            panel()
        elif args.command == "networks":
            console.print(local_networks())
        elif args.command == "scan":
            scan(args.cidr, args.report)
        elif args.command == "arp":
            devices_table(arp_entries())
        elif args.command == "devices":
            if not adb_exists():
                raise RuntimeError("ADB não instalado (Android SDK Platform-Tools).")
            table = Table(title="ADB - sessões autorizadas")
            for col in ("Serial", "Estado", "Descrição"):
                table.add_column(col)
            for dev in adb_devices():
                table.add_row(dev["serial"], dev["status"], dev["description"])
            console.print(table)
        elif args.command == "ls":
            console.print(adb_ls(args.serial, args.path))
        elif args.command == "pull":
            console.print(adb_pull(args.serial, args.remote, args.destination))
    except (RuntimeError, ValueError, OSError) as ex:
        console.print(f"[red]Erro:[/red] {ex}")
        sys.exit(1)

if __name__ == "__main__":
    main()
