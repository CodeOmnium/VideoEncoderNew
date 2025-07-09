import os
import time
import asyncio
import ffmpeg
import httpx
import re
import mimetypes
<<<<<<< HEAD
import json
=======
>>>>>>> 9d8610fafb12bdfee27ef6edc2868b4782a2f8c5
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Load environment variables
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if API_ID == 0:
    raise ValueError("API_ID environment variable is required")
if not API_HASH:
    raise ValueError("API_HASH environment variable is required")

DOWNLOAD_PATH = "downloads/"
PROCESSED_PATH = "processed/"
DOWNLOAD_CHUNK_SIZE = 16 * 1024  # 16 KB
PROGRESS_UPDATE_INTERVAL = 15  # seconds
HTTPX_TIMEOUT = 300  # seconds (5 minutes) - increased for large files

<<<<<<< HEAD
# Video compression settings - now adaptive
TARGET_HEIGHT = 480
OUTPUT_CONTAINER = 'mkv'  # Output container format
PRESET = 'fast'  # Changed from 'ultrafast' to 'fast' for better compression
=======
# Video compression settings
TARGET_HEIGHT = 480
CRF_VALUE = 30
PRESET = 'ultrafast'
REFS = 1
OUTPUT_CONTAINER = 'mkv'  # Output container format
>>>>>>> 9d8610fafb12bdfee27ef6edc2868b4782a2f8c5

# --- Helper Functions ---
def format_bytes(size):
    """Converts bytes to a human-readable format."""
    if size == 0:
        return "0B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size >= power and n < len(power_labels) -1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def get_video_info(file_path):
    """Get video information using ffprobe."""
    try:
        probe = ffmpeg.probe(file_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

        if not video_stream:
            return None

        # Get video properties
        duration = float(probe['format']['duration'])
        bitrate = int(probe['format']['bit_rate'])
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        fps = eval(video_stream['r_frame_rate'])  # Convert fraction to float

        return {
            'duration': duration,
            'bitrate': bitrate,
            'width': width,
            'height': height,
            'fps': fps,
            'size': int(probe['format']['size'])
        }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def calculate_compression_settings(video_info, target_size_reduction=0.6):
    """Calculate optimal compression settings based on video characteristics."""
    if not video_info:
        # Fallback to aggressive settings
        return {
            'crf': 32,
            'maxrate': '1000k',
            'bufsize': '2000k',
            'preset': 'fast'
        }

    duration = video_info['duration']
    original_bitrate = video_info['bitrate']
    width = video_info['width']
    height = video_info['height']

    # Calculate target bitrate for desired size reduction
    target_bitrate = int(original_bitrate * (1 - target_size_reduction))

    # Adaptive CRF based on video characteristics
    if duration > 3600:  # > 1 hour
        crf = 35  # More aggressive for very long videos
        target_bitrate = min(target_bitrate, 800000)  # Max 800kbps
    elif duration > 1800:  # > 30 minutes
        crf = 33  # Aggressive for long videos
        target_bitrate = min(target_bitrate, 1200000)  # Max 1200kbps
    elif duration > 600:  # > 10 minutes
        crf = 31  # Moderate for medium videos
        target_bitrate = min(target_bitrate, 1500000)  # Max 1500kbps
    else:
        crf = 28  # Less aggressive for short videos
        target_bitrate = min(target_bitrate, 2000000)  # Max 2000kbps

    # Adjust based on resolution
    if height > 720:  # High resolution source
        crf += 2  # More aggressive
    elif height < 480:  # Low resolution source
        crf -= 2  # Less aggressive

    # Ensure reasonable bounds
    crf = max(23, min(40, crf))  # CRF between 23-40
    target_bitrate = max(300000, min(3000000, target_bitrate))  # Between 300k-3M

    maxrate = f"{target_bitrate // 1000}k"
    bufsize = f"{target_bitrate * 2 // 1000}k"

    return {
        'crf': crf,
        'maxrate': maxrate,
        'bufsize': bufsize,
        'preset': 'fast'
    }

async def send_progress_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, start_time: float, current_size: int, total_size: int, action: str, force: bool = False):
    """Sends or edits a progress message, but only if enough time has passed or if forced."""
    now = time.time()
    # Get the last update time from context, default to 0 if not set
    last_update = context.bot_data.get((chat_id, message_id, 'last_update'), 0)

    # Only send an update if the interval has passed or if it's a forced update (e.g., for completion messages)
    if not force and (now - last_update) < PROGRESS_UPDATE_INTERVAL:
        return

    # Update the last update time
    context.bot_data[(chat_id, message_id, 'last_update')] = now

    elapsed_time = now - start_time
    speed = current_size / elapsed_time if elapsed_time > 0 else 0
    progress = (current_size / total_size) * 100 if total_size > 0 else 0

    message = (
        f"**{action}**\n"
        f"Progress: {progress:.1f}%\n"
        f"[{'█' * int(progress // 5)}{' ' * (20 - int(progress // 5))}]\n"
        f"{format_bytes(current_size)} / {format_bytes(total_size)}\n"
        f"Speed: {format_bytes(speed)}/s\n"
        f"Elapsed: {elapsed_time:.2f}s"
    )

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message)
    except Exception:
        pass # Ignore if message not found or not modified

# --- Core Logic ---

async def download_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, telethon_message, file_path: str):
    """Downloads a video using Telethon with throttled progress updates."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Starting download...")
    start_time = time.time()

    telethon_client = context.bot_data['telethon_client']
    total_size = telethon_message.file.size

    # The progress_callback for Telethon
    async def progress_callback(current_bytes, total_bytes):
        await send_progress_message(context, chat_id, message_id, start_time, current_bytes, total_bytes, "Downloading")

    await telethon_client.download_media(telethon_message.media, file=file_path, progress_callback=progress_callback)

    # Ensure the final "Download Complete" message is sent
    await send_progress_message(context, chat_id, message_id, start_time, total_size, total_size, "Download Complete", force=True)

async def compress_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, input_path: str, output_path: str):
<<<<<<< HEAD
    """Compresses a video using adaptive settings based on video characteristics."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Analyzing video...")

    # Get video information
    video_info = get_video_info(input_path)
    if not video_info:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Error: Could not analyze video file.")
        raise Exception("Could not analyze video file")

    # Calculate optimal compression settings
    settings = calculate_compression_settings(video_info)

    # Show compression plan to user
    duration_str = f"{int(video_info['duration']//60)}m {int(video_info['duration']%60)}s"
    original_size = format_bytes(video_info['size'])

    plan_message = (
        f"**Compression Plan:**\n"
        f"Duration: {duration_str}\n"
        f"Original size: {original_size}\n"
        f"CRF: {settings['crf']}\n"
        f"Max bitrate: {settings['maxrate']}\n"
        f"Starting compression to MKV..."
    )

    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=plan_message)

    try:
        # Build FFmpeg command with adaptive settings
        input_stream = ffmpeg.input(input_path)

        # Video filter for scaling
        video_filter = f'scale=-2:{TARGET_HEIGHT}'

        # Output with adaptive settings
        output_stream = ffmpeg.output(
            input_stream,
            output_path,
            vf=video_filter,
            vcodec='libx264',
            preset=settings['preset'],
            crf=settings['crf'],
            maxrate=settings['maxrate'],
            bufsize=settings['bufsize'],
            acodec='aac',
            strict='experimental',
            pix_fmt='yuv420p',
            movflags='+faststart',  # Optimize for streaming
            format='matroska'  # Force MKV container
=======
    """Compresses a video using a fast, CRF-based method and outputs in MKV container format."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Compressing video to MKV format... This may take a few minutes.")

    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, 
                    vf=f'scale=-2:{TARGET_HEIGHT}', 
                    vcodec='libx264', 
                    preset=PRESET, 
                    crf=CRF_VALUE, 
                    acodec='aac', 
                    strict='experimental', 
                    pix_fmt='yuv420p',
                    refs=REFS,  # Fixed: Use 'refs' instead of 'x264-params'
                    format='matroska'  # Force MKV (Matroska) container format
                   )
            .run(overwrite_output=True)
>>>>>>> 9d8610fafb12bdfee27ef6edc2868b4782a2f8c5
        )

        # Run compression
        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr output from FFmpeg."
        print(f"FFmpeg error:\n{stderr}")
        error_message = f"Error processing video. The file might be corrupted or in an unsupported format."
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=error_message)
        raise

    # Check output file size and show results
    try:
        output_size = os.path.getsize(output_path)
        compression_ratio = (1 - output_size / video_info['size']) * 100

        result_message = (
            f"**Compression Complete!**\n"
            f"Original: {format_bytes(video_info['size'])}\n"
            f"Compressed: {format_bytes(output_size)}\n"
            f"Reduction: {compression_ratio:.1f}%\n"
            f"Starting upload..."
        )

        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=result_message)
    except Exception:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Compression complete. Starting upload...")

async def upload_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, file_path: str):
    """Uploads a video to the chat using Telethon with throttled progress updates."""
    await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Starting upload...")

    telethon_client = context.bot_data['telethon_client']

    # Get file size for progress updates
    file_size = os.path.getsize(file_path)
    start_time = time.time()

    # The progress_callback for Telethon
    async def progress_callback(current_bytes, total_bytes):
        await send_progress_message(context, chat_id, message_id, start_time, current_bytes, total_bytes, "Uploading")

    await telethon_client.send_file(chat_id, file_path, progress_callback=progress_callback, attributes=[DocumentAttributeVideo(duration=0, w=0, h=0, supports_streaming=True)])

    # Ensure the final "Upload Complete" message is sent
    await send_progress_message(context, chat_id, message_id, start_time, file_size, file_size, "Upload Complete!", force=True)

# --- Command & Message Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    await update.message.reply_text(
<<<<<<< HEAD
        "Hi! I'm an intelligent video compressor bot.\n\n"
        "Send me a video, and I'll compress it to 480p in MKV format.\n"
        "I automatically analyze your video and choose the best compression settings!\n\n"
        "Features:\n"
        "• Adaptive compression based on video length and quality\n"
        "• Guaranteed size reduction (or I'll use more aggressive settings)\n"
        "• MKV format for better compression and compatibility"
=======
        "Hi! I'm a video compressor bot.\n\n"
        "Send me a video, and I'll compress it to 480p in MKV format for you.\n"
        "MKV format provides better compression and compatibility!"
>>>>>>> 9d8610fafb12bdfee27ef6edc2868b4782a2f8c5
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The main handler for receiving and processing videos."""
    chat_id = update.message.chat_id
    status_message = await update.message.reply_text("Initializing...")
    message_id = status_message.message_id

    telethon_client = context.bot_data['telethon_client']
    telethon_message = await telethon_client.get_messages(chat_id, ids=update.message.message_id)

    if not telethon_message or not telethon_message.file:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Sorry, I couldn't retrieve the file from this message.")
        return

    # --- Super Robust Filename Handling ---
    # 1. Get the reliable extension from the mime type
    mime_type = telethon_message.file.mime_type
    ext = mimetypes.guess_extension(mime_type) or '.mp4' # Default to .mp4

    # 2. Get the base filename, or create one if it doesn't exist
    original_filename = telethon_message.file.name
    if original_filename:
        base_name = os.path.splitext(original_filename)[0]
    else:
        base_name = f"video_{time.strftime('%Y-%m-%d_%H-%M-%S')}"

    # 3. Sanitize the base name
    sanitized_base_name = re.sub(r'[\/*?:"<>|&]', "", base_name)
    sanitized_base_name = re.sub(r'\s+', '_', sanitized_base_name)
    sanitized_base_name = sanitized_base_name.strip('_. ')

    # 4. Combine sanitized base name and reliable extension (force MKV output)
    safe_filename = f"{sanitized_base_name}{ext}"

    input_path = os.path.join(DOWNLOAD_PATH, safe_filename)
    # Force MKV output format
<<<<<<< HEAD
    output_filename = f"compressed_{sanitized_base_name}.{OUTPUT_CONTAINER}"
=======
    output_filename = f"processed_{sanitized_base_name}.{OUTPUT_CONTAINER}"
>>>>>>> 9d8610fafb12bdfee27ef6edc2868b4782a2f8c5
    output_path = os.path.join(PROCESSED_PATH, output_filename)

    try:
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        os.makedirs(PROCESSED_PATH, exist_ok=True)

        await download_video(context, chat_id, message_id, telethon_message, input_path)
        await compress_video(context, chat_id, message_id, input_path, output_path)
        await upload_video(context, chat_id, message_id, output_path)

    except Exception as e:
        print(f"An error occurred: {e}")
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"An unexpected error occurred. Please try again later.")
    finally:
        # --- Cleanup ---
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles non-video messages."""
    await update.message.reply_text("Please send me a video file to compress.")

# --- Keep-Alive Web Server ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Intelligent Video Compressor Bot is alive!"

def run_web_server():
    # Render provides the PORT environment variable
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":

    # Start the keep-alive web server in a separate thread
    keep_alive_thread = Thread(target=run_web_server)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    print("Keep-alive server started.")

    async def main():
        # Initialize Telethon client with a long timeout and start it
        telethon_client = TelegramClient(
            'bot_session', 
            API_ID, 
            API_HASH,
            connection_retries=5,
            timeout=3600
        )
        await telethon_client.start(bot_token=TELEGRAM_BOT_TOKEN)
        print("Telethon client started.")

        # Build the python-telegram-bot application
        # Set high timeouts to prevent issues on slow networks or with large files
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .http_version("1.1")
            .get_updates_http_version("1.1")
            .connect_timeout(3600.0)
            .read_timeout(3600.0)
            .write_timeout(3600.0)
            .pool_timeout(3600.0)
            .get_updates_read_timeout(3600.0)
            .get_updates_connect_timeout(3600.0)
            .build()
        )

        # Add the Telethon client to the bot's context data
        application.bot_data['telethon_client'] = telethon_client

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.VIDEO, handle_video))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))

        # Run the bot until the user presses Ctrl-C
        print("Starting bot polling...")
        async with application:
            await application.initialize()
            await application.start()
            await application.updater.start_polling()

            # Keep the script running until it's stopped
            while True:
                await asyncio.sleep(3600)

    # Run the main async function
    asyncio.run(main())
