# ARAT — Acesso Remoto Ao Telefone

CLI com visual de terminal, descoberta de dispositivos em redes privadas autorizadas, tabela ARP, listagem de sessões ADB autorizadas e cópia de arquivos acessíveis via ADB.

**O ARAT não invade telefones, não contorna bloqueios e não monitora pessoas.**

## Instalação (Windows PowerShell)

Requisitos: Python 3.10+ e Git. Para funções Android, Android SDK Platform-Tools (`adb`) no PATH e conexão ADB já autorizada pelo dono do aparelho.

```powershell
git clone https://github.com/raphaelsancho21-byte/ARAT.git
cd ARAT
py -m pip install --user .
arat
```

Se `arat` não estiver no PATH, execute `py -m arat`.

## Comandos

```powershell
arat
arat networks
arat scan 192.168.1.0/24
arat scan 192.168.1.0/24 --report scan.json
arat arp
arat devices
arat ls /sdcard/Download
arat pull /sdcard/DCIM .
```

## Limitações

- Escanear um IP/MAC não dá acesso à tela, aos aplicativos ou aos arquivos.
- Um aparelho fora da rede não pode ser descoberto pela varredura local.
- Redes de convidados, isolamento Wi-Fi ou bloqueio de ICMP podem esconder aparelhos.
- Android pode usar endereços MAC aleatórios.
- ADB só funciona com depuração e autorização prévias no telefone.
- Varredura limitada a redes IPv4 privadas com até 254 hosts.
- Nenhuma telemetria, servidor remoto ou upload de dados.

## Testes

```powershell
py -m unittest discover -s tests -v
```
