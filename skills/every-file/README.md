# Every file

Not a skill an agent loads: the floor the app checks on every Word, Excel and PowerPoint file a turn
writes, whichever agent or pack made it. The rules are the every-file guideline
(`standards/guidelines/every-file/1.1.0`): at most two font families, no text cut off, enough
contrast (WCAG 2.2), formulas with saved results, a title and alternative text, no text hidden under
a picture. A red check goes back to the agent in the same chat, three times at most.

    python3 skills/_checks/packcheck.py every-file <file>
