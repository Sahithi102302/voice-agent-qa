# Bug Report — Pretty Good AI Voice Agent (Pivot Point Orthopedics)

## Bug 1: Agent fabricates date of birth instead of asking the patient

**Severity:** Medium

**Call:** call-01-scheduling (transcript / recording — link or filename once saved)

**Details:** When creating a demo patient profile, the agent asked only for
the caller's first and last name, then stated "your date of birth is July
fourth two thousand for demo purposes" — inventing a DOB rather than asking
the patient for their real one. The caller was never asked for their actual
date of birth, even though the persona had one ready to provide (March 14,
1992). This could indicate the demo environment intentionally skips identity
verification, but if replicated outside the demo path, it would create
incorrect patient records.

## Bug 2: Agent misidentifies caller and appears to route the call incorrectly

**Severity:** High

**Call:** call-02-refill (transcript/recording)

**Details:** The agent initially assumed the caller was "Maria" (a name
from a prior test call placed from the same phone number), despite the
caller clearly introducing themselves as "Priya Nair" in their opening
sentence. The agent asked the caller to spell their name twice and read
back what appears to be a phone number associated with a different
patient record. The call then appears to transfer or route to an
unrelated automated message ("You've reached the Pretty Good AI test
line. Goodbye.") without the refill request being explicitly confirmed
or resolved. This suggests the agent may be indexing patient identity
primarily by phone number rather than properly reconciling it against
the stated name, which could lead to real patients being confused with
each other, or refill requests silently failing without clear
confirmation to the caller.

## Bug 3: Record lookup fails and dead-ends for unmatched callers (reproducible across 6+ calls)

**Severity: High**

**Primary example call:** call-09-refill (clearest full transcript of the failure sequence)
**Also observed in:** call-02-refill, call-03-vague_request, call-04-vague_request-retry,
call-05-interruption_heavy, call-06-reschedule
**Contrast (succeeded):** call-07-insurance_hours, call-08-scheduling-repeat

**Details:** Across 6 of 9 real test calls, when the agent attempted to
verify a caller's identity to access their patient record, the flow
consistently failed and dead-ended, following this exact pattern:

1. The agent frequently misidentified the caller (e.g., asking "Am I
   speaking with Maria?" for a caller who had already clearly stated a
   different name), based on the phone number the call came from.
2. When confirming a caller's phone number aloud for record lookup, the
   agent's read-back was garbled and did not form a coherent number
   (e.g., "one three eight eight three seven six five six").
3. The agent then stated: "I'm unable to find your record in our system
   right now," and offered to transfer the caller to "patient support."
4. Every observed transfer led to the same automated dead end: "Hello.
   You've reached the Pretty Good AI test line. Goodbye." — not a live
   agent, and not a continuation of the conversation.
5. In no affected call was the caller's original request (scheduling,
   rescheduling, or a refill) ever actually resolved.

As a control, calls with no record lookup required (general insurance
and hours questions) completed successfully and naturally every time.
Separately, one call using an identity that had an existing appointment
already on file completed its record lookup successfully, suggesting
the failure is specific to resolving a caller's identity for the first
time — particularly when a phone number is shared across multiple
distinct callers (as in this testing setup, and plausibly in real-world
cases like shared home or work phone lines).

**Impact:** Any new or first-time caller attempting to schedule,
reschedule, or request a refill — core functions of the system — risks
being routed to a non-functional dead end instead of completing their
request or reaching a working fallback.