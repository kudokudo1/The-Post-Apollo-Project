# SECURITY // META APOLLO // POST-APOLLO FAMILY

Post-Apollo welcomes good-faith security reports when they concern a real security or privacy risk.

In Post-Apollo, a security problem can be understood as a violation of an **expected relationship of trust**.

There is an expected relationship between a person and their machine, between one user and another, between software and the permissions it has been given, between an application and the information entrusted to it, and between different machines, seats, services, and systems.

A security vulnerability is something that breaks, bypasses, or unexpectedly changes one of those relationships.

That could mean information reaching someone who was never supposed to receive it. It could mean software gaining authority it was never supposed to have. It could mean one user controlling another user's environment, input crossing between seats, a remote machine crossing a trust boundary, or an application acting outside the relationship the user reasonably expected to have with it.

More conventional security problems belong here too. That includes exposed passwords, tokens, private keys, or sensitive information; unintended command execution; privilege escalation; unsafe file operations; authentication or authorization failures; compromised dependencies; unsafe automation; supply-chain attacks; or accidental disclosure of private repository or user information.

The important question is not simply:

**"Did something technically go wrong?"**

It is:

**"Did the system violate an expected relationship of trust between the people, tools, information, machines, or environments involved?"**

Not every Post-Apollo repository contains software. In repositories centered on philosophy, documentation, research, archives, or artwork, the expected relationships are different, and the security surface is naturally smaller. Security reports there are generally relevant when they involve scripts, automation, workflows, executable examples, exposed secrets, or accidentally published sensitive information.

Ordinary bugs are not automatically security vulnerabilities. Neither are feature requests, outdated documentation, visual problems, compatibility issues, architectural disagreements, or philosophical disagreements. Those belong in the normal issue process unless they also violate a meaningful relationship of trust.

If you discover a real vulnerability, please report it privately whenever possible.

If GitHub provides a **Report a vulnerability** option for the repository, use it. If no private reporting channel exists, open a small public issue asking the repository owner how to make private contact. Do not publish passwords, credentials, private information, exploit details, or a working proof of concept in that issue.

## GOOD-FAITH RESEARCH

Good-faith security research is welcome.

Good faith means respecting the same relationships you are trying to help protect.

Do not access information that does not belong to you. Do not interfere with other people or their systems. Do not maintain access longer than is reasonably necessary to understand or demonstrate the problem. Do not perform destructive testing, and do not publicly disclose a vulnerability before the maintainer has had a reasonable opportunity to investigate and repair it.

There is currently no guaranteed response-time agreement, and Post-Apollo does not operate a standing bug-bounty program.

Security here is not simply about defending code.

It is about preserving the expected relationships of trust between **people, tools, information, machines, and environments**.

**The goal is coordinated repair, not theater.**
