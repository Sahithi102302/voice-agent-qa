# Bug Report — Pretty Good AI Voice Agent (Pivot Point Orthopedics)

Testing conducted via an automated voice bot placing 13 real outbound
calls to +1-805-439-8008, using 9 distinct simulated patient personas
covering scheduling, rescheduling, refills, insurance/hours questions,
ambiguous requests, interruption-heavy callers, an urgent/out-of-scope
request, and a caller who self-corrects mid-call. All calls made from a
single phone number, as required.

**Severity summary:** Critical (1), High (1), Medium (2), Low (1)

---

## Bug 1: No urgency triage or escalation for acute/urgent patient requests

**Severity: Critical**

**Call:** call-12-impossible_request

**Details:** A caller stating sudden, severe pain and requesting to be
seen within the hour received no differentiated handling whatsoever —
the agent proceeded through the exact same generic identity-verification
flow used for routine scheduling and refill calls, with no acknowledgment
of urgency, no triage questions, and no offer of alternatives (urgent
care, ER, same-day escalation). The caller's separate question about a
phone-in prescription without an exam was never addressed at all. The
call then hit the same record-lookup failure and dead-end transfer
documented in Bug 2, meaning a patient in acute distress was routed to
an automated "Goodbye" message with no resolution and no safety-net
escalation path.

**Impact:** This is a patient-safety-relevant gap, not merely a
workflow inconvenience — a real caller in this situation would be left
with no guidance and no live human contact, at exactly the moment such
a gap matters most.

---

## Bug 2: Record lookup fails and dead-ends for callers with conflicting call history on the same phone number

**Severity:** High

**Primary example call:** call-09-refill (clearest full transcript of the failure sequence)

**Also observed in:** call-02-refill, call-03-vague_request,
call-04-vague_request-retry, call-05-interruption_heavy,
call-06-reschedule, call-12-impossible_request, call-13-contradictory_info

**Contrast/control calls (succeeded):** call-07-insurance_hours,
call-08-scheduling-repeat, call-11-first_time_caller

**Details:** Across the majority of real test calls, when the agent
attempted to verify a caller's identity to access their patient record,
the flow consistently failed following this pattern:

1. The agent frequently misidentified the caller (e.g., asking "Am I
   speaking with Maria?") based on the calling phone number, despite
   the caller having already clearly stated a different name.
2. When reading back a caller's phone number for confirmation, the
   agent's speech was garbled and did not form a coherent number
   (e.g., "one three eight eight three seven six five six").
3. The agent stated: "I'm unable to find your record in our system
   right now," and offered to transfer the caller to "patient support."
4. Every observed transfer led to the same automated dead end: "Hello.
   You've reached the Pretty Good AI test line. Goodbye." — not a live
   agent, and not a continuation of the conversation.
5. In no affected call was the caller's original request (scheduling,
   rescheduling, refill, or urgent care) ever resolved.

**Root cause, confirmed via controlled testing:** A call using a
completely fresh identity — Jason Kim, a name never previously used on
the calling phone number — completed the record lookup and full booking
flow successfully on the first attempt, with no errors (call-11). A
repeat call under an already-established identity with an existing
appointment on file also succeeded cleanly (call-08). This confirms the
failure is not a general defect in patient lookup or creation — it
occurs specifically when a phone number has prior call history under
multiple different names, and the agent is unable to disambiguate which
prior identity the current caller is.

**Poor recovery from the failure state:** In call-13, once the lookup
failed, the caller declined an immediate transfer and asked to try
scheduling again. The agent's subsequent responses were inconsistent
and partially self-contradictory — offering to "document the request,"
then in the same turn stating "since I can't create a follow-up record
while support is available, I recommend connecting you to our patient
support team" — before repeating the transfer offer and reaching the
same dead end regardless. This indicates that once the lookup failure
triggers, there is no well-defined recovery path, only a hard funnel
back to a non-functional transfer.

**Real-world relevance:** As a further control, calls with no identity
lookup required at all (general insurance/hours questions, call-07)
succeeded every time, confirming the core pipeline is not the issue —
this is isolated to identity disambiguation specifically. This is a
realistic, common scenario: shared home phones, family members or
caregivers calling on a patient's behalf, or work lines used by
multiple people would all plausibly trigger this same failure in
production.

**Impact:** Any caller sharing a phone number with a prior caller under
a different name is unable to complete scheduling, rescheduling, or
refill requests — core functions of the system — and is routed to a
non-functional dead end instead of a working fallback.

---

## Bug 3: Agent may stall or fail to respond after repeated interruptions

**Severity:** Medium

**Call:** call-10-interruption_heavy

**Details:** When the caller interrupted the agent multiple times in
quick succession (consistent with an impatient/hurried caller persona),
the agent's responses became fragmented mid-sentence, and it eventually
stopped responding altogether — the call ended without the agent
completing its sentence, resolving the request, or saying goodbye. This
suggests the agent's interruption-recovery logic may not gracefully
handle a caller who frequently talks over it, potentially causing the
conversation to silently stall rather than recover or escalate to a
human.

---

## Bug 4: Agent fabricates a date of birth instead of asking the patient

**Severity:** Medium

**Call:** call-01-scheduling

**Details:** When creating a demo patient profile, the agent asked only
for the caller's first and last name, then stated "your date of birth
is July fourth two thousand for demo purposes" — inventing a DOB rather
than asking the patient for their actual one. The caller was never
asked for their real date of birth, even though the persona had one
ready to provide (March 14, 1992). This may be intentional simplified
behavior for the demo environment, but if replicated outside the demo
path, it would result in incorrect patient records.

---

## Minor observation: Caller-stated phone number not cross-checked against actual caller ID

**Severity:** Low

**Call:** call-05-interruption_heavy

**Details:** When asked for a callback number, the caller stated a
number that did not match the actual number the call originated from,
and the agent accepted it without any apparent validation. This is a
minor data-integrity gap rather than a functional failure.

---

## What worked well

For completeness and balance: the agent handled several things
correctly and gracefully across these calls — natural conversational
turn-taking in most calls, correct registration of a mid-call
self-correction (call-13), graceful acceptance of an alternative
appointment slot when the caller's stated preference wasn't available
(call-06), and fully successful, accurate handling of non-identity
questions such as insurance and office hours (call-07, tested twice).