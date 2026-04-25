from datetime import datetime
from aiogram import Dispatcher, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
import keyboards as kb
import database as db
import os
from aiogram import Bot
MIJOZ_BOT_TOKEN = os.getenv("MIJOZ_BOT_TOKEN")
BAKLASHKA_GROUP_ID = int(os.getenv("BAKLASHKA_GROUP_ID", 0))
LITR_GROUP_ID = int(os.getenv("LITR_GROUP_ID", 0))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HOLATLAR (FSM)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AdminHolat(StatesGroup):
    xarajat_tur = State()
    xarajat_summa = State()
    xarajat_izoh = State()
    narx_tur = State()
    narx_qiymat = State()
    qarz_tolov_id = State()
    qarz_tolov_summa = State()
    buyurtma_telefon = State()
    buyurtma_tur = State()
    buyurtma_miqdor = State()
    buyurtma_manzil = State()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YORDAMCHI FUNKSIYALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def admin_bormi(telegram_id: int) -> bool:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        admin = await conn.fetchrow("""
            SELECT id FROM admins 
            WHERE telegram_id = $1 AND aktiv = true
        """, telegram_id)
    return admin is not None

async def admin_id_olish(telegram_id: int) -> int:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id FROM admins WHERE telegram_id = $1
        """, telegram_id)
    return row["id"] if row else None

async def narx_olish(kalit: str) -> int:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT qiymat FROM settings WHERE kalit = $1
        """, kalit)
    return int(row["qiymat"]) if row else 0

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADMIN KLAVIATURASI (КИРИЛ)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📦 Буюртмалар")],
            [KeyboardButton(text="💰 Қарзлар"), KeyboardButton(text="💸 Харажатлар")],
            [KeyboardButton(text="💲 Нархлар"), KeyboardButton(text="📞 Қўнғироқ буюртмаси")],
        ],
        resize_keyboard=True
    )

def bekor_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Бекор қилиш")],
        ],
        resize_keyboard=True
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HANDLERLAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def start(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer(
            "❌ Сиз админ сифатида рўйхатдан ўтмагансиз!\n"
            "Бош админ билан боғланинг."
        )
        return
    await message.answer(
        f"Ассалому алайкум, {message.from_user.first_name}! 👋\n"
        f"Админ панелига хуш келибсиз!",
        reply_markup=admin_menu()
    )

async def statistika(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Рухсат йўқ!")
        return

    bugun = datetime.now().date()
    pool = await db.get_pool()

    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'yangi') as yangi,
                COUNT(*) FILTER (WHERE status = 'qabul_qilindi') as qabul,
                COUNT(*) FILTER (WHERE status = 'yetkazildi') as yetkazildi,
                COUNT(*) FILTER (WHERE status = 'yetkazilmadi') as yetkazilmadi,
                COUNT(*) FILTER (WHERE status = 'bekor') as bekor,
                SUM(miqdor) FILTER (
                    WHERE status = 'yetkazildi' 
                    AND mahsulot_tur = 'baklashka'
                ) as baklashka,
                SUM(miqdor) FILTER (
                    WHERE status = 'yetkazildi' 
                    AND mahsulot_tur = 'litr'
                ) as litr
            FROM orders
            WHERE DATE(yaratilgan_vaqt) = $1
        """, bugun)

        jami_qarz = await conn.fetchval("""
            SELECT COALESCE(SUM(qolgan_summa), 0)
            FROM debts WHERE holat != 'yopiq'
        """)

        baklashka_narx = await narx_olish('baklashka_narx')
        litr_narx = await narx_olish('litr_narx')

        baklashka_soni = stats['baklashka'] or 0
        litr_soni = stats['litr'] or 0
        jami_savdo = (baklashka_soni * baklashka_narx) + (litr_soni * litr_narx)

    await message.answer(
        f"📊 Бугунги статистика ({bugun.strftime('%d.%m.%Y')}):\n\n"
        f"🆕 Янги: {stats['yangi'] or 0} та\n"
        f"✅ Қабул қилинди: {stats['qabul'] or 0} та\n"
        f"🚚 Етказилди: {stats['yetkazildi'] or 0} та\n"
        f"❌ Етказилмади: {stats['yetkazilmadi'] or 0} та\n"
        f"🚫 Бекор: {stats['bekor'] or 0} та\n\n"
        f"💧 Баклашка: {baklashka_soni} та\n"
        f"🚰 Литр сув: {litr_soni} Л\n\n"
        f"💵 Жами савдо: {jami_savdo:,.0f} сўм\n"
        f"💰 Жами қарз: {jami_qarz:,.0f} сўм",
        reply_markup=admin_menu()
    )

async def buyurtmalar(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Рухсат йўқ!")
        return

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        orders = await conn.fetch("""
            SELECT o.id, o.mahsulot_tur, o.miqdor, o.telefon,
                   o.manzil, o.tolov_turi, o.status,
                   o.yaratilgan_vaqt, c.ism as courier_ism
            FROM orders o
            LEFT JOIN couriers c ON o.yetkazuvchi_id = c.id
            WHERE o.status IN ('yangi', 'qabul_qilindi')
            ORDER BY o.yaratilgan_vaqt DESC
            LIMIT 10
        """)

    if not orders:
        await message.answer("📦 Ҳозирча фаол буюртма йўқ.")
        return

    for order in orders:
        tur = "Баклашка" if order["mahsulot_tur"] == "baklashka" else "Литр"
        tolov_map = {"naqt": "💵 Нақт", "click": "📱 Click", "qarz": "📝 Қарз"}
        status_map = {
            "yangi": "🆕 Янги",
            "qabul_qilindi": "✅ Қабул қилинди"
        }
        courier_ism = order["courier_ism"] or "Тайинланмаган"

        matn = (
            f"🆔 #{order['id']}\n"
            f"💧 {tur} — {order['miqdor']}\n"
            f"📞 {order['telefon']}\n"
            f"📍 {order['manzil']}\n"
            f"💳 {tolov_map.get(order['tolov_turi'], '')}\n"
            f"🚚 Етказувчи: {courier_ism}\n"
            f"📌 {status_map.get(order['status'], order['status'])}\n"
            f"🕐 {order['yaratilgan_vaqt'].strftime('%d.%m.%Y %H:%M')}"
        )
        await message.answer(matn)

async def qarzlar(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Рухсат йўқ!")
        return

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        # Telefon raqam bo'yicha guruhlash
        qarzlar = await conn.fetch("""
            SELECT 
                o.telefon,
                COUNT(d.id) as qarz_soni,
                SUM(d.qolgan_summa) as jami_qarz
            FROM debts d
            JOIN orders o ON d.order_id = o.id
            WHERE d.holat != 'yopiq'
            GROUP BY o.telefon
            ORDER BY jami_qarz DESC
        """)

    if not qarzlar:
        await message.answer("✅ Ҳозирча очиқ қарз йўқ!", reply_markup=admin_menu())
        return

    jami = sum(q["jami_qarz"] for q in qarzlar)

    matn = "💰 Қарздорлар рўйхати:\n\n"
    for q in qarzlar:
        matn += (
            f"📞 {q['telefon']}\n"
            f"💵 Қарз: {q['jami_qarz']:,.0f} сўм "
            f"({q['qarz_soni']} та буюртма)\n\n"
        )

    await message.answer(
        matn + f"━━━━━━━━━━━━━━━\n💳 Жами: {jami:,.0f} сўм",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📞 {q['telefon']} — {q['jami_qarz']:,.0f} сўм",
                    callback_data=f"qarz_detail_{q['telefon']}"
                )] for q in qarzlar
            ] + [
                [InlineKeyboardButton(
                    text="✅ Тўлов қабул қилиш",
                    callback_data="qarz_tolov_tanlash"
                )]
            ]
        )
    )
async def qarz_detail_callback(callback: CallbackQuery):
    telefon = callback.data.replace("qarz_detail_", "")

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        qarzlar = await conn.fetch("""
            SELECT 
                d.id, d.summa, d.qolgan_summa, 
                d.holat, d.birinchi_qarz_sanasi,
                c.ism as courier_ism,
                o.mahsulot_tur, o.miqdor, o.manzil
            FROM debts d
            JOIN orders o ON d.order_id = o.id
            LEFT JOIN couriers c ON d.yetkazuvchi_id = c.id
            WHERE d.holat != 'yopiq' AND o.telefon = $1
            ORDER BY d.birinchi_qarz_sanasi
        """, telefon)

    if not qarzlar:
        await callback.answer("Қарз топилмади!", show_alert=True)
        return

    jami = sum(float(q["qolgan_summa"]) for q in qarzlar)
    matn = f"📞 {telefon} қарзлари:\n\n"

    for q in qarzlar:
        tur = "Баклашка" if q["mahsulot_tur"] == "baklashka" else "Литр"
        matn += (
            f"🆔 Қарз #{q['id']}\n"
            f"💧 {tur} — {q['miqdor']}\n"
            f"📍 {q['manzil']}\n"
            f"🚚 {q['courier_ism'] or '-'}\n"
            f"💵 Жами: {q['summa']:,.0f} сўм\n"
            f"⚠️ Қолган: {q['qolgan_summa']:,.0f} сўм\n"
            f"📅 {q['birinchi_qarz_sanasi'].strftime('%d.%m.%Y')}\n\n"
        )

    await callback.message.answer(
        matn + f"━━━━━━━━━━━━━━━\n💳 Жами қарз: {jami:,.0f} сўм",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ Тўлов қабул қилиш",
                    callback_data=f"qarz_tolov_tel_{telefon}"
                )]
            ]
        )
    )
    await callback.answer()

async def qarz_tolov_telefon_callback(callback: CallbackQuery, state: FSMContext):
    telefon = callback.data.replace("qarz_tolov_tel_", "")
    await state.update_data(qarz_telefon=telefon)
    await state.set_state(AdminHolat.qarz_tolov_summa)
    await callback.message.answer(
        f"📞 {telefon}\n"
        f"💵 Тўлов суммасини киритинг (сўмда):\nМасалан: 50000",
        reply_markup=bekor_menu()
    )
    await callback.answer()

async def qarz_tolov_tanlash_callback(callback: CallbackQuery, state: FSMContext):
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        telefonlar = await conn.fetch("""
            SELECT DISTINCT o.telefon, SUM(d.qolgan_summa) as jami
            FROM debts d
            JOIN orders o ON d.order_id = o.id
            WHERE d.holat != 'yopiq'
            GROUP BY o.telefon
            ORDER BY jami DESC
        """)

    if not telefonlar:
        await callback.answer("Қарз йўқ!", show_alert=True)
        return

    await callback.message.answer(
        "📞 Қайси рақамдан тўлов қабул қиласиз?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📞 {t['telefon']} — {t['jami']:,.0f} сўм",
                    callback_data=f"qarz_tolov_tel_{t['telefon']}"
                )] for t in telefonlar
            ]
        )
    )
    await callback.answer()

async def qarz_tolov_callback(callback: CallbackQuery, state: FSMContext):
    qarz_id = int(callback.data.split("_")[2])
    await state.update_data(qarz_id=qarz_id)
    await state.set_state(AdminHolat.qarz_tolov_summa)
    await callback.message.answer(
        "💵 Тўлов суммасини киритинг (сўмда):\nМасалан: 50000",
        reply_markup=bekor_menu()
    )
    await callback.answer()

async def qarz_tolov_summa(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    try:
        summa = float(message.text.replace(",", "").replace(" ", ""))
        if summa <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Тўғри сумма киритинг. Масалан: 50000")
        return

    data = await state.get_data()
    telefon = data.get("qarz_telefon")
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        # Telefon bo'yicha barcha ochiq qarzlarni olish
        qarzlar = await conn.fetch("""
            SELECT d.id, d.qolgan_summa
            FROM debts d
            JOIN orders o ON d.order_id = o.id
            WHERE d.holat != 'yopiq' AND o.telefon = $1
            ORDER BY d.birinchi_qarz_sanasi
        """, telefon)

        qolgan_summa = summa
        for qarz in qarzlar:
            if qolgan_summa <= 0:
                break

            qarz_qolgan = float(qarz["qolgan_summa"])

            if qolgan_summa >= qarz_qolgan:
                # Bu qarzni to'liq yopish
                await conn.execute("""
                    UPDATE debts SET qolgan_summa = 0, holat = 'yopiq'
                    WHERE id = $1
                """, qarz["id"])
                await conn.execute("""
                    INSERT INTO debt_payments 
                        (debt_id, summa, tolov_turi, kim_kiritdi, tasdiqlangan)
                    VALUES ($1, $2, 'naqt', $3, true)
                """, qarz["id"], qarz_qolgan, message.from_user.full_name)
                qolgan_summa -= qarz_qolgan
            else:
                # Qisman to'lash
                yangi_qolgan = qarz_qolgan - qolgan_summa
                await conn.execute("""
                    UPDATE debts 
                    SET qolgan_summa = $1, holat = 'qisman'
                    WHERE id = $2
                """, yangi_qolgan, qarz["id"])
                await conn.execute("""
                    INSERT INTO debt_payments 
                        (debt_id, summa, tolov_turi, kim_kiritdi, tasdiqlangan)
                    VALUES ($1, $2, 'naqt', $3, true)
                """, qarz["id"], qolgan_summa, message.from_user.full_name)
                qolgan_summa = 0

        # Qolgan qarzni tekshirish
        qolgan = await conn.fetchval("""
            SELECT COALESCE(SUM(qolgan_summa), 0)
            FROM debts d
            JOIN orders o ON d.order_id = o.id
            WHERE d.holat != 'yopiq' AND o.telefon = $1
        """, telefon)

    holat_matn = "✅ Барча қарзлар тўланди!" if float(qolgan) == 0 else f"⚠️ Қолган қарз: {float(qolgan):,.0f} сўм"

    await message.answer(
        f"✅ Тўлов қабул қилинди!\n\n"
        f"📞 {telefon}\n"
        f"💵 Тўланди: {summa:,.0f} сўм\n"
        f"{holat_matn}",
        reply_markup=admin_menu()
    )
async def xarajatlar(message: Message, state: FSMContext):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Рухсат йўқ!")
        return

    await state.set_state(AdminHolat.xarajat_tur)
    await message.answer(
        "💸 Харажат турини киритинг:\nМасалан: Ёқилғи, Таъмирлаш, Бошқа",
        reply_markup=bekor_menu()
    )

async def xarajat_tur(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    await state.update_data(tur=message.text.strip())
    await state.set_state(AdminHolat.xarajat_summa)
    await message.answer(
        "💵 Суммани киритинг (сўмда):\nМасалан: 150000",
        reply_markup=bekor_menu()
    )

async def xarajat_summa(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    try:
        summa = float(message.text.replace(",", "").replace(" ", ""))
        if summa <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Тўғри сумма киритинг. Масалан: 150000")
        return

    await state.update_data(summa=summa)
    await state.set_state(AdminHolat.xarajat_izoh)
    await message.answer(
        "📝 Изоҳ киритинг (ихтиёрий):\n"
        "Ёки 'Ўтказиш' деб ёзинг",
        reply_markup=bekor_menu()
    )

async def xarajat_izoh(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    data = await state.get_data()
    izoh = None if message.text == "Ўтказиш" else message.text.strip()
    admin_id = await admin_id_olish(message.from_user.id)
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO expenses (tur, summa, izoh, admin_id)
            VALUES ($1, $2, $3, $4)
        """, data["tur"], data["summa"], izoh, admin_id)

    await message.answer(
        f"✅ Харажат қўшилди!\n\n"
        f"📌 Тур: {data['tur']}\n"
        f"💵 Сумма: {data['summa']:,.0f} сўм\n"
        f"📝 Изоҳ: {izoh or '-'}",
        reply_markup=admin_menu()
    )

async def narxlar(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Рухсат йўқ!")
        return

    baklashka_narx = await narx_olish('baklashka_narx')
    litr_narx = await narx_olish('litr_narx')

    await message.answer(
        f"💲 Ҳозирги нархлар:\n\n"
        f"💧 Баклашка (18.9Л): {baklashka_narx:,} сўм\n"
        f"🚰 Литр сув: {litr_narx:,} сўм\n\n"
        f"Қайсини ўзгартирасиз?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="💧 Баклашка нархи",
                    callback_data="narx_baklashka"
                )],
                [InlineKeyboardButton(
                    text="🚰 Литр нархи",
                    callback_data="narx_litr"
                )]
            ]
        )
    )

async def narx_tanlash_callback(callback: CallbackQuery, state: FSMContext):
    tur = callback.data.split("_")[1]
    await state.update_data(narx_tur=tur)
    await state.set_state(AdminHolat.narx_qiymat)

    tur_nomi = "Баклашка" if tur == "baklashka" else "Литр сув"
    await callback.message.answer(
        f"💲 {tur_nomi} учун янги нарх киритинг (сўмда):\nМасалан: 12000",
        reply_markup=bekor_menu()
    )
    await callback.answer()

async def narx_qiymat(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    try:
        qiymat = int(message.text.replace(",", "").replace(" ", ""))
        if qiymat <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Тўғри сумма киритинг. Масалан: 12000")
        return

    data = await state.get_data()
    kalit = f"{data['narx_tur']}_narx"
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE settings SET qiymat = $1 WHERE kalit = $2
        """, str(qiymat), kalit)

    tur_nomi = "Баклашка" if data['narx_tur'] == "baklashka" else "Литр сув"
    await message.answer(
        f"✅ Нарх янгиланди!\n\n"
        f"💧 {tur_nomi}: {qiymat:,} сўм",
        reply_markup=admin_menu()
    )
async def qongiroq_buyurtma(message: Message, state: FSMContext):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Рухсат йўқ!")
        return
    await state.set_state(AdminHolat.buyurtma_telefon)
    await message.answer(
        "📞 Телефон рақамни киритинг:\nМасалан: +998901234567",
        reply_markup=bekor_menu()
    )

async def buyurtma_telefon(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    telefon = message.text.strip()
    if not telefon.startswith("+") or len(telefon) < 10:
        await message.answer(
            "❗ Телефон рақам нотўғри.\nМасалан: +998901234567"
        )
        return

    await state.update_data(telefon=telefon)
    await state.set_state(AdminHolat.buyurtma_tur)
    await message.answer(
        "💧 Маҳсулот турини танланг:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💧 Баклашка (18.9Л)")],
                [KeyboardButton(text="🚰 Литр сув")],
                [KeyboardButton(text="❌ Бекор қилиш")],
            ],
            resize_keyboard=True
        )
    )

async def buyurtma_tur(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    if message.text == "💧 Баклашка (18.9Л)":
        tur = "baklashka"
    elif message.text == "🚰 Литр сув":
        tur = "litr"
    else:
        await message.answer("Илтимос, тугмалардан фойдаланинг.")
        return

    await state.update_data(mahsulot_turi=tur)
    await state.set_state(AdminHolat.buyurtma_miqdor)

    if tur == "baklashka":
        await message.answer(
            "Нечта баклашка керак?\nМасалан: 2",
            reply_markup=bekor_menu()
        )
    else:
        await message.answer(
            "Неча литр керак?\nМасалан: 10",
            reply_markup=bekor_menu()
        )

async def buyurtma_miqdor(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    try:
        miqdor = float(message.text.replace(",", "."))
        if miqdor <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Тўғри рақам киритинг. Масалан: 2")
        return

    await state.update_data(miqdor=miqdor)
    await state.set_state(AdminHolat.buyurtma_manzil)
    await message.answer(
        "📍 Манзилни киритинг:\nМасалан: Мустақиллик кўчаси 15-уй",
        reply_markup=bekor_menu()
    )

async def buyurtma_manzil(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

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
            f"📞 {message.from_user.full_name}",
            data["telefon"],
            data["mahsulot_turi"],
            data["miqdor"],
            message.text.strip()
        )

    tur_nomi = "Баклашка (18.9Л)" if data["mahsulot_turi"] == "baklashka" else "Литр сув"
    miqdor_son = int(data["miqdor"]) if float(data["miqdor"]).is_integer() else data["miqdor"]

    await message.answer(
        f"✅ Буюртма яратилди!\n\n"
        f"🆔 #{order_id}\n"
        f"💧 {tur_nomi} — {miqdor_son}\n"
        f"📞 {data['telefon']}\n"
        f"📍 {message.text.strip()}",
        reply_markup=admin_menu()
    )

    # Guruhga xabar yuborish
    guruh_id = BAKLASHKA_GROUP_ID if data["mahsulot_turi"] == "baklashka" else LITR_GROUP_ID
    if guruh_id:
        bot = Bot(token=MIJOZ_BOT_TOKEN)
        try:
            await bot.send_message(
                guruh_id,
                f"🆕 ЯНГИ БУЮРТМА #{order_id}\n"
                f"(📞 Қўнғироқ орқали)\n\n"
                f"💧 {tur_nomi} — {miqdor_son}\n"
                f"📞 {data['telefon']}\n"
                f"📍 {message.text.strip()}\n"
                f"🕐 {datetime.now().strftime('%H:%M')}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Қабул қилдим",
                            callback_data=f"guruh_qabul_{order_id}"
                        )]
                    ]
                )
            )
        finally:
            await bot.session.close()
async def buyurtma_tolov(message: Message, state: FSMContext):
    if message.text == "❌ Бекор қилиш":
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=admin_menu())
        return

    tolov_map = {
        "💵 Нақт": "naqt",
        "📱 Click": "click",
        "📝 Қарз": "qarz"
    }

    if message.text not in tolov_map:
        await message.answer("Илтимос, тугмалардан фойдаланинг.")
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
            f"📞 {message.from_user.full_name}",
            data["telefon"],
            data["mahsulot_turi"],
            data["miqdor"],
            data["manzil"],
            tolov
        )

    tur_nomi = "Баклашка (18.9Л)" if data["mahsulot_turi"] == "baklashka" else "Литр сув"
    miqdor_son = int(data["miqdor"]) if float(data["miqdor"]).is_integer() else data["miqdor"]

    await message.answer(
        f"✅ Буюртма яратилди!\n\n"
        f"🆔 #{order_id}\n"
        f"💧 {tur_nomi} — {miqdor_son}\n"
        f"📞 {data['telefon']}\n"
        f"📍 {data['manzil']}\n"
        f"💳 {tolov_nomi}",
        reply_markup=admin_menu()
    )

    # Guruhga xabar yuborish
    guruh_id = BAKLASHKA_GROUP_ID if data["mahsulot_turi"] == "baklashka" else LITR_GROUP_ID
    if guruh_id:
        bot = Bot(token=MIJOZ_BOT_TOKEN)
        try:
            await bot.send_message(
                guruh_id,
                f"🆕 ЯНГИ БУЮРТМА #{order_id}\n"
                f"(📞 Қўнғироқ орқали)\n\n"
                f"💧 {tur_nomi} — {miqdor_son}\n"
                f"📞 {data['telefon']}\n"
                f"📍 {data['manzil']}\n"
                f"💳 {tolov_nomi}\n"
                f"🕐 {datetime.now().strftime('%H:%M')}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Қабул қилдим",
                            callback_data=f"guruh_qabul_{order_id}"
                        )]
                    ]
                )
            )
        finally:
            await bot.session.close()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGISTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def register(dp: Dispatcher):
    dp.message.register(start, CommandStart())
    dp.message.register(statistika, F.text == "📊 Статистика")
    dp.message.register(buyurtmalar, F.text == "📦 Буюртмалар")
    dp.message.register(qarzlar, F.text == "💰 Қарзлар")
    dp.message.register(xarajatlar, F.text == "💸 Харажатлар")
    dp.message.register(narxlar, F.text == "💲 Нархлар")
    dp.message.register(qongiroq_buyurtma, F.text == "📞 Қўнғироқ буюртмаси")
    dp.message.register(buyurtma_telefon, AdminHolat.buyurtma_telefon)
    dp.message.register(buyurtma_tur, AdminHolat.buyurtma_tur)
    dp.message.register(buyurtma_miqdor, AdminHolat.buyurtma_miqdor)
    dp.message.register(buyurtma_manzil, AdminHolat.buyurtma_manzil)
    dp.message.register(xarajat_tur, AdminHolat.xarajat_tur)
    dp.message.register(xarajat_summa, AdminHolat.xarajat_summa)
    dp.message.register(xarajat_izoh, AdminHolat.xarajat_izoh)
    dp.message.register(narx_qiymat, AdminHolat.narx_qiymat)
    dp.message.register(qarz_tolov_summa, AdminHolat.qarz_tolov_summa)
    dp.callback_query.register(narx_tanlash_callback, F.data.startswith("narx_"))
    dp.callback_query.register(qarz_detail_callback, F.data.startswith("qarz_detail_"))
    dp.callback_query.register(qarz_tolov_tanlash_callback, F.data == "qarz_tolov_tanlash")
    dp.callback_query.register(qarz_tolov_telefon_callback, F.data.startswith("qarz_tolov_tel_"))