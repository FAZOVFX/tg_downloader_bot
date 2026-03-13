import asyncio
import os
import re
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# --- SOZLAMALAR ---
TOKEN = os.getenv("BOT_TOKEN") # Bu yerga bot tokenini qo'ying
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Fayllarni vaqtincha saqlash uchun papka
if not os.path.exists("downloads"):
    os.makedirs("downloads")

# --- FUNKSIYALAR ---

def get_video_info(url):
    """Video haqida ma'lumot olish (Sarlavha, ID, davomiyligi)"""
    ydl_opts = {'quiet': True, 'skip_download': True, 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

async def download_task(url, format_id, out_tmpl):
    """Yuklab olish jarayoni"""
    ydl_opts = {
        'format': format_id,
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return out_tmpl

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("👋 Salom! Men YouTube va Instagramdan video yuklovchi botman.\n\n"
                         "🔗 Link yuboring yoki qo'shiq/artist nomini yozing.")

# 1. YOUTUBE LINK ISHLOVCHISI
@dp.message(F.text.regexp(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+'))
async def yt_link_handler(message: types.Message):
    url = message.text
    msg = await message.reply("🔍 YouTube videosi tahlil qilinmoqda...")
    
    try:
        info = await asyncio.to_thread(get_video_info, url)
        v_id = info['id']
        title = info.get('title', 'Video')[:50]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 480p", callback_data=f"dl_480_{v_id}"),
             InlineKeyboardButton(text="📹 720p", callback_data=f"dl_720_{v_id}")],
            [InlineKeyboardButton(text="📹 1080p", callback_data=f"dl_1080_{v_id}"),
             InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl_mp3_{v_id}")]
        ])
        
        await msg.edit_text(f"🎬 **{title}**\n\nFormatni tanlang:", reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ma'lumot olib bo'lmadi. Linkni tekshiring.")

# 2. INSTAGRAM LINK ISHLOVCHISI (AVTO YUKLASH)
@dp.message(F.text.regexp(r'(https?://)?(www\.)?instagram\.com/(reels?|p|tv)/.+'))
async def insta_link_handler(message: types.Message):
    url = message.text
    status = await message.answer("📥 Instagramdan yuklanmoqda (Video + Audio)...")
    
    file_prefix = f"downloads/insta_{message.from_user.id}"
    video_path = f"{file_prefix}.mp4"
    audio_path = f"{file_prefix}.mp3"

    try:
        # Videoni yuklash
        await download_task(url, 'best', video_path)
        # Audioni yuklash
        ydl_audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_path,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        }
        with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])

        await message.answer_video(video=FSInputFile(video_path), caption="Instagram Video ✅")
        await message.answer_audio(audio=FSInputFile(audio_path), caption="Video ovozi (MP3) ✅")
        
        os.remove(video_path)
        os.remove(audio_path)
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Instagramdan yuklashda xato: {e}")

# 3. YOUTUBE FORMATLARINI YUKLASH (CALLBACK)
@dp.callback_query(F.data.startswith("dl_"))
async def process_callback_dl(callback: types.CallbackQuery):
    _, quality, v_id = callback.data.split("_")
    url = f"https://www.youtube.com/watch?v={v_id}"
    await callback.message.edit_text(f"⏳ {quality} yuklanmoqda... Kuting.")
    
    file_path = f"downloads/{v_id}_{quality}.{'mp3' if quality == 'mp3' else 'mp4'}"
    
    try:
        if quality == 'mp3':
            f_id = 'bestaudio/best'
        else:
            f_id = f"bestvideo[height<={quality}]+bestaudio/best"

        final_file = await download_task(url, f_id, file_path)
        
        if quality == 'mp3':
            await callback.message.answer_audio(audio=FSInputFile(final_file))
        else:
            await callback.message.answer_video(video=FSInputFile(final_file))
            
        os.remove(final_file)
        await callback.message.delete()
    except Exception as e:
        await callback.message.answer(f"❌ Yuklashda xatolik: {e}")

# 4. QIDIRUV (MATN BERILSA)
@dp.message(F.text)
async def search_handler(message: types.Message):
    if len(message.text) < 3: return
    
    query = message.text
    msg = await message.answer(f"🔍 '{query}' bo'yicha qidirilmoqda...")
    
    try:
        ydl_opts = {'quiet': True, 'noplaylist': True, 'default_search': 'ytsearch5'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = await asyncio.to_thread(ydl.extract_info, query, download=False)
            
        text = "🔎 Topilgan natijalar:\n\n"
        buttons = []
        for entry in results['entries']:
            text += f"🔹 {entry['title'][:50]}...\n"
            buttons.append([InlineKeyboardButton(text=entry['title'][:30], callback_data=f"dl_720_{entry['id']}")])
        
        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except:
        await msg.edit_text("❌ Hech narsa topilmadi.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())