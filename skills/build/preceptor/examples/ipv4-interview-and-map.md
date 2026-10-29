# Interview and course map for the IPv4 primer (SYNTHETIC learner)

The learner here is invented. The authoring session wrote both sides, to record steps 1 to 4 of the procedure as they were carried out for the example course. No real person was interviewed.

## What the request already answered

The request (the same text as the learner brief among the acceptance-case inputs) gave the subject, goal, pace, depth, exclusions and notation tolerance. Those were not asked again.

| Point | Taken from the request |
|---|---|
| Subject | IPv4 subnetting by hand |
| Goal | A first networking certificate exam in about a month, no calculator |
| Depth | Solid competence: can do it, not only follow it |
| Pace | Three or four half-hour sessions a week |
| Must exclude | History of the internet, IPv6, variable-length subnetting |
| Notation | Symbols accepted if each is explained once |

## What was asked

**Level, with one diagnostic question.** "Without a calculator: what is `11000000` in decimal, and what is the network address of 192.168.1.130/25?"

Answer given: "192 for the first. I don't know how to do the second."

Reading: binary is slow but present; nothing about prefixes is secure. The course starts at binary and treats it as a short first module, not as assumed knowledge.

**Anchor domain.** "Home networks: routers, addresses handed out by the router." Used for the applied challenge only.

## The course map shown for approval

Method: preceptor course build. Size: **primer, 5 modules**. One skill resting on four ideas: five modules cover it, and a longer course would have to pad.

| # | Module | Opens after | The learner can then |
|---|---|---|---|
| 1 | Binary and place value | (start) | Convert between 8-bit binary and decimal |
| 2 | Address structure and prefix length | 1 | Split an address into network and host bits; convert a prefix length to a mask and back |
| 3 | Network and broadcast addresses | 2 | Find the network address, broadcast address and usable range of any host |
| 4 | Counting hosts and subnets | 2 | Count addresses, usable hosts and subnets; choose a prefix length for a requirement |
| 5 | Splitting a network (applied challenge) | 3 and 4 | Cut a network into equal subnets, complete any row of the plan, and check it against requirements |

Modules 3 and 4 both rest on module 2 and not on each other, so either can be done first. Module 5 needs both.

Left out, as asked: IPv6, variable-length subnetting, /31 and /32 (named in the course as outside it).

Reply: "Yes."

## What was built

The course data was written module by module to the standard in the course design reference, validated, recomputed and built. The commands and their output are in `README.md` beside this file.
