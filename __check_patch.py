from pathlib import Path

path = Path("patches") / "20250918-path-config.diff"
text = path.read_text(encoding="utf-8")
print("toir", "toir_raspredelenije.py" in text)
