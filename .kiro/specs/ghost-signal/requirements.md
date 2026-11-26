# Requirements: Ghost Signal

## Requirement 1: Ask by SMS
**User story:** As a person with a basic phone and no data, I want to text a question and get a short answer back, so that I can use the web's knowledge without internet.

### Acceptance criteria
1. WHEN an SMS arrives at the Twilio number THE SYSTEM SHALL reply to the sender with one answer.
2. THE SYSTEM SHALL keep every reply within 3 SMS parts.
3. WHEN the question is in Lao or Arabic script THE SYSTEM SHALL reply in that language.
6. WHEN the local-language Wikipedia has no match THE SYSTEM SHALL search English Wikipedia and still reply in the question's language.
4. WHEN no trusted source answers the question THE SYSTEM SHALL reply with a "not found" message instead of guessing.
5. WHEN an answer is given THE SYSTEM SHALL include the source link if it fits.

## Requirement 2: Commands
**User story:** As a user, I want short commands for common needs.

1. WHEN the message is HELP (or empty, ຊ່ວຍ, or مساعدة) THE SYSTEM SHALL reply with usage instructions.
2. WHEN the message is WEATHER <city> (or ອາກາດ / طقس <city>) THE SYSTEM SHALL reply with current weather and tomorrow's forecast, accepting Lao and Arabic city names.
3. WHEN the message is RATE [FROM] [TO...] (or ອັດຕາ / سعر) THE SYSTEM SHALL reply with exchange rates; with one currency it SHALL convert to the sender's local currency (LAK for Lao, EGP for Arabic).

## Requirement 3: Safety and cost
1. WHEN a request to /sms has an invalid Twilio signature THE SYSTEM SHALL reject it with 403.
2. WHEN one sender asks more than 20 questions in an hour THE SYSTEM SHALL reply with a rate-limit message and not search.
3. WHEN a health question is answered THE SYSTEM SHALL advise seeing a health worker.
4. IF a source or the AI fails THEN THE SYSTEM SHALL still send a short apology reply.

## Requirement 4: Try it without a phone
**User story:** As a judge outside Laos, I want to try the service in my browser.

1. THE SYSTEM SHALL serve an old-phone simulator page at `/` that uses the same answer engine.
2. THE simulator SHALL show how many SMS parts and which encoding each reply uses.
