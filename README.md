# Smart Telegram Video Compressor Bot

A powerful and intelligent Telegram bot that dramatically reduces video file sizes. Inspired by the efficiency of popular compression bots, this tool is optimized for speed and effectiveness, making it perfect for personal use or deployment on services like Replit and Render.

## Key Features

- **Intelligent Compression:** Uses a fast, single-pass CRF (Constant Rate Factor) method with aggressive settings (`crf=30`, `ref=1`) to significantly reduce file size while maintaining 480p quality.
- **MKV Container Format:** Outputs videos in MKV (Matroska) format for better compression efficiency and wider codec compatibility.
- **High-Speed Encoding:** The FFmpeg parameters are heavily optimized for speed, allowing it to process long videos in a fraction of the time of standard configurations.
- **Robust File Handling:** Automatically handles a wide variety of video formats and corrects for unreliable or malformed filenames sent by Telegram clients.
- **Real-Time Progress:** Provides clear, throttled status updates on downloading, compressing, and uploading to avoid API rate limits.
- **Large File Support:** Built with `telethon` for its superior handling of large file downloads and uploads.
- **24/7 Hosting Ready:** Includes a lightweight Flask web server to support "keep-alive" services, essential for free-tier hosting platforms.
- **Recovery Script:** Comes with a `recover.py` utility to manually re-process a video if the bot is interrupted.

## How It Works

1.  A user sends any video to the bot.
2.  The bot downloads the video, sanitizing the filename to prevent errors.
3.  It uses **FFmpeg** with a highly-optimized CRF strategy to compress the video to 480p, saving the result in MKV format to a temporary directory.
4.  The bot uploads the newly compressed, much smaller MKV video back to the user.
5.  All temporary files are automatically deleted to conserve disk space.

## Why MKV Format?

- **Better Compression:** MKV container can achieve smaller file sizes compared to MP4 with the same quality
- **Wider Codec Support:** MKV supports more video and audio codecs, providing better flexibility
- **No Patent Issues:** MKV is completely open-source and patent-free
- **Better Streaming:** Improved streaming capabilities and chapter support
- **Future-Proof:** More modern container format with better metadata support

## Quickstart: Deploying on Replit

This bot is pre-configured for a seamless experience on Replit.

1.  **Fork the Repository:** Click the "Fork" button on this GitHub page to create your own copy.
2.  **Create a Replit Account:** If you don't have one, sign up at [Replit.com](https://replit.com).
3.  **Import from GitHub:** On your Replit dashboard, click **"Create Repl"** and then use the **"Import from GitHub"** option to import your forked repository.
4.  **Configure Secrets:**
    - In the Replit workspace, go to the **"Secrets"** tab in the left-hand menu.
    - Add the following three secrets. You can get these from [my.telegram.org](https://my.telegram.org) and by talking to [@BotFather](https://t.me/BotFather) on Telegram.
      - `TELEGRAM_BOT_TOKEN` = `Your bot token here`
      - `API_ID` = `Your API ID here`
      - `API_HASH` = `Your API hash here`
5.  **Run the Bot:**
    - Click the main **"Run"** button at the top. Replit will automatically install all dependencies (including FFmpeg) and start the bot.
    - Your bot is now live and will output compressed videos in MKV format!

### Keeping the Bot Alive (24/7)

To keep your bot running on Replit's free tier, you need to use a "keep-alive" service.

1.  When you run the bot, a web view will open in your Replit workspace. Copy the URL from the address bar.
2.  Sign up for a free monitoring service like [UptimeRobot](https://uptimerobot.com/).
3.  In UptimeRobot, create a new "HTTP(s)" monitor and paste the URL from your Replit web view. Set it to ping your bot every 5-10 minutes.

This will ensure your bot stays awake and responsive 24/7.

## Local Installation

If you prefer to run the bot on your own machine:

```bash
# Clone your forked repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# Create and activate a Python virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# .\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Create a .env file and add your API credentials
# (See "Configure Secrets" in the Replit section above)

# Make sure you have FFmpeg installed on your system
# (e.g., 'sudo apt install ffmpeg' on Debian/Ubuntu)

# Run the bot
python main.py
```

## Configuration Options

You can customize the compression settings by modifying these constants in `main.py`:

```python
# Video compression settings
TARGET_HEIGHT = 480        # Output resolution height
CRF_VALUE = 30            # Compression quality (lower = better quality, larger file)
PRESET = 'ultrafast'      # Encoding speed preset
REFS = 1                  # Reference frames (lower = faster encoding)
OUTPUT_CONTAINER = 'mkv'  # Output container format
```

## Supported Input Formats

The bot can handle virtually any video format that FFmpeg supports, including:
- MP4, AVI, MOV, WMV, FLV, MKV, WEBM
- Various codecs: H.264, H.265, VP8, VP9, etc.
- All outputs are converted to H.264 video + AAC audio in MKV container

## File Size Comparison

Typical compression results with MKV format:
- 1GB input → 200-400MB output (depending on content)
- 500MB input → 100-200MB output  
- 100MB input → 20-50MB output

*Results may vary based on video content, duration, and original quality.*