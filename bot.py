import os
import re
import asyncio
import tempfile
import shutil
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import yt_dlp
from shazamio import Shazam

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Har bir foydalanuvchi uchun vaqtinchalik ma'lumot (link + platforma)
pending = {}

def extract_url(text: str):
    """Matndan birinchi URL ni ajratib oladi"""
    match = re.search(r'https?://\S+', text)
    return match.group(0) if match else None


async def search_youtube(query: str, num_results: int = 5):
    """YouTube da qidirish (ytsearch)"""
    def _search():
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'noplaylist': True,
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch{num_results}:{query}", download=False)
                entries = info.get('entries', []) if info else []
                return [
                    {
                        'id': entry.get('id'),
                        'title': entry.get('title', 'Nomsiz'),
                        'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}"
                    }
                    for entry in entries if entry and entry.get('id')
                ][:num_results]
            except Exception:
                return []
    return await asyncio.to_thread(_search)


async def download_media(url: str, is_video: bool = True, max_height: int = None):
    """
    yt-dlp orqali yuklab olish.
    Har safar yangi vaqtinchalik papka yaratiladi va oxirida tozalanadi.
    """
    def _download():
        temp_dir = tempfile.mkdtemp()
        if is_video:
            # Video: 1080p yoki IG uchun eng yaxshisi
            if max_height:
                fmt = f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]"
            else:
                fmt = "bestvideo+bestaudio/best"
            postprocessors = []
            out_ext = "%(ext)s"
        else:
            # Audio: MP3
            fmt = "bestaudio/best"
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            out_ext = "mp3"

        ydl_opts = {
            'format': fmt,
            'outtmpl': f'{temp_dir}/%(id)s.{out_ext}',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'postprocessors': postprocessors,
            # Agar Render da ffmpeg yo'lini belgilash kerak bo'lsa:
            # 'ffmpeg_location': '/usr/bin/ffmpeg',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Nomsiz')
            return filename, title, temp_dir
        return None, None, None

    return await asyncio.to_thread(_download)


# ==================== HANDLERLAR ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Salom, Fazo!\n\n"
        "✅ Instagram video linki yuboring → video + \"Audio yuklash\" tugmasi\n"
        "✅ YouTube linki yuboring → 1080p video yoki Audio tanlash\n"
        "✅ Audio yuboring → Shazam orqali qo'shiqni eshitib topaman va ro'yxat chiqaraman\n"
        "✅ Qo'shiq nomi yoki artist yozing → izlab topaman va yuklab beraman\n\n"
        "Boshlang! 🎵📹\n\n"
        "Render free (512 MB) uchun har yuklashdan keyin cache avtomatik tozalanadi."
    )


@dp.message(F.text)
async def handle_text(message: types.Message):
    text = message.text.strip()
    url = extract_url(text)

    if url:
        url_lower = url.lower()
        if 'instagram.com' in url_lower or 'instagr.am' in url_lower:
            await handle_instagram(url, message)
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            await handle_youtube(url, message)
        else:
            await message.answer("❌ Faqat Instagram va YouTube havolalarini qo'llab-quvvatlayman.")
    else:
        # Qo'shiq nomi yoki artist bo'yicha qidiruv
        await handle_song_search(text, message)


async def handle_instagram(url: str, message: types.Message):
    user_id = message.from_user.id
    pending[user_id] = {"url": url, "platform": "ig"}

    await message.answer("📥 Instagram videoni yuklab olmoqda... (bu bir necha soniya vaqt oladi)")

    try:
        filename, title, tmpdir = await download_media(url, is_video=True, max_height=None)
        if filename and os.path.exists(filename):
            markup = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🎵 Audio yuklab olish", callback_data="iga")
            ]])
            await bot.send_video(
                chat_id=message.chat.id,
                video=FSInputFile(filename),
                caption=f"✅ {title}\nInstagram videosi yuklandi!",
                reply_markup=markup
            )
            # CACHE TOZALASH
            os.unlink(filename)
            shutil.rmtree(tmpdir, ignore_errors=True)
        else:
            await message.answer("❌ Video yuklab bo'lmadi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:100]}")
    finally:
        if user_id in pending:
            del pending[user_id]


async def handle_youtube(url: str, message: types.Message):
    user_id = message.from_user.id
    pending[user_id] = {"url": url, "platform": "yt"}

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📹 1080p Video", callback_data="ytv")],
        [InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data="yta")]
    ])
    await message.answer("📥 YouTube videosi topildi!\nFormatni tanlang:", reply_markup=markup)


async def handle_song_search(query: str, message: types.Message):
    await message.answer(f"🔍 '{query}' bo'yicha qidirilmoqda...")

    results = await search_youtube(query)
    if not results:
        await message.answer("😔 Hech qanday natija topilmadi. Boshqa so'z bilan urinib ko'ring.")
        return

    keyboard = []
    for res in results:
        title_short = res['title'][:40] + "..." if len(res['title']) > 40 else res['title']
        keyboard.append([
            InlineKeyboardButton(text=f"🎵 {title_short}", callback_data=f"sa:{res['id']}"),
            InlineKeyboardButton(text="📹", callback_data=f"sv:{res['id']}"),
        ])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("🎶 Topilgan qo'shiqlar (tanlang):", reply_markup=markup)


@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message):
    await message.answer("🔊 Audio eshitilmoqda... Shazam orqali qo'shiq topilmoqda.")

    file_obj = message.voice or message.audio
    file_id = file_obj.file_id
    file_info = await bot.get_file(file_id)

    # Vaqtinchalik fayl
    suffix = '.ogg' if message.voice else ('.mp3' if getattr(file_obj, 'mime_type', '') == 'audio/mpeg' else '.m4a')
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_audio_path = tmp.name

    await bot.download_file(file_info.file_path, temp_audio_path)

    try:
        shazam = Shazam()
        out = await shazam.recognize_song(temp_audio_path)

        if out and out.get('track'):
            track = out['track']
            title = track.get('title', 'Nomsiz')
            artist = track.get('subtitle', '') or track.get('artist', '')
            query = f"{title} {artist}".strip()
            await message.answer(f"✅ Topildi: **{query}**\nEndi yuklab olish ro'yxati:")
            await handle_song_search(query, message)
        else:
            await message.answer("❌ Qo'shiq topilmadi.\nQo'shiq nomi yoki artistni yozib ko'ring.")
    except Exception:
        await message.answer("❌ Audio tanishda xatolik. Qayta urinib ko'ring.")
    finally:
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)


# ==================== CALLBACK HANDLER (tugmalar) ====================

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    chat_id = callback.message.chat.id

    try:
        # ==================== INSTAGRAM AUDIO ====================
        if data == "iga":
            if user_id not in pending or pending[user_id].get("platform") != "ig":
                await callback.answer("Vaqt o'tib ketdi yoki xato.")
                return
            url = pending[user_id]["url"]
            await callback.message.edit_text("🎵 Audio yuklab olinmoqda...")

            filename, title, tmpdir = await download_media(url, is_video=False)
            if filename and os.path.exists(filename):
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=FSInputFile(filename),
                    caption=f"✅ {title} — Audio"
                )
                os.unlink(filename)
                shutil.rmtree(tmpdir, ignore_errors=True)
                await callback.answer("✅ Audio yuklandi!")
            else:
                await callback.answer("❌ Yuklab bo'lmadi.")
            if user_id in pending:
                del pending[user_id]

        # ==================== YOUTUBE 1080p VIDEO ====================
        elif data == "ytv":
            if user_id not in pending or pending[user_id].get("platform") != "yt":
                await callback.answer("Vaqt o'tib ketdi.")
                return
            url = pending[user_id]["url"]
            await callback.message.edit_text("📹 1080p video yuklab olinmoqda...")

            filename, title, tmpdir = await download_media(url, is_video=True, max_height=1080)
            if filename and os.path.exists(filename):
                await bot.send_video(
                    chat_id=chat_id,
                    video=FSInputFile(filename),
                    caption=f"✅ {title} (1080p)"
                )
                os.unlink(filename)
                shutil.rmtree(tmpdir, ignore_errors=True)
                await callback.answer("✅ Video yuklandi!")
            else:
                await callback.answer("❌ Yuklab bo'lmadi.")
            if user_id in pending:
                del pending[user_id]

        # ==================== YOUTUBE AUDIO ====================
        elif data == "yta":
            if user_id not in pending or pending[user_id].get("platform") != "yt":
                await callback.answer("Vaqt o'tib ketdi.")
                return
            url = pending[user_id]["url"]
            await callback.message.edit_text("🎵 Audio yuklab olinmoqda...")

            filename, title, tmpdir = await download_media(url, is_video=False)
            if filename and os.path.exists(filename):
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=FSInputFile(filename),
                    caption=f"✅ {title} — Audio"
                )
                os.unlink(filename)
                shutil.rmtree(tmpdir, ignore_errors=True)
                await callback.answer("✅ Audio yuklandi!")
            else:
                await callback.answer("❌ Yuklab bo'lmadi.")
            if user_id in pending:
                del pending[user_id]

        # ==================== QIDIRUVDAN AUDIO ====================
        elif data.startswith("sa:"):
            vid_id = data[3:]
            url = f"https://www.youtube.com/watch?v={vid_id}"
            await callback.message.edit_text("🎵 Audio yuklab olinmoqda...")

            filename, title, tmpdir = await download_media(url, is_video=False)
            if filename and os.path.exists(filename):
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=FSInputFile(filename),
                    caption=f"✅ {title}"
                )
                os.unlink(filename)
                shutil.rmtree(tmpdir, ignore_errors=True)
                await callback.answer("✅ Audio yuklandi!")
            else:
                await callback.answer("❌ Yuklab bo'lmadi.")

        # ==================== QIDIRUVDAN VIDEO (1080p) ====================
        elif data.startswith("sv:"):
            vid_id = data[3:]
            url = f"https://www.youtube.com/watch?v={vid_id}"
            await callback.message.edit_text("📹 1080p video yuklab olinmoqda...")

            filename, title, tmpdir = await download_media(url, is_video=True, max_height=1080)
            if filename and os.path.exists(filename):
                await bot.send_video(
                    chat_id=chat_id,
                    video=FSInputFile(filename),
                    caption=f"✅ {title} (1080p)"
                )
                os.unlink(filename)
                shutil.rmtree(tmpdir, ignore_errors=True)
                await callback.answer("✅ Video yuklandi!")
            else:
                await callback.answer("❌ Yuklab bo'lmadi.")

    except Exception as e:
        await callback.answer(f"Xatolik: {str(e)[:50]}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
