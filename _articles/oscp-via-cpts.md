---
layout: post
title: "OSCP via CPTS, not versus"
date: 2025-06-20
categories: [article, certs]
---

I wasn't around to see it until recently, but it seems that ever since Hack The Box launched their Certified Penetration Testing Specialist ([CPTS](https://academy.hackthebox.com/preview/certifications/htb-certified-penetration-testing-specialist)) certification, the comparisons were inevitable: _"which one is better, CPTS or OSCP?"_

I think the best answer to that comparison is _"it depends"_, and I'll touch upon it in this article as well. But the second best answer is _"why not both?"_, and that will be my main focus. I got my CPTS on the way to getting OSCP, after doing a bit of research to assess my options. I'll tell you about how that went, prefaced by a bit of context of where I was before starting the journey. Once we have that baseline, I'll try to help you figure out what you can take from my experience, and what you can leave.

## id && sudo -l
Let's talk a bit about my experience in offensive security before I started my path to OSCP, to better frame my decisions and how yours might be different.

I was lucky to grow up with access to a computer (an [IBM PS/1](https://en.wikipedia.org/wiki/IBM_PS/1#Models_2011)!), so my interest in programming started early on, and the fascination with hacking followed a while after. I went on to study software engineering in university, but in parallel I was getting yelled at by my family for staying up all night trying to beat [wargames](https://web.archive.org/web/20051124165147/http://www.dievo.org/index.php?cmd=1&part=2&PHPSESSID=b367364a1fa0c6379594c8553b5a0c0a). With the start of my career I lost the habit, until the middle of 2021, when I started playing around on TryHackMe in my spare time. In 2023 I had the opportunity to join the infosec team at the company I had been with for a few years, and finally got paid to hack! My next job after that was back in leadership, though quite hands-on due to the size of the structure, with (defensive) security being one of the responsibilities.

After I resigned from that position, I paused for a bit to figure out where I wanted to go. I decided it was finally time to listen to that calling, and that my background would bring a ton of value in offensive security. Looking at the interesting jobs around me, all of them had the OSCP as a requirement at some level. Despite that fascination, all I had to show for it was some very spotty knowledge. So I was going to take the time to properly learn the skills, get the certification to validate those skills, and finally attack the job market.

## The ends, to justify the means
The OSCP has a reputation for being tough, and the cost made me want to be pretty sure I'd succeed. So I looked up what people did to prepare for the exam. Alongside the advice that I already knew from a while back, to beat a sizeable number of `boot2root` machines on platforms like Hack The Box, there was a new pattern emerging: HTB Academy was being recommended as a better place to learn, if you were at least relatively inexperienced. I looked into it, and decided to follow that advice. Before we get into the why, here's what I decided to do and how it worked out:

- I studied the Penetration Tester path, required to take the CPTS exam, in a little over 4 months;
- I sat the exam in early March, and got the passing results on April 2nd;
- I had actually enrolled for the OSCP the day before, with the 90-day course + exam option;
- I skimmed through the course, worked through the three mock exams, and scheduled my exam for the 1st of May;
- I got the passing results on May 4th.

Would I do it again? Absolutely. Do I recommend it? It depends. Is there a better way? I don't think so. Can I please make sense? Alright, let me explain.

## The problem
The PEN-200 is the course you have access to when you enroll for OSCP, although you are not required to complete any of it. It covers network, web application and Active Directory penetration testing, underpinned by explaining the general testing methodology. However, the sentiment is that the course alone does _not_ prepare you for the OSCP exam, if you are relatively new to the field, and I agree. It is hard to put my finger on why the course doesn't do enough, but I think it is ultimately due to not guiding the student through enough situations.

The course includes a sizeable amount of challenge labs, which you are encouraged to complete, but you are on your own to solve them as they are unguided. I should say that from what I could tell, the student mentors on OffSec's Discord were helpful when people had trouble with the labs. But I don't think this is an efficient learning method. It is often recommended to complement the course's labs with even more labs on other platforms (the [TJ Null](https://docs.google.com/spreadsheets/u/1/d/1dwSMIAPIam0PuRBkCiDI88pU3yzrqqHkDtBngUHNCw8/htmlview) and more recently the [LainKusanagi](https://docs.google.com/spreadsheets/d/18weuz_Eeynr6sXFQ87Cd5F0slOj9Z6rt/edit?gid=487240997#gid=487240997) lists). It's definitely fair to expect a degree of independent learning. A discussion on the famous "try harder" mantra could get its own article, but it's true that this field practically _demands_ the ability to learn independently. But this felt a bit like being taught that there are many ways to start a fire, then being taught one way to start a fire, and then being air-dropped in wilderness and told to survive, and try harder.

## The solution
The [Penetration Tester](https://academy.hackthebox.com/path/preview/penetration-tester) job role path, on HTB Academy, is the organised collection of learning modules you are required to complete in order to take the CPTS exam. It also covers network, web application and Active Directory penetration testing, drilling methodology into you as you go. Sounds familiar. Does it prepare you for OSCP? _Yes_. Save for a few exceptions, the CPTS course is more complete in both the breadth and depth of the subjects, which I think helps precisely by guiding the student through more situations. By teaching you more ways to start a fire, you'll be in a better position to understand what it takes to start a fire, increasing your chances to recognise how you may be able to start a fire in the wild.

I invite you to compare the course structures yourself:
- [for CPTS](https://academy.hackthebox.com/path/preview/penetration-tester), expand the "28 Modules included" dropdown, and open the ones that interest you for their table of contents;
- [for OSCP](https://www.offsec.com/app/uploads/2023/03/V1.Regular-Syllabus-PDF.pdf), the syllabus they make available online is still mostly up-to-date, except for the cloud modules.

The breadth and depth difference should be clear. The few exceptions where the PEN-200 covers more than the CPTS path are the modules on Antivirus Evasion, Phishing and Client Attacks, and AWS enumeration and attacks. Note that the AWS modules were out of scope for the OSCP exam when I took it, but this might change.

The catch is that the HTB Academy path will take considerably longer to complete. This can be a problem if you can only dedicate an hour or two regularly, since it might feel like it will take ages to complete, which can hurt your motivation. To be fair though, there are no shortcuts. You will need to put in the work one way or the other, and I think this is a far better alternative than hoping you've solved enough boxes. Bonus: you can still solve boxes as well.

Let's talk monies. OSCP is already expensive, how much are these extra lessons going to cost? Surprisingly, less than 10% of the cheapest OSCP bundle. You would think that `long course * subscription model = $$$$$$", but you can actually take the course for as little as $110 total (I'll explain how later), or even $8 a month if you are a student.

## The details, where the devil is
Ok, you have somehow reached this far (I'm flattered!) so I guess I have your attention. Here's what I think you should do.

Go enroll on HTB Academy. If you're new to IT or want to fill some gaps in your fundamentals, check the modules in the [Information Security Foundations](https://academy.hackthebox.com/path/preview/information-security-foundations) path. Knowledge in these areas is considered a prerequisite for what we are going to do next, and these are all free so you don't even need a subscription yet.

By the way, _"should I take \[insert easier cert here\] before?"_ If you plan to get OSCP, no, don't worry about that and don't waste your money. The CPTS path will cover the knowledge, and OSCP will cover the job hunt.

Alright, when you're good to go, start the Penetration Tester path. For that you'll need some kind of paid access. It gets complicated, and you should explore all the options for yourself, but if you're only interested in the CPTS course (with or without exam), then:
- if you're a student, get the student subscription at $8 a month;
- if not, start a _monthly_ Platinum subscription, then _downgrade_ to Gold for the second month, then _cancel_ your subscription, for a total of $106 (you may have VAT on top).

Now it's time to study. Take notes and most importantly take your time, don't compare yourself to others and focus on understanding, not speed. If you need help, the `#modules` channel on [HTB's Discord](https://discord.gg/hackthebox) is a good place to get it. Take breaks when you need them, don't underestimate burn-out. The final module, [Attacking Enterprise Networks](https://academy.hackthebox.com/course/preview/attacking-enterprise-networks), is a simulated external-to-internal penetration test, from anonymous internet user to Domain Admin. You should attempt to do this blindly - just spin up the lab, don't look at the content nor the questions (they serve as a walkthrough), and work your way through it. It'll be a great test of your overall understanding.

When you're done, I _know_ you'll feel _really_ good that it's _done_. Be proud! It was a helluva lot of work even before the exam. Speaking of which...

... should you take the exam? The truth is that it doesn't yet hold a ton of value for HR (though maybe it does in your region, make sure you check). It's still making its way, as a relatively new certification. A voucher for the exam costs $210, unless you didn't follow my advice and got an annual subscription. So you might choose to skip the exam, and I think that's perfectly valid. My opinion? If you can afford it, _definitely_ go for it. It will help consolidate everything you've learned, test you under the pressure of a deadline, and I'm convinced it _will_ eventually hold value for HR.

The exam is a 10-day affair, during which you perform a penetration test of an organisation and deliver a report of the findings. You can fail the exam because of a poor report despite nailing the technical part (and many have). Everything you learn in the course _can_ feature in the exam, and the exam will _not_ feature anything that wasn't taught, so in more ways than not, the course _will_ prepare you for the exam. Because of this, the best time to take it is soon after finishing the course. Some people recommend doing boxes or ProLabs to practice. I had done six easy boxes during the course, but didn't do any more or any ProLabs between finishing the course and starting the exam.

Regarding the technical part, yes, you will have learned everything you need to pass, but the exam will still test you, mostly on putting things together and the fundamentals of what it is that you are trying to do. The 10 days allow for being healthy - the only night that I barely slept was the last one, as I was racing to finish my report. But I do recommend taking at least some days off from work for the exam. Aside from that, there are many posts with tips for the exam, [this one](https://www.brunorochamoura.com/posts/cpts-tips/) being the best for my taste, and I don't think I could add to them. Oh, actually that's not true, I have ~~a shameless plug~~ a tip: if you write your notes in markdown, you might be interested in my [mdfindings2reptor](mdfindings2reptor).

## The beast
You're here. You've finished the HTB Academy path, you might even have taken the exam, and it's time to finally slay the OSCP dragon. At this stage you might not want to do exactly as I did. I was in a hurry to get this done, so I skipped some steps. You probably can skip some too, I just can't recommend it in good faith.

First, the course content. I didn't do the AWS modules until after the exam, because like I said they were not in scope back then. That might be different for you, reader from the future. The rest of the course I sped through, with my notes from CPTS on the side, looking for anything that had not been covered. There were some additions, mostly on different ways of achieving the same things, so it was still valuable. I think you can do the same. I didn't do any of the exercises included in each module. If I had given myself more time, I would have done at least the capstone exercises.

When it comes to the challenge labs, I only did the three mock exams. There is some confusion over whether these really are retired exam environments, but the course claimed they were the closest labs to what I would face in the exam, so I focused on them. Treat them like exams, and dedicate at least an 8 hour chunk of your focus to them. There are many more challenge labs, and I would actually recommend doing some of them. OffSec boxes have a different feel, if you're coming from HTB at least. It's hard to say what it is, but you'll know it when you see it. But I wouldn't think you need to complete _all_ of them, at some point I think you'd just be avoiding the exam.

One last piece of advice before the exam: maybe I'm weird, but if you're anything like me, you might find yourself _annoyed_ at this point. You will have noticed from the challenge labs that some of the exploitation paths are... _annoying_. "Guessy" could be another word, "underwhelming" yet another. For example, you might well need to bruteforce that login form, especially if you've spent hours trying to find another way in and found nothing. Does it happen in the wild? Sure. Can anyone bruteforce a login without needing an expensive course? Yes. Are there better things to test us on? You bet. But I had to accept this and prepare for it, and so should you. No need to add anger to the cocktail of emotions you might experience on exam day.

Finally, it's time. Trust me, you are ready. Don't underestimate the exam, but be confident. Anything that happens now is as much under your control as it could have been. Sure, you could have done more labs, but where would it stop? If you've followed this path, I know that you know what you're doing. Go for it, and good luck!

---

I hope this was helpful, and whether or not you follow my advice, I hope you pass! I think the world needs more of us. As always, for reading this far, you're a champ.