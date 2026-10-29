# IPv4 subnetting: twelve questions

Instrument: subnetting-quiz, version 1, quiz mode
Finished: 2026-10-08T20:47:09Z
Purpose: A check on prefix lengths, masks, network and broadcast addresses, usable ranges and summary routes.
Questions shown: 12. Answered: 10. Skipped: 2. No answer: 0. Hidden by earlier answers: 0.

### [mask-26] What is the subnet mask for a /26 prefix, in dotted decimal?
Type: single
Answer: 255.255.255.192
Result: correct

### [hosts-27] How many usable host addresses does a /27 subnet have?
Type: single
Answer: 32
Result: incorrect
Correct answer: 30

### [network-of-host] A host has the address 192.168.10.77/26. What is the network address of its subnet?
Type: single
Answer: 192.168.10.64
Result: correct

### [broadcast-of-host] What is the broadcast address of the subnet that contains 172.16.5.130/25?
Type: single
Answer: 172.16.5.127
Result: incorrect
Correct answer: 172.16.5.255

### [first-usable] What is the first usable host address in 10.20.30.96/28?
Type: single
Answer: 10.20.30.97
Result: correct

### [last-usable] What is the last usable host address in 192.168.4.0/22?
Type: single
Answer: 192.168.7.255
Result: incorrect
Correct answer: 192.168.7.254

### [prefix-for-hosts] A subnet must hold 50 hosts. Which is the longest prefix, meaning the smallest subnet, that fits them?
Type: single
Answer: /26
Result: correct

### [same-subnet] Which of these addresses are in the same /27 subnet as 192.168.1.100?
Type: multi
Answer:
- 192.168.1.97
Result: incorrect
Correct answer:
- 192.168.1.97
- 192.168.1.126

### [subnets-from-24] A /24 network is divided into /28 subnets. How many subnets does that give?
Type: single
Answer: 16
Result: correct

### [wildcard] Which wildcard mask is the inverse of the subnet mask 255.255.240.0?
Type: single
Answer: (skipped)
Result: skipped
Correct answer: 0.0.15.255

### [containing-subnet] 10.1.0.0/16 is divided into /21 subnets. Which subnet contains the address 10.1.9.200?
Type: single
Answer: 10.1.8.0/21
Result: correct

### [summary-route] Which single prefix covers exactly 192.168.8.0/24, 192.168.9.0/24, 192.168.10.0/24 and 192.168.11.0/24?
Type: single
Answer: (skipped)
Result: skipped
Correct answer: 192.168.8.0/22

## Score

Correct: 6
Attempted: 10
Total: 12
Skipped: 2
No answer: 0
Rule: One mark per item. An item is correct only when the answer matches exactly; a select-all item needs every correct option and no others. Skipped items earn no mark and are reported separately, so the result gives correct out of attempted and correct out of all items.

End of export: 12 questions.
