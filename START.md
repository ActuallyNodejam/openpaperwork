# START.md — set OpenPaperwork up and make the sample invoice

Someone pasted the install prompt from the README into their agent, and that agent is now reading
this file. Work through the steps in order and finish on the check. Never ask the person to paste
an API key into the chat, and never write a key into a file. Nothing here sends anything anywhere;
the sample invoice stays in its folder.

## 1. Add the library

**You are Claude Code** (you have the `/plugin` command). Add the marketplace and install the
library:

```text
/plugin marketplace add ActuallyNodejam/openpaperwork
/plugin install openpaperwork
```

On first use the plugin sets up its own Python: at its first session start it installs
requirements.txt and Chromium once, into the plugin's own data folder, and prints one line for the
person to run with `sudo` if poppler is missing. Show such a line and let them run it; everything
else is automatic.

**You are another agent** (Codex in the ChatGPT app or the command line, Cursor, Antigravity or
another agent that reads Agent Skills). In the folder you are working in, add the skills:

```sh
npx skills add ActuallyNodejam/openpaperwork
```

The packs' scripts need Python 3.10 or later and a few packages, set up once. From a clone of this
repository:

```sh
sh portable-pack/install.sh
sh portable-pack/doctor.sh --fix
. .venv/bin/activate
```

Run the doctor again until it prints `Ready`, and keep working from that shell. If you cannot
run `npx`, the install script alone links every pack into `~/.agents/skills`.

## 2. Make the sample invoice

In a new, empty folder, write `notes.txt` with exactly this content:

```text
Faktura att skicka

Vi: Exempel Mätteknik AB, Exempelvägen 12, 753 20 Uppsala. Org.nr 556000-2106, styrelsens säte Uppsala.
Momsreg.nr SE556000210601. Godkänd för F-skatt. Bankgiro 5000-1007.
Tel 018-000 00 00, ekonomi@exempel-matteknik.example

Kund: Exempel Industri AB, Provvägen 5, 721 30 Västerås. Org.nr 556000-3104.
Deras referens: Karin Lund på inköp, beställning 4471.

Fakturanummer 2026-1187, fakturadatum 9 oktober 2026.
Levererat den fjortonde september 2026.
Vad vi levererade:
- Kalibrering av tryckgivare, 18 st à 640,00 kr. På den raden 10 % volymrabatt.
- Reservdelssats TG-2, 6 st à 1 275,00 kr
- Frakt, 390,00 kr
Alla priser exklusive moms, moms 25 % på allt.
Kunden betalade 8 000 kr i förskott den 31 augusti, det ska dras av på det som ska betalas.
Betalningsvillkor: 30 dagar netto.
```

The names and numbers are invented; this is the case in the README's before-and-after pictures.

**In Claude Code**, start the invoice workflow in that folder:

    /openpaperwork:invoice

**In the other agents**, follow the `e-invoice` skill on that folder and do what it says for a
Swedish invoice.

The invoice comes out beside `notes.txt` as a PDF with its XML file.

## 3. End on the check

The check is the finish line. In Claude Code the plugin runs it before the turn ends; in the other
agents, run it as the skill says:

    python3 <the skills folder>/_checks/packcheck.py e-invoice <your output>

Keep fixing what a FAIL line names and running the check again, at most three times, until it
prints `pack check clean`. A WARN line on a clean run belongs in your reply.

Then report, one short line each: what was installed, what was made, what the check said, and
anything that needs the person (a `sudo` line). Do not send the invoice anywhere.
