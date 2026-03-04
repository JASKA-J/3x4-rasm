import io
import asyncio
import cv2
import numpy as np
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from rembg import remove
from PIL import Image

# 1. BOT TOKENINGIZNI KIRITING
TOKEN = "8798419136:AAFH_K2EjKVs9KGvG7sinITgUspu64bGGXs"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# 30x40mm o'lchami (300 DPI da)
W_FINAL, H_FINAL = 354, 472

# Yuzni aniqlash uchun kaskad yuklash (OpenCV bilan birga keladi)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
if face_cascade.empty():
    face_cascade = cv2.CascadeClassifier(cv2.samples.findFile('haarcascades/haarcascade_frontalface_default.xml'))

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Salom! Menga tekis qaragan tushgan rasm yuboring, men uni 30x40 hujjat rasmiga avtomatik kostyumda tayyorlayman.")

@dp.message_handler(content_types=['photo'])
async def process_image(message: types.Message):
    await message.answer("Rasmingiz tahlil qilinmoqda va kostyum moslashtirilmoqda, iltimos kuting...")

    # Rasmni xotiraga yuklash
    photo_io = io.BytesIO()
    await message.photo[-1].download(destination_file=photo_io)
    photo_io.seek(0)

    # PIL Image ob'ektini yaratish
    input_img = Image.open(photo_io).convert("RGB")
    
    # --- 1-BOSQICH: YUZNI ANIQLASH (OpenCV) ---
    # PIL imageni OpenCV formatiga (BGR) o'tkazish
    opencv_img = cv2.cvtColor(np.array(input_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(opencv_img, cv2.COLOR_BGR2GRAY)
    
    # Yuzlarni topish
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        await message.answer("Xatolik: Rasmda yuz aniqlanmadi. Iltimos, aniqroq rasm yuboring.")
        return

    # Eng katta yuzni tanlash (agar bir nechta bo'lsa)
    (x, y, w, h) = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
    
    # Yuzning markazi
    face_center_x = x + w // 2
    face_center_y = y + h // 2

    # --- 2-BOSQICH: FONNI O'CHIRISH (Rembg) ---
    no_bg_img = remove(input_img)

    # --- 3-BOSQICH: KOSTYUMNI YUKLASH VA MOSLASH ---
    try:
        suit = Image.open("suit.png").convert("RGBA")
    except:
        await message.answer("Xatolik: suit.png fayli topilmadi!")
        return

    # Kostyum o'lchamini inson yuzining kengligiga moslab o'zgartirish
    # Bu koeffitsientni (masalan, 2.5) suit.png'ingizga qarab sozlashingiz mumkin
    suit_width_factor = 2.8 
    new_suit_width = int(w * suit_width_factor)
    suit_aspect_ratio = suit.height / suit.width
    new_suit_height = int(new_suit_width * suit_aspect_ratio)
    
    current_suit = suit.resize((new_suit_width, new_suit_height))

    # --- 4-BOSQICH: RENDER VA KOMPOZITSIYA ---
    # Oq fon yaratish (vaqtincha kattaroq, keyin qirqamiz)
    canvas = Image.new("RGBA", (input_img.width * 2, input_img.height * 2), (255, 255, 255, 255))
    
    # Insonni (fonsiz) canvas markaziga qo'yish
    canvas.paste(no_bg_img, (input_img.width // 2, input_img.height // 2), no_bg_img)

    # Kostyumni yuzning ostiga joylashtirish
    # Kostyumning bo'yin qismi yuz markazidan bir oz pastroqda bo'lishi kerak
    suit_y_offset = int(h * 0.55) # Yuz balandligining 55% i pastga
    
    suit_x = (input_img.width // 2) + (face_center_x - input_img.width // 2) - (new_suit_width // 2)
    suit_y = (input_img.height // 2) + (face_center_y - input_img.height // 2) + suit_y_offset

    canvas.paste(current_suit, (int(suit_x), int(suit_y)), current_suit)

    # --- 5-BOSQICH: QIRQISH (CROP) VA FINAL FORMAT ---
    # Final rasm yuz markaziga nisbatan 30x40 proporsiyada qirqiladi
    
    crop_width = int(new_suit_width * 1.2) # Kostyumdan biroz kengroq
    crop_height = int(crop_width * (H_FINAL / W_FINAL))
    
    crop_x = (input_img.width // 2) + face_center_x - (crop_width // 2)
    crop_y = (input_img.height // 2) + face_center_y - int(crop_height * 0.35) # Yuz teparoqda bo'lishi uchun

    # Qirqish
    final_img = canvas.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
    
    # Final o'lchamga keltirish (354x472)
    final_img = final_img.resize((W_FINAL, H_FINAL))

    # Natijani saqlash
    output_io = io.BytesIO()
    final_img.convert("RGB").save(output_io, "JPEG", quality=100)
    output_io.seek(0)

    # Yuborish
    await message.answer_document(types.InputFile(output_io, "30x40_face_detected.jpg"))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
