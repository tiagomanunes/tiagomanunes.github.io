---
layout: post
title: "Underpass"
date: 2025-05-10
categories: [htb, easy]
provider: htb
machine: underpass
retired: true
---

Underpass was a cool little box that served as a mini-test for methodology. With [Administrator](/writeups/administrator/) we talked about how I said that "if I don't learn anything, I won't write about it". This one made me go back to thinking that by that standard I'll probably write something about 99% of boxes, and Administrator was in that 1%. More often than not there will be something completely new that we'll have to adapt to. So this will be a short one, but I still think the process was interesting. Short story shorter:

<div class="attack-chain">
  {% include attack-step.html title="Enumerate SNMP" description="Discovered daloradius web app in SNMP public strings" type="enum" %}
  {% include attack-step.html title="Exploit misconfiguration" description="Accessed web app using default credentials" type="attack" %}
  {% include attack-step.html title="Enumerate web app" description="Discovered MD5-hashed password for `moshSvc`" type="enum" %}
  {% include attack-step.html title="Foothold" description="Cracked password for `moshSvc` and logged in via SSH" type="foothold" %}
  {% include attack-step.html title="Enumerate premissions" description="Discovered that `moshSvc` can run `mosh-server` with sudo" type="enum" %}
  {% include attack-step.html title="Privilege escalation" description="Abuse sudo rights to get root shell" type="root" %}
</div>

## Ambient dub techno music on
`Nmap` showed us only SSH and HTTP ports on the initial and full TCP scans. Pointing a web browser at the machine found only a default post-install Apache page, so the next step, for me anyway, was to check for any hidden directories and virtual hosts, but both of these found nothing with decent wordlists.

The Apache version is not the latest, but while there are a few reported vulnerabilities, none of them are an obvious next step, especially considering the context of an Easy-rated machine on HTB. So at this point we have essentially nothing on the two TCP services we found. Next step, UDP. And yep, we get something:
```
$ sudo nmap -F -sUV 10.10.11.48 -vv -oA initial-udp
<SNIP>
Not shown: 97 closed udp ports (port-unreach)
PORT     STATE         SERVICE REASON              VERSION
161/udp  open          snmp    udp-response ttl 63 SNMPv1 server; net-snmp SNMPv3 server (public)
1812/udp open|filtered radius  no-response
1813/udp open|filtered radacct no-response
Service Info: Host: UnDerPass.htb is the only daloradius server in the basin!
```

_Note:_ as I write this, I realise that I completely disregarded the radius ports at that point, thinking they were false-positives. With the context of the rest of the box, I know they weren't, but the `REASON` in the `nmap` output also tells us that. These ports turned out not to be relevant, at least for the path I took, but I would absolutely _not_ have remembered these ports had I got stuck later on. So yeah, I definitely do have lessons learned for this box too.

Well, hello SNMP, I think the last time I saw you was on HTB Academy's [Footprinting](https://academy.hackthebox.com/course/preview/footprinting) module, which does feel like ages ago. A quick look at the notes and we have some things to try. It looks like version `2c` is supported and we get a set of public community strings that reveal useful information:
```
$ snmpwalk -v2c -c public 10.10.11.48
iso.3.6.1.2.1.1.1.0 = STRING: "Linux underpass 5.15.0-126-generic #136-Ubuntu SMP Wed Nov 6 10:38:22 UTC 2024 x86_64"
iso.3.6.1.2.1.1.2.0 = OID: iso.3.6.1.4.1.8072.3.2.10
iso.3.6.1.2.1.1.3.0 = Timeticks: (2917611) 8:06:16.11
iso.3.6.1.2.1.1.4.0 = STRING: "steve@underpass.htb"
iso.3.6.1.2.1.1.5.0 = STRING: "UnDerPass.htb is the only daloradius server in the basin!"
iso.3.6.1.2.1.1.6.0 = STRING: "Nevada, U.S.A. but not Vegas"
<SNIP>
```

It _seems_ like we've found a username, and "UnDerPass" looks suspicious, so we try those as a credential pair with SSH because why not, but it was not meant to be. Again as I write this I notice that the weird capitalisation is for "UDP", so I guess retro-hints are a thing. Anyway, we note a potentially vulnerable Linux version for later, and the other relevant thing is a mention of a "daloradius server" that this machine is supposed to be.

A quick google search tells us that it is [a web application](https://github.com/lirantal/daloradius) to manage RADIUS deployments. At this point we don't particularly care about what the app does, we just go back to the browser and indeed, pointing it to `http://underpass.htb/daloradius/` gives us a forbidden response code.

## Breaching the radius I mean perimeter
I threw `ffuf` at it again to find that we could read some files such as `ChangeLog`, and going a bit deeper into the GitHub project we see that `/app/operators/` or `/app/users/` are the authenticated entry-points for the app. The `README` file also quickly mentions that "the installation script will generate _random credentials_ to be used for the operator's first login", so I didn't even try some cheesy admin credentials, aside from giving SNMP Steve a shot just in case.

The `2.2 beta` version we see doesn't seem to be too vulnerable, even to authenticated attackers. Considering that I could read some files at the base of the installation, I looked at the project's source code once again to look for potentially compromising data in files like `docker-compose.yml`. It is indeed downloadable, and even though it looks like a copy of the default one, I checked what things like `DEFAULT_CLIENT_SECRET` were about. That took me to [someone's GitHub project](https://github.com/asdaru/freeradius-mysql-daloradius/blob/master/README.md), casually saying the following: "Information about web interface you can find on daloradius github. _Default login and password for web interface: ..._"

Euh, so what was this earlier about random credentials? Someone is lying, and trying those default and definitely not random credentials does work. On the dashboard, due to there not being much of anything, the existence of one user stands out. Following that up, we find an `svcMosh` with a password, seemingly hashed with MD5. Sure enough, hashcat takes care of it quickly:
```
$ hashcat 4<REDACTED>3 rockyou.txt -m 0

<SNIP>

4<REDACTED>3:<REDACTED>
```

SSH accepts the credentials, so \[hacker voice\] _we're in_.

## The mosh pit
As usual, before anything else, we run `id` and `sudo -l`. The latter tells us we can run `/usr/bin/mosh-server`. I didn't know about [Mosh](https://mosh.org/) before this, and it looks pretty cool. I can't say I understood what the `mosh` binary actually does, but I'll leave that for another day even though it turned out to be the difference here.

After looking for vulnerabilities (there aren't any known ones, huh), and for any tricks to abuse `sudo` in unexpected ways (no entry on GTFObins either), I assumed that running the server with `sudo` was probably just a Bad Idea™ waiting to be exploited. Running the server tells us on which port it's running, gives us an encryption key that we need to use to connect with a client, and according to the `man` page, stays running for 60 seconds waiting for a connection:
```
svcMosh@underpass:/$ sudo /usr/bin/mosh-server

MOSH CONNECT 60001 +dV5WunhS7NtoW1Ok22SCQ

<SNIP>

[mosh-server detached, pid = 4128]
```

I wasn't quite sure what to do after this, so I tried different things, mostly with the `mosh` command, which basically started a new SSH session but not with elevated privileges. I think what tipped me to trying the `mosh-client` was realising that `mosh` worked even without starting the server, so it probably was not connecting to the one I was spawning. Anyway, to use the client, we first need to set the encryption key given at server start in a `MOSH_KEY` environment variable, and then connect to the listening port. And voilà:

```
svcMosh@underpass:/$ export MOSH_KEY=+dV5WunhS7NtoW1Ok22SCQ
svcMosh@underpass:/$ mosh-client 127.0.0.1 60001

<SNIP>

root@underpass:~# whoami
root
```

## Roll the credits
- `Nmap` false-positives can be a thing, especially with UDP, but don't be too quick to dismiss things.
- As always, for reading this far, you're a champ.