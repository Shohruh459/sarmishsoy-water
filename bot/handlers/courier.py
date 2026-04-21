import os
from datetime import datetime
from aiogram import Dispatcher, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
import keyboards as kb
import database as db

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HOLATLAR (FSM)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class YetkazuvchiHolat(StatesGroup):
    yetkazolmadi_sabab = State()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YORDAMCHI FUNKSIYA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def courier_bormi(telegram_id: int) -> bool:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        courier = await conn.fetchrow("""
            SELECT id FROM couriers 
            WHERE telegram_id = $1 AND aktiv = true
        """, telegram_id)
    return courier is not None

async def courier_id_olish(telegram_id: int) -> int:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id FROM couriers WHERE telegram_id = $1
        """, telegram_id)
    return row["id"] if row else None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HANDLERLAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def start(message: Message):
    if not await courier_bormi(message.from_user.id):
        await message.answer(
            "❌ Siz yetkazuvchi sifatida ro'yxatdan o'tmagansiz!\n"
            "Admin bilan bog'laning."
        )
        return

    await message.answer(
        f"Assalomu aleykum, {message.from_user.first_name}! 👋\n"
        f"Yetkazuvchi paneliga xush kelibsiz!",
        reply_markup=kb.courier_asosiy()
    )

async def buyurtmalarim(message: Message):
    if not await courier_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return

    courier_id = await courier_id_olish(message.from_user.id)
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        orders = await conn.fetch("""
            SELECT id, mahsulot_tur, miqdor, telefon, manzil, 
                   tolov_turi, status, yaratilgan_vaqt
            FROM orders
            WHERE yetkazuvchi_id = $1 
            AND status = 'qabul_qilindi'
            ORDER BY yaratilgan_vaqt DESC
        """, courier_id)

    if not orders:
        await message.answer("📦 Hozircha tayinlangan buyurtma yo'q.")
        return

    for order in orders:
        tur = "Baklashka (18.9L)" if order["mahsulot_tur"] == "baklashka" else "Litr suv"
        tolov_map = {"naqt": "💵 Naqt", "click": "📱 Click", "qarz": "📝 Qarz"}
        matn = (
            f"🆔 Buyurtma #{order['id']}\n"
            f"💧 {tur} — {order['miqdor']}\n"
            f"📞 {order['telefon']}\n"
            f"📍 {order['manzil']}\n"
            f"💳 {tolov_map.get(order['tolov_turi'], order['tolov_turi'])}\n"
            f"🕐 {order['yaratilgan_vaqt'].strftime('%d.%m.%Y %H:%M')}"
        )
        await message.answer(
            matn,
            reply_markup=kb.courier_buyurtma_inline(order["id"])
        )

async def yetkazdi_callback(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[1])
    pool = await db.get_pool()

    async with pool.acquire() as conn:
        order = await conn.fetchrow("""
            SELECT o.*, c.telegram_id as courier_telegram_id
            FROM orders o
            JOIN couriers c ON o.yetkazuvchi_id = c.id
            WHERE o.id = $1
        """, order_id)

        if not order:
            await callback.answer("Buyurtma topilmadi!", show_alert=True)
            return

        await conn.execute("""
            UPDATE orders SET status = 'yetkazildi' WHERE id = $1
        """, order_id)

        # Agar qarz bo'lsa — debts ga qo'shish
        if order["tolov_turi"] == "qarz":
            # Narx hisoblash (misol: baklashka=15000, litr=1000)
            narx = 15000 if order["mahsulot_tur"] == "baklashka" else 1000
            summa = narx * order["miqdor"]
            await conn.execute("""
                INSERT INTO debts 
                    (mijoz_telegram_id, yetkazuvchi_id, order_id, summa, qolgan_summa)
                VALUES ($1, $2, $3, $4, $4)
            """,
                order["mijoz_telegram_id"],
                order["yetkazuvchi_id"],
                order_id,
                summa
            )

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Yetkazildi deb belgilandi!"
    )
    await callback.answer("✅ Bajarildi!")

async def yetkazolmadi_callback(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(YetkazuvchiHolat.yetkazolmadi_sabab)
    await callback.message.answer(
        "❌ Yetkazolmadingiz. Sababini yozing:",
        reply_markup=kb.bekor_qilish()
    )
    await callback.answer()

async def yetkazolmadi_sabab(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.courier_asosiy())
        return

    data = await state.get_data()
    order_id = data["order_id"]
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders 
            SET status = 'yetkazilmadi', bekor_sabab = $1 
            WHERE id = $2
        """, message.text, order_id)

    await message.answer(
        "✅ Qayd etildi. Sabab yozildi.",
        reply_markup=kb.courier_asosiy()
    )

async def kunlik_hisobot(message: Message):
    if not await courier_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return

    courier_id = await courier_id_olish(message.from_user.id)
    bugun = datetime.now().date()
    pool = await db.get_pool()

    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'yetkazildi') as yetkazildi,
                COUNT(*) FILTER (WHERE status = 'yetkazilmadi') as yetkazilmadi,
                COUNT(*) FILTER (WHERE status = 'qabul_qilindi') as kutilmoqda,
                SUM(miqdor) FILTER (
                    WHERE status = 'yetkazildi' AND mahsulot_tur = 'baklashka'
                ) as baklashka,
                SUM(miqdor) FILTER (
                    WHERE status = 'yetkazildi' AND mahsulot_tur = 'litr'
                ) as litr
            FROM orders
            WHERE yetkazuvchi_id = $1
            AND DATE(yaratilgan_vaqt) = $2
        """, courier_id, bugun)

    await message.answer(
        f"📊 Bugungi hisobot ({bugun.strftime('%d.%m.%Y')}):\n\n"
        f"✅ Yetkazildi: {stats['yetkazildi'] or 0} ta\n"
        f"❌ Yetkazilmadi: {stats['yetkazilmadi'] or 0} ta\n"
        f"⏳ Kutilmoqda: {stats['kutilmoqda'] or 0} ta\n\n"
        f"💧 Baklashka: {stats['baklashka'] or 0} ta\n"
        f"🚰 Litr suv: {stats['litr'] or 0} L",
        reply_markup=kb.courier_asosiy()
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGISTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def register(dp: Dispatcher):
    dp.message.register(start, CommandStart())
    dp.message.register(buyurtmalarim, F.text == "📦 Buyurtmalarim")
    dp.message.register(kunlik_hisobot, F.text == "📊 Kunlik hisobot")
    dp.message.register(
        yetkazolmadi_sabab, YetkazuvchiHolat.yetkazolmadi_sabab
    )
    dp.callback_query.register(
        yetkazdi_callback, F.data.startswith("yetkazdi_")
    )
    dp.callback_query.register(
        yetkazolmadi_callback, F.data.startswith("yetkazolmadi_")
    )