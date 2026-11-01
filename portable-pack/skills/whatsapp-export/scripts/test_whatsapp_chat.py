import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from whatsapp_chat import parse  # noqa: E402

SCRIPT = Path(__file__).parent / "whatsapp_chat.py"


def test_ios_export_with_attachment_and_multiline():
    text = (
        "[05/09/2026, 14:03:12] Maria Berg: Offer sent to the client\n"
        "second line of the same message\n"
        "[13/09/2026, 09:00:00] Alex: ‎<attached: 00000012-PHOTO-2026-09-13-09-00-00.jpg>\n"
        "[13/09/2026, 09:05:00] Alex: ‎Messages and calls are end-to-end encrypted.\n"
    )
    messages = parse(text)
    assert messages[0] == {
        "time": "2026-09-05T14:03",
        "author": "Maria Berg",
        "text": "Offer sent to the client\nsecond line of the same message",
    }
    assert messages[1]["attachment"] == "00000012-PHOTO-2026-09-13-09-00-00.jpg"
    assert messages[1]["time"] == "2026-09-13T09:00"


def test_android_12_hour_month_first_and_system_lines():
    text = (
        "9/1/26, 10:15 PM - Messages and calls are end-to-end encrypted.\n"
        "9/1/26, 10:16 PM - Sam: IMG-20260901-WA0001.jpg (file attached)\n"
        "9/30/26, 12:05 AM - Kim: Deadline moved to Friday\n"
    )
    messages = parse(text)
    assert messages[0]["author"] is None
    assert messages[1]["time"] == "2026-09-01T22:16"
    assert messages[1]["attachment"] == "IMG-20260901-WA0001.jpg"
    assert messages[2]["time"] == "2026-09-30T00:05"


def test_android_24_hour_days_first_from_decreasing_days():
    text = "03.10.26, 08:00 - A: one\n01.11.26, 09:30 - B: two\n"
    assert [m["time"] for m in parse(text)] == ["2026-10-03T08:00", "2026-11-01T09:30"]


def test_zip_copies_media_without_overwriting_and_links_it():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        chat = root / "WhatsApp Chat - Site team.zip"
        with zipfile.ZipFile(chat, "w") as archive:
            archive.writestr("_chat.txt", "[05/09/2026, 14:03:12] Maria: ‎<attached: 00000001-plan.pdf>\n")
            archive.writestr("00000001-plan.pdf", b"%PDF-1.4 plan")
        (root / "WhatsApp Chat - Site team files").mkdir()
        (root / "WhatsApp Chat - Site team files" / "00000001-plan.pdf").write_bytes(b"older")
        result = subprocess.run([sys.executable, str(SCRIPT), str(chat), "--json"], capture_output=True, text=True, check=True)
        message = json.loads(result.stdout)[0]
        saved = Path(message["file"])
        assert saved.name == "00000001-plan (2).pdf"
        assert saved.read_bytes() == b"%PDF-1.4 plan"
        assert (root / "WhatsApp Chat - Site team files" / "00000001-plan.pdf").read_bytes() == b"older"
