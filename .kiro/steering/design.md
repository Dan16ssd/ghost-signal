---
inclusion: fileMatch
fileMatchPattern: "ghost_signal/static/**"
---
# Simulator design

- It is an old button phone: green LCD, monospace text, multi-tap keypad (2 = ABC). Typing on
  the computer keyboard also works.
- "Scare me, then make it easy": one ghost touch per screen (the floating ghost while waiting,
  a playful hint line), but every hint says what to do next.
- Each reply shows its SMS cost: number of parts and encoding.
- Accessibility: every key has a label, visible focus outline, `aria-live` on the message log,
  `dir="auto"` so Arabic reads right to left, motion off with `prefers-reduced-motion`,
  contrast of at least 4.5:1 on the LCD.
- Works at phone width (judges open it on their phones).
