from pathlib import Path
import whisper

import shutil, sys
print(shutil.which("ffmpeg") or "FFmpeg not found!")   # quick Python test


# -------- SETTINGS --------
input_dir  = Path(r"C:\Users\alice\Downloads\apocalypse\Audio")
output_dir = Path(r"C:\Users\alice\Downloads\apocalypse\transcripts")
model_size = "base"        # tiny, base, small, medium, large
audio_suffixes = (".m4a",) # add others if you need

# -------- PREP --------
output_dir.mkdir(parents=True, exist_ok=True)
model = whisper.load_model(model_size)

# -------- PROCESS --------
for audio_path in input_dir.glob("*"):            # yields Path objects
    if audio_path.suffix.lower() in audio_suffixes:
        print(f"Transcribing: {audio_path}")
        try:
            result = model.transcribe(str(audio_path))
        except FileNotFoundError:
            print(f"⚠️  Could not open {audio_path}")
            continue

        txt_path = output_dir / (audio_path.stem + ".txt")
        txt_path.write_text(result["text"], encoding="utf-8")
        print(f"  ➜ Saved to {txt_path}")
