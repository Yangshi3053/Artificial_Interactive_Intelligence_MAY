import os
import subprocess


def play_wav(path):
    """Play a WAV file with the simplest available local audio tool."""
    if os.name == "nt":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return True

    players = [
        ["afplay", str(path)],
        ["aplay", str(path)],
        ["paplay", str(path)],
    ]

    for command in players:
        try:
            subprocess.run(command, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    return False
