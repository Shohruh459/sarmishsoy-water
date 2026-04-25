import os
from datetime import datetime
from aiogram import Dispatcher, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
import keyboards as kb
import database as db

WORK_START = int(os.getenv("WORK_START", 8))
WORK_END = int(os.getenv("WORK_END", 20))
BAKLASHKA_GROUP_ID = int(os.getenv("BAKLASHKA_GROUP_ID", 0))
LITR_GROUP_ID = int(os.getenv("LITR_GROUP_ID", 0))
MIJOZ_BOT_TOKEN = os.getenv("MIJOZ_BOT_TOKEN")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HOLATLAR (FSM)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BuyurtmaHolat(StatesGroup):
    mahsulot_turi = State()
    miqdor = State()
    telefon = State()
    manzil = State()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YORDAMCHI FUNKSIYALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def ish_vaqtimi() -> bool:
    hozir = datetime.now().hour
    return WORK_START <= hozir < WORK_END

async def bekor_va_bosh_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Bekor qilindi. Asosiy menyu:",
        reply_markup=kb.mijoz_asosiy()
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HANDLERLAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Assalomu aleykum, {message.from_user.first_name}! 👋\n"
        f"Sarmishsoy Water botiga xush kelibsiz!\n"
        f"Ish vaqti: {WORK_START:02d}:00 – {WORK_END:02d}:00",
        reply_markup=kb.mijoz_asosiy()
    )

async def buyurtma_boshlash(message: Message, state: FSMContext):
    if not ish_vaqtimi():
        await message.answer(
            f"⏰ Kechirasiz, ish vaqti tugagan!\n"
            f"Ish vaqti: {WORK_START:02d}:00 – {WORK_END:02d}:00\n\n"
            f"📞 Qo'ng'iroq qilishingiz mumkin:\n"
            f"💧 Baklashka: +998 93 439 65 03\n"
            f"🚰 Litr suv: +998 93 310 11 70"
        )
        return
    await state.set_state(BuyurtmaHolat.mahsulot_turi)
    await message.answer(
        "Mahsulot turini tanlang:",
        reply_markup=kb.mahsulot_turi()
    )

async def mahsulot_tanlash(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.mijoz_asosiy())
        return

    if message.text == "💧 Baklashka (18.9L)":
        tur = "baklashka"
    elif message.text == "🚰 Litr suv":
        tur = "litr"
    else:
        await message.answer("Iltimos, tugmalardan foydalaning.")
        return

    await state.update_data(mahsulot_turi=tur)
    await state.set_state(BuyurtmaHolat.miqdor)

    if tur == "baklashka":
        await message.answer(
            "Nechta baklashka kerak? (raqam kiriting)\nMasalan: 2",
            reply_markup=kb.bekor_qilish()
        )
    else:
        await message.answer(
            "Necha litr kerak? (raqam kiriting)\nMasalan: 10",
            reply_markup=kb.bekor_qilish()
        )

async def miqdor_kiritish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.mijoz_asosiy())
        return

    try:
        miqdor = float(message.text.replace(",", "."))
        if miqdor <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Iltimos, to'g'ri raqam kiriting. Masalan: 2")
        return

    await state.update_data(miqdor=miqdor)
    await state.set_state(BuyurtmaHolat.telefon)
    await message.answer(
        "📞 Telefon raqamni kiriting:\n"
        "Masalan: +998901234567\n\n"
        "⚠️ Buyurtmani qabul qiluvchi raqamni kiriting!",
        reply_markup=kb.bekor_qilish()
    )

async def telefon_kiritish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.mijoz_asosiy())
        return

    telefon = message.text.strip()
    if not telefon.startswith("+") or len(telefon) < 10:
        await message.answer(
            "❗ Telefon raqam noto'g'ri.\n"
            "Masalan: +998901234567"
        )
        return

    await state.update_data(telefon=telefon)
    await state.set_state(BuyurtmaHolat.manzil)
    await message.answer(
        "📍 Manzilni kiriting:\nMasalan: Mustaqillik ko'chasi 15-uy",
        reply_markup=kb.bekor_qilish()
    )

async def manzil_kiritish(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.mijoz_asosiy())
        return

    await state.update_data(manzil=message.text.strip())
    data = await state.get_data()
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        order_id = await conn.fetchval("""
            INSERT INTO orders 
                (mijoz_telegram_id, mijoz_ism, telefon, 
                 mahsulot_tur, miqdor, manzil, tolov_turi, status)
            VALUES ($1, $2, $3, $4, $5, $6, 'noma_lum', 'yangi')
            RETURNING id
        """,
            message.from_user.id,
            message.from_user.full_name,
            data["telefon"],
            data["mahsulot_turi"],
            data["miqdor"],
            message.text.strip()
        )

    tur_nomi = "Baklashka (18.9L)" if data["mahsulot_turi"] == "baklashka" else "Litr suv"
    miqdor_son = int(data["miqdor"]) if float(data["miqdor"]).is_integer() else data["miqdor"]

    await message.answer(
        f"✅ Buyurtma qabul qilindi!\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"💧 Mahsulot: {tur_nomi}\n"
        f"📦 Miqdor: {miqdor_son}\n"
        f"📞 Telefon: {data['telefon']}\n"
        f"📍 Manzil: {data['manzil']}\n\n"
        f"⏳ Yetkazuvchi tez orada yo'lga chiqadi!",
        reply_markup=kb.buyurtma_bekor_inline(order_id)
    )

    # Guruhga xabar yuborish
    guruh_id = BAKLASHKA_GROUP_ID if data["mahsulot_turi"] == "baklashka" else LITR_GROUP_ID
    if guruh_id:
        bot = Bot(token=MIJOZ_BOT_TOKEN)
        try:
            await bot.send_message(
                guruh_id,
                f"🆕 YANGI BUYURTMA #{order_id}\n\n"
                f"💧 {tur_nomi} — {miqdor_son}\n"
                f"📞 {data['telefon']}\n"
                f"📍 {data['manzil']}\n"
                f"🕐 {datetime.now().strftime('%H:%M')}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Qabul qildim",
                            callback_data=f"guruh_qabul_{order_id}"
                        )]
                    ]
                )
            )
        finally:
            await bot.session.close()

async def tolov_tanlash(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.mijoz_asosiy())
        return

    tolov_map = {
        "💵 Naqt": "naqt",
        "📱 Click": "click",
        "📝 Qarz": "qarz"
    }

    if message.text not in tolov_map:
        await message.answer("Iltimos, tugmalardan foydalaning.")
        return

    tolov = tolov_map[message.text]
    tolov_nomi = message.text
    data = await state.get_data()
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        order_id = await conn.fetchval("""
            INSERT INTO orders 
                (mijoz_telegram_id, mijoz_ism, telefon, 
                 mahsulot_tur, miqdor, manzil, tolov_turi, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'yangi')
            RETURNING id
        """,
            message.from_user.id,
            message.from_user.full_name,
            data["telefon"],
            data["mahsulot_turi"],
            data["miqdor"],
            data["manzil"],
            tolov
        )

    tur_nomi = "Baklashka (18.9L)" if data["mahsulot_turi"] == "baklashka" else "Litr suv"
    miqdor_son = int(data["miqdor"]) if float(data["miqdor"]).is_integer() else data["miqdor"]

    # Mijozga tasdiqlash xabari
    await message.answer(
        f"✅ Buyurtma qabul qilindi!\n\n"
        f"🆔 Buyurtma: #{order_id}\n"
        f"💧 Mahsulot: {tur_nomi}\n"
        f"📦 Miqdor: {miqdor_son}\n"
        f"📞 Telefon: {data['telefon']}\n"
        f"📍 Manzil: {data['manzil']}\n"
        f"💳 To'lov: {tolov_nomi}\n\n"
        f"⏳ Yetkazuvchi tez orada bog'lanadi!",
        reply_markup=kb.buyurtma_bekor_inline(order_id)
    )

    # Guruhga xabar yuborish
    guruh_id = BAKLASHKA_GROUP_ID if data["mahsulot_turi"] == "baklashka" else LITR_GROUP_ID
    if guruh_id:
        bot = Bot(token=MIJOZ_BOT_TOKEN)
        try:
            await bot.send_message(
                guruh_id,
                f"🆕 YANGI BUYURTMA #{order_id}\n\n"
                f"💧 {tur_nomi} — {miqdor_son}\n"
                f"📞 {data['telefon']}\n"
                f"📍 {data['manzil']}\n"
                f"💳 {tolov_nomi}\n"
                f"🕐 {datetime.now().strftime('%H:%M')}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Qabul qildim",
                            callback_data=f"guruh_qabul_{order_id}"
                        )]
                    ]
                )
            )
        finally:
            await bot.session.close()

async def buyurtmalarim(message: Message):
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        orders = await conn.fetch("""
            SELECT id, mahsulot_tur, miqdor, status, yaratilgan_vaqt
            FROM orders
            WHERE mijoz_telegram_id = $1
            ORDER BY yaratilgan_vaqt DESC
            LIMIT 5
        """, message.from_user.id)

    if not orders:
        await message.answer("📋 Sizda hali buyurtma yo'q.")
        return

    status_map = {
        "yangi": "🆕 Yangi",
        "qabul_qilindi": "✅ Qabul qilindi",
        "yetkazildi": "✅ Yetkazildi",
        "yetkazilmadi": "❌ Yetkazilmadi",
        "bekor": "🚫 Bekor qilindi"
    }

    matn = "📋 So'nggi 5 ta buyurtma:\n\n"
    for order in orders:
        tur = "Baklashka" if order["mahsulot_tur"] == "baklashka" else "Litr"
        sana = order["yaratilgan_vaqt"].strftime("%d.%m.%Y %H:%M")
        status = status_map.get(order["status"], order["status"])
        matn += (
            f"🆔 #{order['id']} | {tur} {order['miqdor']}\n"
            f"📅 {sana}\n"
            f"📌 {status}\n\n"
        )

    await message.answer(matn, reply_markup=kb.mijoz_asosiy())

async def bekor_qilish_callback(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT status, mijoz_telegram_id FROM orders WHERE id = $1
        """, order_id)

        if not order:
            await callback.answer("Buyurtma topilmadi!", show_alert=True)
            return

        if order["mijoz_telegram_id"] != callback.from_user.id:
            await callback.answer("Bu sizning buyurtmangiz emas!", show_alert=True)
            return

        if order["status"] != "yangi":
            await callback.answer(
                "Faqat 'yangi' statusidagi buyurtmani bekor qilish mumkin!",
                show_alert=True
            )
            return

        await conn.execute("""
            UPDATE orders SET status = 'bekor' WHERE id = $1
        """, order_id)

    await callback.message.edit_text(
        callback.message.text + "\n\n🚫 Buyurtma bekor qilindi!"
    )
    await callback.answer("✅ Buyurtma bekor qilindi!")

async def guruh_qabul_callback(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    telegram_id = callback.from_user.id
    ism = callback.from_user.full_name

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT status FROM orders WHERE id = $1
        """, order_id)

        if not order:
            await callback.answer("Buyurtma topilmadi!", show_alert=True)
            return

        if order["status"] != "yangi":
            await callback.answer(
                "Bu buyurtma allaqachon qabul qilingan!",
                show_alert=True
            )
            return

        # Yetkazuvchini tekshirish yoki yaratish
        courier = await conn.fetchrow("""
            SELECT id FROM couriers WHERE telegram_id = $1
        """, telegram_id)

        if not courier:
            courier_id = await conn.fetchval("""
                INSERT INTO couriers (telegram_id, ism, tur, aktiv)
                VALUES ($1, $2, 'baklashka', true)
                RETURNING id
            """, telegram_id, ism)
        else:
            courier_id = courier["id"]

        await conn.execute("""
            UPDATE orders 
            SET yetkazuvchi_id = $1, status = 'qabul_qilindi'
            WHERE id = $2
        """, courier_id, order_id)

    await callback.message.edit_text(
        callback.message.text +
        f"\n\n✅ {ism} qabul qildi!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Yetkazdim",
                        callback_data=f"guruh_yetkazdi_{order_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Yetkazolmadim",
                        callback_data=f"guruh_yetkazolmadi_{order_id}"
                    )
                ]
            ]
        )
    )
    await callback.answer("✅ Buyurtma qabul qilindi!")

async def guruh_yetkazdi_callback(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT * FROM orders WHERE id = $1
        """, order_id)

        if not order:
            await callback.answer("Buyurtma topilmadi!", show_alert=True)
            return

        if order["status"] != "qabul_qilindi":
            await callback.answer("Buyurtma holati noto'g'ri!", show_alert=True)
            return

    await callback.message.edit_text(
        callback.message.text +
        f"\n\n💳 To'lov turini tanlang:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💵 Naqt",
                        callback_data=f"tolov_naqt_{order_id}"
                    ),
                    InlineKeyboardButton(
                        text="📱 Click",
                        callback_data=f"tolov_click_{order_id}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📝 Keyinroq (qarz)",
                        callback_data=f"tolov_qarz_{order_id}"
                    ),
                ],
            ]
        )
    )
    await callback.answer()
async def tolov_turi_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    tolov = parts[1]
    order_id = int(parts[2])

    tolov_map = {
        "naqt": "💵 Naqt",
        "click": "📱 Click",
        "qarz": "📝 Keyinroq (qarz)"
    }

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT * FROM orders WHERE id = $1
        """, order_id)

        await conn.execute("""
            UPDATE orders 
            SET status = 'yetkazildi', tolov_turi = $1
            WHERE id = $2
        """, tolov, order_id)

        if tolov == "qarz":
            baklashka_narx = 10000
            litr_narx = 200
            narx = baklashka_narx if order["mahsulot_tur"] == "baklashka" else litr_narx
            summa = narx * order["miqdor"]
            await conn.execute("""
                INSERT INTO debts 
                    (mijoz_telegram_id, yetkazuvchi_id, order_id, summa, qolgan_summa)
                VALUES ($1, $2, $3, $4, $4)
            """, order["mijoz_telegram_id"], order["yetkazuvchi_id"], order_id, summa)

    await callback.message.edit_text(
        callback.message.text +
        f"\n\n✅ Yetkazildi! To'lov: {tolov_map[tolov]}"
    )
    await callback.answer("✅ Bajarildi!")
async def guruh_yetkazolmadi_callback(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders SET status = 'yetkazilmadi' WHERE id = $1
        """, order_id)

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ YETKAZILMADI!"
    )
    await callback.answer("❌ Qayd etildi!")

async def qarzlarim(message: Message):
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        qarzlar = await conn.fetch("""
            SELECT d.id, d.summa, d.qolgan_summa, d.holat, d.birinchi_qarz_sanasi
            FROM debts d
            WHERE d.mijoz_telegram_id = $1
            ORDER BY d.yaratilgan_vaqt DESC
        """, message.from_user.id)

    if not qarzlar:
        await message.answer("✅ Sizda qarz yo'q!")
        return

    matn = "💰 Qarzlaringiz:\n\n"
    jami = 0
    for q in qarzlar:
        if q["holat"] != "yopiq":
            matn += (
                f"🆔 #{q['id']}\n"
                f"💵 Jami: {q['summa']:,.0f} so'm\n"
                f"⚠️ Qolgan: {q['qolgan_summa']:,.0f} so'm\n"
                f"📅 Sana: {q['birinchi_qarz_sanasi'].strftime('%d.%m.%Y')}\n\n"
            )
            jami += q["qolgan_summa"]

    matn += f"━━━━━━━━━━━━━━━\n💳 Jami qarz: {jami:,.0f} so'm"
    await message.answer(matn, reply_markup=kb.mijoz_asosiy())

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGISTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def register(dp: Dispatcher):
    dp.message.register(start, CommandStart())
    dp.message.register(bekor_va_bosh_menu, F.text == "❌ Bekor qilish")
    dp.message.register(buyurtma_boshlash, F.text == "🛒 Buyurtma berish")
    dp.message.register(buyurtmalarim, F.text == "📋 Buyurtmalarim")
    dp.message.register(qarzlarim, F.text == "💰 Qarzlarim")
    dp.message.register(mahsulot_tanlash, BuyurtmaHolat.mahsulot_turi)
    dp.message.register(miqdor_kiritish, BuyurtmaHolat.miqdor)
    dp.message.register(telefon_kiritish, BuyurtmaHolat.telefon)
    dp.message.register(manzil_kiritish, BuyurtmaHolat.manzil)
    dp.callback_query.register(bekor_qilish_callback, F.data.startswith("bekor_"))
    dp.callback_query.register(guruh_qabul_callback, F.data.startswith("guruh_qabul_"))
    dp.callback_query.register(guruh_yetkazdi_callback, F.data.startswith("guruh_yetkazdi_"))
    dp.callback_query.register(guruh_yetkazolmadi_callback, F.data.startswith("guruh_yetkazolmadi_"))
    dp.callback_query.register(tolov_turi_callback, F.data.startswith("tolov_"))