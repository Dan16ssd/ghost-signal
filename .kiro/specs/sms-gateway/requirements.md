# Requirements: SMS gateway (safety, cost, carrier rules)

## Introduction
The Twilio webhook is the front door. Every SMS and AI call costs money, carriers require
opt-out handling, and Twilio may deliver the same webhook twice.

## Glossary
- **Sender**: the phone number in Twilio's `From` field.
- **Opted out**: a Sender who sent STOP and not START since.
- **AI budget**: the number of AI calls allowed per UTC day for all Senders together.

## Requirement 1: STOP always wins
**User Story:** As a Sender, I want STOP to end all texts from Ghost Signal, so that I am never texted after I opt out.
1. WHEN a message is exactly one stop word (STOP, STOPALL, UNSUBSCRIBE, END, QUIT, CANCEL, ຢຸດ, توقف, إيقاف) THE SYSTEM SHALL mark the Sender opted out, cancel the Sender's waiting reminders and confirm in the Sender's language.
2. WHILE a Sender is opted out THE SYSTEM SHALL send nothing to that Sender, including reminders and rate-limit replies.
3. WHEN an opted-out Sender sends one start word (START, UNSTOP, ເລີ່ມ, ابدأ) THE SYSTEM SHALL opt them back in and confirm.
4. WHEN a stop word appears inside a longer message THE SYSTEM SHALL treat the message as a question.

## Requirement 2: Answer each message once
**User Story:** As a Sender, I want one answer per question, so that I do not pay for duplicates.
1. WHEN a webhook arrives with a MessageSid already seen THE SYSTEM SHALL reply with empty TwiML and do no work.

## Requirement 3: Cost caps
**User Story:** As the operator, I want spending limits, so that a flood of texts cannot empty the balance.
1. WHEN a Sender has asked `GHOST_MAX_PER_HOUR` questions in the last hour THE SYSTEM SHALL reply with the rate-limit message and not search.
2. WHEN the AI budget for the day is used THE SYSTEM SHALL answer with plain source extracts instead of AI, without an error.
3. THE SYSTEM SHALL keep limits, opt-outs and seen MessageSids across restarts.

## Requirement 4: Privacy
1. THE SYSTEM SHALL NOT store or log message texts, except the words of a reminder the Sender asked to keep.
2. THE SYSTEM SHALL mask phone numbers in logs.

## Requirement 5: Operations
1. THE SYSTEM SHALL expose `/health` with version, Twilio and AI status, and today's questions, AI calls and waiting reminders.
