# Requirements: SMS reminders

## Introduction
People without smartphones have no calendar app. A reminder by SMS (medicine, vaccination day,
market day) is one of the most useful things a basic phone can get.

## Requirement 1: Set a reminder in local time
**User Story:** As a Sender, I want to text "REMIND 8pm take medicine" and get an SMS at 8pm my time, so that I do not forget.
1. WHEN a message starts with a remind word (REMIND, ເຕືອນ, ذكرني, and others) THE SYSTEM SHALL read the time and the task.
2. THE SYSTEM SHALL use the time zone of the Sender's country from the calling code, and say "UTC" when the country is unknown.
3. THE SYSTEM SHALL understand English forms by rules: "8pm", "7:30am", "21:00", "tomorrow 7am", "in 2 hours", "in 15 min".
4. WHEN rules find no time and AI is on THE SYSTEM SHALL ask the AI for the time in local time (any language).
5. WHEN a clock time has already passed today THE SYSTEM SHALL use tomorrow, also across daylight-saving changes.
6. WHEN the time is under 30 seconds away, more than 30 days away or unreadable THE SYSTEM SHALL explain the format with an example.
7. THE SYSTEM SHALL confirm with the due time and the task.

## Requirement 2: See and delete reminders
**User Story:** As a Sender, I want to see and remove my reminders by SMS, so that I stay in control without an app.
1. WHEN the message is "REMIND LIST" THE SYSTEM SHALL list waiting reminders, numbered.
2. WHEN the message is "REMIND DEL <n>" THE SYSTEM SHALL cancel the n-th reminder and confirm.
3. WHEN a Sender already has `GHOST_MAX_REMINDERS` waiting THE SYSTEM SHALL refuse a new one and say how to delete.

## Requirement 3: Delivery
1. WHEN a reminder is due THE SYSTEM SHALL send it once by SMS.
2. WHEN the Sender is a web simulator visitor THE SYSTEM SHALL deliver it to the simulator inbox instead.
3. WHEN the Sender has opted out THE SYSTEM SHALL cancel it.
