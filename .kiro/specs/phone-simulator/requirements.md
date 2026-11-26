# Requirements: phone simulator

## Introduction
Judges and visitors cannot all text a US number. The simulator lets anyone try Ghost Signal in
a browser, as if on an old button phone, using the same engine as SMS.

## Requirement 1: Feels like a button phone
**User Story:** As a judge, I want to type like on a button phone, so that I feel what a real Sender does.
1. THE simulator SHALL show an old phone with a green LCD and a 12-key multi-tap keypad (2 = ABC, 0 = space).
2. WHEN the same key is tapped again within 0.9 s THE simulator SHALL cycle the letter instead of adding one.
3. THE simulator SHALL also accept typing from the computer keyboard.

## Requirement 2: Texting from any country
1. THE simulator SHALL let the visitor choose the country they are "texting from"; language hint, currency and time zone follow it.
2. Example buttons SHALL show Laos, the Philippines and other countries, including a reminder due in 1 minute.

## Requirement 3: Honest about SMS cost
1. EACH reply SHALL show its number of SMS parts and the encoding (GSM-7 or UCS-2).

## Requirement 4: Mischief that guides
1. WHILE waiting THE simulator SHALL show a floating ghost; after each reply a hint line SHALL say what to try next.
2. WHEN a reminder comes due THE simulator SHALL show it as a new SMS.

## Requirement 5: Accessible
1. Keys SHALL have labels, focus SHALL be visible, new messages SHALL be announced, Arabic SHALL read right to left, and motion SHALL stop with reduced-motion settings.
