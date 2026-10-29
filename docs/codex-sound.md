# Codex and Herdr notification sound

`scripts/codex-soft-chime.py` renders a 0.8-second stereo chime with a rounded
onset, lightly detuned sine tones, and a fading shimmer. Its peak is -30 dBFS,
22 dB below the shipped `codex-notification.wav`. System volume stays unchanged.

The current Linux package bundles the sound in `/usr/lib/chatgpt/resources`.
Generate and install the replacement from the repository root:

```sh
python3 scripts/codex-soft-chime.py /tmp/codex-soft-chime.wav
sudo cp -n /usr/lib/chatgpt/resources/codex-notification.wav /usr/lib/chatgpt/resources/codex-notification.wav.original
sudo install -m 644 /tmp/codex-soft-chime.wav /usr/lib/chatgpt/resources/codex-notification.wav
```

An app update can replace the sound; rerun these commands afterwards. If Codex
has cached the original audio, restart it when convenient. The alternate Classic
sound is unchanged. To restore the original notification:

```sh
sudo cp /usr/lib/chatgpt/resources/codex-notification.wav.original /usr/lib/chatgpt/resources/codex-notification.wav
```

Herdr uses the same chime via `[ui.sound].path` in its managed config.
The MP3 is stored at `native/home/files/.config/herdr/sounds/soft-chime.mp3`. Regenerate it
after changing the synthesis script:

```sh
ffmpeg -y -i /tmp/codex-soft-chime.wav -codec:a libmp3lame -q:a 2 native/home/files/.config/herdr/sounds/soft-chime.mp3
dotjik apply
herdr server reload-config
```

This applies to both finished and needs-attention sounds and survives Herdr updates.
