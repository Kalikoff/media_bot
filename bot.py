import asyncio
import os
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MAX_FILE_SIZE = 50 * 1024 * 1024

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def download_video(url: str, output_dir: str) -> dict | None:
    """Скачивает видео в указанную директорию, возвращает инфо или None"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-us,en;q=0.9',
        },
    }
    
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(
            None,
            lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=True)
        )
        return info
    except Exception as e:
        print(f"Download error: {e}")
        return None


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Отправь ссылку на видео (YouTube, Instagram, TikTok и т.д.)")


@dp.message(F.text)
async def handle_link(message: types.Message):
    url = message.text.strip()
    
    if not url.startswith(("http://", "https://")):
        return
    
    status_msg = await message.answer("⏳ Скачиваю видео...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        info = await download_video(url, tmpdir)
        
        if not info:
            await status_msg.edit_text("❌ Не удалось скачать видео. Проверь ссылку.")
            return
        
        filepath = Path(tmpdir) / f"{info['id']}.mp4"
        if not filepath.exists():
            files = list(Path(tmpdir).glob(f"{info['id']}.*"))
            if files:
                filepath = files[0]
            else:
                await status_msg.edit_text("❌ Файл не найден после скачивания.")
                return
        
        file_size = filepath.stat().st_size
        
        if file_size > MAX_FILE_SIZE:
            await status_msg.edit_text(
                f"⚠️ Видео слишком большое ({file_size // (1024*1024)} MB). "
                f"Telegram ограничивает отправку до 50 MB."
            )
            return
        
        try:
            await status_msg.delete()
            await message.answer_video(
                video=FSInputFile(filepath),
                caption=None,
                supports_streaming=True
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())