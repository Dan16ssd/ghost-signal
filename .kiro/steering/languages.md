---
inclusion: fileMatch
fileMatchPattern: "ghost_signal/{lang,answer,reminders}.py"
---
# Languages

- Launch languages, hand-written: English, Lao (Danny reviews), Arabic (Mohamed reviews).
  Every fixed message key exists in all three (a test checks this).
- Other languages: the fixed message is AI-translated once and cached; English when AI is off.
- Detection order: the text's script -> common Latin words -> the sender's country -> English.
  The country only breaks ties (Arabic vs Persian letters, Latin text with no common words).
- Search the question's own Wikipedia first; if it does not answer, turn the question into
  English keywords and search English Wikipedia, but always reply in the question's language.
- Command words: the English word always works everywhere; add local words for big languages.
- Arabic replies are right-to-left with Latin commands and digits inside: keep commands short.
