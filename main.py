import asyncio
import os
import yt_dlp
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# Loglarni sozlash (Xatolarni Render loglarida ko'rish uchun)
logging.basicConfig(level=logging.INFO)

# Tokenni Render Environment Variables'dan oladi
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("⚠️ BOT_TOKEN topilmadi! Render sozlamalarini tekshiring.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Yuklab olish uchun vaqtinchalik papka
if not os.path.exists("downloads"):
    os.makedirs("downloads")

def clean_html(text):
    """Telegram HTML xatoligini (entities) oldini olish uchun matnni tozalash"""
    if not text:
        return "Video"
    # Telegram tushunmaydigan yoki xato beradigan belgilarni olib tashlaymiz
    clean = re.sub(r'[<>&_*`]', '', text)
    return clean[:50]

async def download_video(url, format_id, out_tmpl):
    """yt-dlp orqali yuklab olish funksiyasi"""
    # Faqat YouTube uchun cookies.txt ishlatamiz
    use_cookies = "cookies.txt" if "youtube.com" in url or "youtu.be" in url else None
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'cookiefile': use_cookies,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])
    return out_tmpl

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("👋 <b>Salom! Men YouTube va Instagram yuklovchisiman.</b>\n\n"
                         "✨ Menga video linkini yuboring yoki qo'shiq nomini yozing!", parse_mode="HTML")

@dp.message(F.text.contains("http"))
async def link_handler(message: types.Message):
    url = message.text
    msg = await message.reply("🔍 <b>Link tahlil qilinmoqda...</b>", parse_mode="HTML")
    
    try:
        ydl_opts = {'quiet': True}
        if "youtube" in url or "youtu.be" in url:
            ydl_opts['cookiefile'] = 'cookies.txt'
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            v_id = info.get('id', 'video')
            title = clean_html(info.get('title', 'Video'))
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 Videoni yuklash", callback_data=f"dl_best_{v_id}"),
             InlineKeyboardButton(text="🎵 MP3 yuklash", callback_data=f"dl_mp3_{v_id}")]
        ])
        await msg.edit_text(f"🎬 <b>{title}</b>\n\nTanlang: 👇", reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Link Error: {e}")
        await msg.edit_text("❌ <b>Xatolik!</b> Link noto'g'ri yoki video yopiq.")

@dp.callback_query(F.data.startswith("dl_"))
async def callbacks(callback: types.CallbackQuery):
    _, quality, v_id = callback.data.split("_")
    
    # Linkni asl xabardan olish
    try:
        url = callback.message.reply_to_message.text
    except:
        await callback.answer("❌ Xato: Asl havola topilmadi.", show_alert=True)
        return
    
    await callback.message.edit_text("⏳ <b>Yuklash boshlandi... Ozgina kuting</b> 🚀", parse_mode="HTML")
    
    ext = 'mp3' if quality == 'mp3' else 'mp4'
    file_path = f"downloads/{v_id}.{ext}"
    
    try:
        # Eng universal formatlar: agar 720p bo'lmasa, borini oladi
        if quality == 'mp3':
            f_id = 'bestaudio/best'
        else:
            f_id = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            
        await download_video(url, f_id, file_path)
        
        file = FSInputFile(file_path)
        if quality == 'mp3':
            await callback.message.answer_audio(audio=file, caption="🎶 @ttsuzbek_robot")
        else:
            await callback.message.answer_video(video=file, caption="📹 @ttsuzbek_robot")
        
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Download Error: {e}")
        await callback.message.answer("❌ <b>Kechirasiz, yuklashda xatolik yuz berdi.</b>")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message(F.text)
async def search_handler(message: types.Message):
    query = message.text
    if len(query) < 3: return
    
    msg = await message.reply(f"🔎 <b>{query}</b> qidirilmoqda...", parse_mode="HTML")
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
            title = clean_html(video['title'])
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 Video", callback_data=f"dl_best_{v_id}"),
             InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl_mp3_{v_id}")]
        ])
        await msg.edit_text(f"🎬 <b>{title}</b>\n\nTopildi! Yuklamoqchimisiz? 👇", 
                           reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Search Error: {e}")
        await msg.edit_text("❌ Qidiruvda xatolik yuz berdi.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
