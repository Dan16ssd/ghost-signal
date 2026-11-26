# Requirements: medicine reminder calls

## Introduction
Older people living alone often forget medicine, and many only have a basic phone. A phone call
is easier than reading an SMS. Ghost Signal calls them every day, asks them to press 1, and if
they do not answer twice, texts a family member they chose.

## Glossary
- **Person**: the phone number that set up the medicine (the only number Ghost Signal calls).
- **Dose**: one planned call for one medicine at one local time.
- **Family contact**: a number the Person named that replied YES.

## Requirement 1: Set daily medicine calls
**User Story:** As an older person, or a child setting it up for a parent, I want to text "MEDS 8am 8pm blood pressure pill", so that the phone rings every day at those times.
1. WHEN a message starts with a medicine word (MEDS, ຢາ, دواء and others) THE SYSTEM SHALL read 1 to 4 daily times and the medicine name, by rules for English times and by AI for other languages.
2. THE SYSTEM SHALL use the time zone of the Person's country.
3. WHEN the message is "MEDS in N min <medicine>" THE SYSTEM SHALL place the first call N minutes from now and repeat daily at that time (for demos).
4. THE SYSTEM SHALL allow at most 3 medicines per Person, with MEDS LIST and MEDS DEL <n>.

## Requirement 2: The call
**User Story:** As a Person, I want a short call in my language that I answer with one key, so that it works on any phone.
1. WHEN a dose is due THE SYSTEM SHALL call only the Person's own number.
2. THE call SHALL say the medicine time, the medicine name and "press 1 when you have taken it" in the Person's language.
3. WHERE no voice exists for Lao THE SYSTEM SHALL speak Thai, with the medicine name translated to Thai by AI (or left out when AI is off).
4. WHERE no voice exists for the Person's language THE SYSTEM SHALL send the reminder by SMS instead and say so when the medicine is set.
5. WHEN the Person presses 1, or texts 1 / OK / TAKEN while a dose is open, THE SYSTEM SHALL mark the dose taken and plan the next one.

## Requirement 3: Retry and family alert
**User Story:** As a family member far away, I want an SMS if my mother misses her medicine, so that I can check on her.
1. WHEN a call gets no 1 THE SYSTEM SHALL call again 10 minutes later.
2. WHEN two calls get no 1 THE SYSTEM SHALL mark the dose missed and send each accepted Family contact an SMS with the Person's number and the medicine.
3. WHEN the Person sends "MEDS FAMILY <+number>" THE SYSTEM SHALL text that number an invitation; alerts SHALL start only after it replies YES.
4. THE SYSTEM SHALL never call a Family contact.

## Requirement 4: Safety and cost
1. WHEN the Person or a Family contact sends STOP THE SYSTEM SHALL stop all their calls and texts.
2. THE SYSTEM SHALL cap calls per day for everyone together (`GHOST_MAX_CALLS_PER_DAY`) and fall back to SMS above it.
3. WHEN Twilio calls the voice pages THE SYSTEM SHALL check the Twilio signature.

## Requirement 5: Try it in the simulator
1. WHEN a simulator visitor's dose is due THE simulator phone SHALL ring and show what the voice says, with Press 1 and Ignore.
