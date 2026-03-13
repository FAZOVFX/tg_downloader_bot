import asyncio, os, yt_dlp, logging, re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from shazamio import Shazam

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

if not os.path.exists("downloads"): os.makedirs("downloads")

async def download_audio(url, out_tmpl):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'cookiefile': 'cookies.txt',
        'nocheckcertificate': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return out_tmpl + ".mp3"

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("👋 Salom! Men universal musiqa botiman.\n\n"
                         "1. YouTube link yuboring (MP3 beraman).\n"
                         "2. Qo'shiq nomi yoki artist yozing (Ro'yxat beraman).\n"
                         "3. Audio, Video yoki Voice yuboring (Qo'shiqni topib beraman)!")

# --- 1. SHAZAM FUNKSIYASI (Audio/Video/Voice orqali topish) ---
@dp.message(F.audio | F.voice | F.video)
async def shazam_handler(message: types.Message):
    msg = await message.reply("🔍 Musiqa aniqlanmoqda, iltimos kuting...")
    
    # Faylni yuklab olish
    file_id = message.audio.file_id if message.audio else (message.voice.file_id if message.voice else message.video.file_id)
    file = await bot.get_file(file_id)
    file_name = f"downloads/shazam_{file_id}.mp3"
    await bot.download_file(file.file_path, file_name)
    
    try:
        # Shazam orqali aniqlash
        out = await shazam.recognize_song(file_name)
        if not out.get('track'):
            await msg.edit_text("😔 Kechirasiz, bu musiqani taniy olmadim.")
            return

        track = out['track']
        title = track.get('title')
        subtitle = track.get('subtitle') # Artist nomi
        search_query = f"{subtitle} {title}"
        
        await msg.edit_text(f"✅ Topildi: <b>{search_query}</b>\n🔍 YouTube-dan qidirilmoqda...", parse_mode="HTML")
        
        # YouTube-dan qidirib yuklab berish
        file_path = f"downloads/found_{file_id}"
        final_file = await download_audio(f"ytsearch1:{search_query}", file_path)
        
        await message.answer_audio(audio=FSInputFile(final_file), caption=f"🎵 {search_query}\n@ttsuzbek_robot")
        await msg.delete()
        
    except Exception as e:
        logging.error(f"Shazam Error: {e}")
        await msg.edit_text("❌ Aniqlashda xatolik yuz berdi.")
    finally:
        if os.path.exists(file_name): os.remove(file_name)
        if os.path.exists(file_path + ".mp3"): os.remove(file_path + ".mp3")

# --- 2. YOUTUBE LINK HANDLER ---
@dp.message(F.text.contains("http"))
async def link_handler(message: types.Message):
    url = message.text
    msg = await message.reply("⏳ YouTube-dan yuklanmoqda...")
    file_path = f"downloads/auto_{message.from_user.id}"
    try:
        final_file = await download_audio(url, file_path)
        await message.answer_audio(audio=FSInputFile(final_file), caption="🎶 @ttsuzbek_robot")
        await msg.delete()
    except:
        await msg.edit_text("❌ Xatolik!")
    finally:
        if os.path.exists(file_path + ".mp3"): os.remove(file_path + ".mp3")

# --- 3. QIDIRUV (RO'YXAT) HANDLER ---
@dp.message(F.text)
async def search_handler(message: types.Message):
    query = message.text
    msg = await message.reply(f"🔎 <b>{query}</b> qidirilmoqda...", parse_mode="HTML")
    try:
        ydl_opts = {'quiet': True, 'cookiefile': 'cookies.txt'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch5:{query}", download=False)
        
        if not info['entries']:
            await msg.edit_text("😔 Topilmadi.")
            return

        buttons = []
        text = f"🎶 <b>'{query}' bo'yicha natijalar:</b>\n\n"
        for i, entry in enumerate(info['entries'], 1):
            title = entry.get('title')[:45]
            v_id = entry.get('id')
            text += f"{i}. {title}\n"
            buttons.append([InlineKeyboardButton(text=f"{i}-ni yuklash 📥", callback_data=f"yt_{v_id}")])

        await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except:
        await msg.edit_text("❌ Xato!")

@dp.callback_query(F.data.startswith("yt_"))
async def download_callback(callback: types.CallbackQuery):
    v_id = callback.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={v_id}"
    await callback.message.edit_text("⏳ Yuklanmoqda...")
    file_path = f"downloads/sel_{v_id}"
    try:
        final_file = await download_audio(url, file_path)
        await callback.message.answer_audio(audio=FSInputFile(final_file), caption="🎶 @ttsuzbek_robot")
        await callback.message.delete()
    except:
        await callback.message.answer("❌ Xato!")
    finally:
        if os.path.exists(file_path + ".mp3"): os.remove(file_path + ".mp3")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
