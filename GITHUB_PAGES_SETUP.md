# GitHub Pages Setup Instructions

## Enable GitHub Pages for Melody Player

To activate the interactive melody player:

### Steps:

1. **Go to Repository Settings**
   - Navigate to the repository on GitHub
   - Click "Settings" tab

2. **Enable GitHub Pages**
   - In left sidebar, click "Pages"
   - Under "Source", select "Deploy from a branch"
   - Choose branch: `copilot/reverse-engineer-8051-audio-board`
   - Choose folder: `/ (root)`
   - Click "Save"

3. **Wait for Deployment**
   - GitHub will build and deploy the site
   - Takes 1-2 minutes usually
   - Check the green checkmark in Actions tab

4. **Access the Player**
   - URL will be: `https://cb-embedded.github.io/Mephisto/`
   - Or check the Pages settings for the exact URL

## What You'll See

The melody player includes:
- **10 melody buttons** - One for each extracted sequence
- **Control buttons** - Stop all, test note
- **Real-time channel display** - Shows frequency and amplitude for channels A, B, C
- **Status display** - Current playback information

## Testing the Melodies

1. Click any "Melody X" button to start playback
2. The button will highlight while playing
3. Watch the channel displays update in real-time
4. Use "Stop All" to halt playback
5. Try "Test Note" to verify audio is working

## Technical Details

- **Web Audio API** - Uses OscillatorNode with square waves
- **Direct binary access** - Loads sound_cpu_8051.bin via fetch()
- **Real-time synthesis** - Three simultaneous channels
- **Format parsing** - Extracts [Note_ID] [Duration] [Command] triplets

## Troubleshooting

**No sound?**
- Check browser audio isn't muted
- Try clicking "Test Note" first (A440 for 1 second)
- Check browser console for errors

**Page not loading?**
- Verify GitHub Pages is enabled
- Check deployment status in Actions tab
- Wait a few minutes after enabling

**Wrong melodies?**
- The parser extracts based on pattern analysis
- Some may be data fragments rather than complete songs
- Feedback on which ones sound correct helps validate the format!

## Files Deployed

- `index.html` - Main player page
- `melody-player.js` - JavaScript implementation
- `sound_cpu_8051.bin` - Original firmware (32KB)
- `_config.yml` - Jekyll configuration

## Browser Compatibility

Works in:
- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ⚠️ Requires modern browser with Web Audio API support

---

**Once deployed, test the melodies and provide feedback on the format accuracy!**
