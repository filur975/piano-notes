# Noter

A small desktop app for learning to read notes and find them on the piano. The interface is in Swedish.
It uses only the Python standard library (Tkinter), so there is nothing to `pip install`.

## Run

Needs Python 3.11+ with Tkinter. On Debian/Ubuntu Tkinter may need installing first:
`sudo apt install python3-tk`

```
python3 noter_tk.py
```

Choose a key (C major, D major, B♭ major …), treble clef, bass clef or both, and a direction:

- **Not → tangent**: a note is shown on the staff; click the matching piano key.
- **Tangent → not**: a piano key is highlighted; click where that note is written on the staff.

The key signature applies, so in D major the note on the top treble line (F) is answered with
the F♯ key. Note names are Swedish (H = B natural, B = B♭, Fiss = F♯, Ess = E♭). The range
follows the classic beginner chart: G2–middle C in the bass clef and middle C–G5 in the treble clef.

## Tests

```
python3 -m unittest
```

## Web app (PWA)

`web/` has the same app for the browser, installable on phones, tablets and computers and
usable offline. It is plain HTML, CSS and JavaScript with no build step; the music logic in
`web/notes.js` is a port of `notes.py`. Keep the two in step when changing the rules.

Run it locally (a service worker needs `http://localhost` or HTTPS, so opening the file directly won't work):

```
cd web && python3 -m http.server 8000
```

Then open http://localhost:8000. Tests for the JavaScript port: `cd web && node --test`.

The workflow "Publish web app" publishes `web/` to GitHub Pages on every push to `master`
that touches it. Turn it on once under the repository's Settings → Pages → Source: "GitHub Actions".
The app is then at `https://<user>.github.io/<repo>/`. To install it: in Chrome/Edge use the
install icon in the address bar; on iPhone/iPad open it in Safari → Share → "Lägg till på hemskärmen".
An installed app updates itself in the background, and the new version shows the next time it is opened.

## Windows installer

The GitHub Actions workflow "Build Windows app" (run it manually, or push a tag like `v1.0`)
builds `NoterSetup.exe`. Download it from the run's artifacts and run it on the Windows
computer. It installs Noter for the current user (no admin password needed) and adds a
Start menu entry and an optional desktop icon.

To build locally on Windows instead, run `build_windows.bat` (needs Python 3.11+ and,
for the installer, [Inno Setup 6](https://jrsoftware.org/isdl.php)).
