import asyncio
import os
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# TOKEnNI SECRET-DAN OLISH (Hugging Face Settings -> Secrets)
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("XATOLIK: BOT_TOKEN topilmadi! Hugging Face Settings -> Secrets bo'limiga tokenni qo'shing.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Fayllar uchun vaqtinchalik papka
if not os.path.exists("downloads"):
    os.makedirs("downloads")

async def download_video(url, format_id, out_tmpl):
    ydl_opts = {
        'format': format_id,
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return out_tmpl

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Salom! Menga YouTube yoki Instagram linkini yuboring.")

@dp.message(F.text.contains("http"))
async def link_handler(message: types.Message):
    url = message.text
    msg = await message.reply("🔍 Link tekshirilmoqda...")
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            v_id = info.get('id', 'video')
            title = info.get('title', 'Video')[:50]
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 Video (720p)", callback_data=f"dl_720_{v_id}"),
             InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"dl_mp3_{v_id}")]
        ])
        await msg.edit_text(f"🎬 {title}\n\nFormatni tanlang:", reply_markup=keyboard)
    except Exception as e:
        await msg.edit_text(f"Xatolik yuz berdi: {str(e)[:100]}")

@dp.callback_query(F.data.startswith("dl_"))
async def callbacks(callback: types.CallbackQuery):
    _, quality, v_id = callback.data.split("_")
    url = callback.message.reply_to_message.text # Asl linkni olish
    
    await callback.message.edit_text(f"⏳ Yuklanmoqda, kuting...")
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    file_path = f"downloads/{v_id}.{ext}"
    
    try:
        f_id = 'bestaudio/best' if quality == 'mp3' else 'bestvideo[height<=720]+bestaudio/best'
        await download_video(url, f_id, file_path)
        
        if quality == 'mp3':
            await callback.message.answer_audio(audio=FSInputFile(file_path))
        else:
            await callback.message.answer_video(video=FSInputFile(file_path))
        
        if os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.delete()
    except Exception as e:
        await callback.message.answer(f"Xato: {str(e)[:100]}")

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())