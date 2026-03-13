import asyncio, os, yt_dlp, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

if not os.path.exists("downloads"): os.makedirs("downloads")

async def download_video(url, format_id, out_tmpl):
    # Instagram va boshqalar uchun kuki shart emas, lekin YouTube uchun kerak
    use_cookies = "cookies.txt" if "youtube.com" in url or "youtu.be" in url else None
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'cookiefile': use_cookies,
        'nocheckcertificate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return out_tmpl

@dp.message(F.text.contains("http"))
async def link_handler(message: types.Message):
    url = message.text
    msg = await message.reply("⚡️ Video tayyorlanmoqda... 📥")
    
    try:
        # Instagram uchun kuki ishlatmaymiz
        ydl_opts = {'quiet': True}
        if "youtube" in url or "youtu.be" in url:
            ydl_opts['cookiefile'] = 'cookies.txt'
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            v_id = info.get('id', 'video')
            title = info.get('title', 'Video')[:50]
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 Video", callback_data=f"dl_best_{v_id}"),
             InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl_mp3_{v_id}")]
        ])
        await msg.edit_text(f"✅ Topildi: **{title}**\n\nPastdan birini tanlang 👇", reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        # Haqiqiy xatoni logda ko'rish uchun
        logging.error(f"Xato: {e}")
        await msg.edit_text(f"❌ Yuklashda muammo bo'ldi.\nSababi: {str(e)[:50]}...")

@dp.callback_query(F.data.startswith("dl_"))
async def callbacks(callback: types.CallbackQuery):
    _, quality, v_id = callback.data.split("_")
    # Linkni qayta tiklash
    url = callback.message.reply_to_message.text
    
    await callback.message.edit_text("⏳ Yuklanmoqda... (Katta videolar biroz vaqt oladi) 🚀")
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    file_path = f"downloads/{v_id}.{ext}"
    
    try:
        f_id = 'bestaudio/best' if quality == 'mp3' else 'bestvideo+bestaudio/best'
        await download_video(url, f_id, file_path)
        
        input_file = FSInputFile(file_path)
        if quality == 'mp3':
            await callback.message.answer_audio(audio=input_file, caption="🎶 @ttsuzbek_robot")
        else:
            await callback.message.answer_video(video=input_file, caption="📹 @ttsuzbek_robot")
        
        await callback.message.delete()
        if os.path.exists(file_path): os.remove(file_path)
    except Exception as e:
        await callback.message.answer(f"❌ Xato: {str(e)[:50]}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
