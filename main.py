import asyncio
import os
import yt_dlp
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# TOKENNI OLISH
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("⚠️ BOT_TOKEN topilmadi! Render sozlamalarini tekshiring.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Yuklab olish papkasi
if not os.path.exists("downloads"):
    os.makedirs("downloads")

async def download_video(url, format_id, out_tmpl):
    ydl_opts = {
        'format': format_id,
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'cookiefile': 'cookies.txt',  # GitHub-ga yuklagan faylingiz nomi
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return out_tmpl

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("👋 Salom! Men YouTube va Instagramdan yuklovchi botman.\n\n"
                         "✨ Menga video linkini yuboring yoki artist/qo'shiq nomini yozing! 🎶")

@dp.message(F.text.contains("http"))
async def link_handler(message: types.Message):
    url = message.text
    msg = await message.reply("🔍 Link tahlil qilinmoqda, ozgina kuting... ⏳")
    
    try:
        ydl_opts = {'quiet': True, 'cookiefile': 'cookies.txt'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            v_id = info.get('id', 'video')
            title = info.get('title', 'Video')[:50]
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 Video (720p)", callback_data=f"dl_720_{v_id}"),
             InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"dl_mp3_{v_id}")]
        ])
        await msg.edit_text(f"🎬 **{title}**\n\nQaysi formatda yuklamoqchisiz? 👇", 
                           reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Xatolik yuz berdi: YouTube bloklagan bo'lishi mumkin. Kuki faylni yangilang.")

@dp.message(F.text)
async def search_handler(message: types.Message):
    # Agar xabar link bo'lmasa, qidiruv deb hisoblaymiz
    query = message.text
    msg = await message.reply(f"🔎 **'{query}'** bo'yicha qidirilmoqda... ✨")
    
    try:
        search_url = f"ytsearch1:{query}"
        ydl_opts = {'quiet': True, 'cookiefile': 'cookies.txt'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, search_url, download=False)
            if not info['entries']:
                await msg.edit_text("😔 Hech narsa topilmadi.")
                return
            
            video = info['entries'][0]
            v_id = video['id']
            title = video['title'][:50]
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 Videoni yuklash", callback_data=f"dl_720_{v_id}"),
             InlineKeyboardButton(text="🎵 MP3 ni yuklash", callback_data=f"dl_mp3_{v_id}")]
        ])
        await msg.edit_text(f"🎵 **Topildi:** {title}\n\nPastdagilardan birini tanlang: 👇", 
                           reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Qidiruvda xatolik: {str(e)[:50]}")

@dp.callback_query(F.data.startswith("dl_"))
async def callbacks(callback: types.CallbackQuery):
    _, quality, v_id = callback.data.split("_")
    # Qidiruvdan kelgan bo'lsa ID orqali link yasaymiz
    url = f"https://www.youtube.com/watch?v={v_id}"
    
    await callback.message.edit_text(f"🚀 Yuklash boshlandi... kuting... ⚡")
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    file_path = f"downloads/{v_id}.{ext}"
    
    try:
        if quality == 'mp3':
            f_id = 'bestaudio/best'
            await download_video(url, f_id, file_path)
            await callback.message.answer_audio(audio=FSInputFile(file_path), caption="🎶 Siz so'ragan audio! @sizning_botingiz")
        else:
            f_id = 'bestvideo[height<=720]+bestaudio/best'
            await download_video(url, f_id, file_path)
            await callback.message.answer_video(video=FSInputFile(file_path), caption="📹 Mana video! @sizning_botingiz")
        
        if os.path.exists(file_path):
            os.remove(file_path)
        await callback.message.delete()
    except Exception as e:
        await callback.message.answer(f"❌ Yuklashda xato: Server band bo'lishi mumkin.")

async def main():
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())