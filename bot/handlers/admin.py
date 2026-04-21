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
class AdminHolat(StatesGroup):
    courier_ism = State()
    courier_tur = State()
    courier_telegram_id = State()
    xarajat_tur = State()
    xarajat_summa = State()
    xarajat_izoh = State()
    buyurtma_tayinlash = State()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YORDAMCHI FUNKSIYA
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HANDLERLAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def start(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer(
            "❌ Siz admin sifatida ro'yxatdan o'tmagansiz!\n"
            "Bosh admin bilan bog'laning."
        )
        return

    await message.answer(
        f"Assalomu aleykum, {message.from_user.first_name}! 👋\n"
        f"Admin paneliga xush kelibsiz!",
        reply_markup=kb.admin_asosiy()
    )

async def statistika(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
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

    await message.answer(
        f"📊 Bugungi statistika ({bugun.strftime('%d.%m.%Y')}):\n\n"
        f"🆕 Yangi: {stats['yangi'] or 0} ta\n"
        f"✅ Qabul qilindi: {stats['qabul'] or 0} ta\n"
        f"🚚 Yetkazildi: {stats['yetkazildi'] or 0} ta\n"
        f"❌ Yetkazilmadi: {stats['yetkazilmadi'] or 0} ta\n"
        f"🚫 Bekor: {stats['bekor'] or 0} ta\n\n"
        f"💧 Baklashka: {stats['baklashka'] or 0} ta\n"
        f"🚰 Litr suv: {stats['litr'] or 0} L\n\n"
        f"💰 Jami qarz: {jami_qarz:,.0f} so'm",
        reply_markup=kb.admin_asosiy()
    )

async def buyurtmalar(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
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
        await message.answer("📦 Hozircha faol buyurtma yo'q.")
        return

    for order in orders:
        tur = "Baklashka" if order["mahsulot_tur"] == "baklashka" else "Litr"
        tolov_map = {"naqt": "💵 Naqt", "click": "📱 Click", "qarz": "📝 Qarz"}
        status_map = {
            "yangi": "🆕 Yangi",
            "qabul_qilindi": "✅ Qabul qilindi"
        }
        courier_ism = order["courier_ism"] or "Tayinlanmagan"

        matn = (
            f"🆔 #{order['id']}\n"
            f"💧 {tur} — {order['miqdor']}\n"
            f"📞 {order['telefon']}\n"
            f"📍 {order['manzil']}\n"
            f"💳 {tolov_map.get(order['tolov_turi'], '')}\n"
            f"🚚 Yetkazuvchi: {courier_ism}\n"
            f"📌 {status_map.get(order['status'], order['status'])}\n"
            f"🕐 {order['yaratilgan_vaqt'].strftime('%d.%m.%Y %H:%M')}"
        )

        # Yangi buyurtmaga yetkazuvchi tayinlash tugmasi
        if order["status"] == "yangi":
            pool2 = await db.get_pool()
            async with pool2.acquire() as conn2:
                couriers = await conn2.fetch("""
                    SELECT id, ism FROM couriers WHERE aktiv = true
                """)

            if couriers:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                tugmalar = []
                for c in couriers:
                    tugmalar.append([InlineKeyboardButton(
                        text=f"👤 {c['ism']}",
                        callback_data=f"tasdiq_{order['id']}_{c['id']}"
                    )])
                markup = InlineKeyboardMarkup(inline_keyboard=tugmalar)
                await message.answer(matn, reply_markup=markup)
            else:
                await message.answer(matn)
        else:
            await message.answer(matn)

async def tayinlash_callback(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    order_id = int(parts[1])
    courier_id = int(parts[2])

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders 
            SET yetkazuvchi_id = $1, status = 'qabul_qilindi'
            WHERE id = $2
        """, courier_id, order_id)

        courier = await conn.fetchrow("""
            SELECT ism, telegram_id FROM couriers WHERE id = $1
        """, courier_id)

        order = await conn.fetchrow("""
            SELECT * FROM orders WHERE id = $1
        """, order_id)

    tur = "Baklashka (18.9L)" if order["mahsulot_tur"] == "baklashka" else "Litr suv"
    tolov_map = {"naqt": "💵 Naqt", "click": "📱 Click", "qarz": "📝 Qarz"}

    # Yetkazuvchiga xabar yuborish
    try:
        await bot.send_message(
            courier["telegram_id"],
            f"🆕 Yangi buyurtma tayinlandi!\n\n"
            f"🆔 #{order['id']}\n"
            f"💧 {tur} — {order['miqdor']}\n"
            f"📞 {order['telefon']}\n"
            f"📍 {order['manzil']}\n"
            f"💳 {tolov_map.get(order['tolov_turi'], '')}",
            reply_markup=kb.courier_buyurtma_inline(order_id)
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text +
        f"\n\n✅ {courier['ism']} ga tayinlandi!"
    )
    await callback.answer("✅ Tayinlandi!")

async def yetkazuvchilar(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        couriers = await conn.fetch("""
            SELECT c.id, c.ism, c.tur, c.aktiv,
                COUNT(o.id) FILTER (
                    WHERE DATE(o.yaratilgan_vaqt) = CURRENT_DATE
                    AND o.status = 'yetkazildi'
                ) as bugun
            FROM couriers c
            LEFT JOIN orders o ON o.yetkazuvchi_id = c.id
            GROUP BY c.id
            ORDER BY c.ism
        """)

    if not couriers:
        await message.answer("👥 Yetkazuvchilar yo'q.")
        return

    matn = "👥 Yetkazuvchilar:\n\n"
    for c in couriers:
        aktiv = "✅" if c["aktiv"] else "❌"
        tur = "Baklashka" if c["tur"] == "baklashka" else "Litr"
        matn += (
            f"{aktiv} {c['ism']} ({tur})\n"
            f"   Bugun: {c['bugun']} ta yetkazdi\n\n"
        )

    await message.answer(matn, reply_markup=kb.admin_asosiy())

async def qarzlar(message: Message):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        qarzlar = await conn.fetch("""
            SELECT d.id, d.mijoz_telegram_id, d.summa,
                   d.qolgan_summa, d.holat,
                   d.birinchi_qarz_sanasi,
                   c.ism as courier_ism
            FROM debts d
            LEFT JOIN couriers c ON d.yetkazuvchi_id = c.id
            WHERE d.holat != 'yopiq'
            ORDER BY d.birinchi_qarz_sanasi
        """)

    if not qarzlar:
        await message.answer("✅ Hozircha ochiq qarz yo'q!")
        return

    matn = "💰 Ochiq qarzlar:\n\n"
    jami = 0
    for q in qarzlar:
        matn += (
            f"🆔 #{q['id']}\n"
            f"👤 Mijoz ID: {q['mijoz_telegram_id']}\n"
            f"💵 Jami: {q['summa']:,.0f} so'm\n"
            f"⚠️ Qolgan: {q['qolgan_summa']:,.0f} so'm\n"
            f"🚚 Yetkazuvchi: {q['courier_ism'] or '-'}\n"
            f"📅 {q['birinchi_qarz_sanasi'].strftime('%d.%m.%Y')}\n\n"
        )
        jami += q["qolgan_summa"]

    matn += f"━━━━━━━━━━━━━━━\n💳 Jami: {jami:,.0f} so'm"
    await message.answer(matn, reply_markup=kb.admin_asosiy())

async def xarajatlar(message: Message, state: FSMContext):
    if not await admin_bormi(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return

    await state.set_state(AdminHolat.xarajat_tur)
    await message.answer(
        "💸 Xarajat turini kiriting:\nMasalan: Yoqilg'i, Ta'mirlash, Boshqa",
        reply_markup=kb.bekor_qilish()
    )

async def xarajat_tur(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.admin_asosiy())
        return

    await state.update_data(tur=message.text.strip())
    await state.set_state(AdminHolat.xarajat_summa)
    await message.answer(
        "💵 Summani kiriting (so'mda):\nMasalan: 150000",
        reply_markup=kb.bekor_qilish()
    )

async def xarajat_summa(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.admin_asosiy())
        return

    try:
        summa = float(message.text.replace(",", "").replace(" ", ""))
        if summa <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ To'g'ri summa kiriting. Masalan: 150000")
        return

    await state.update_data(summa=summa)
    await state.set_state(AdminHolat.xarajat_izoh)
    await message.answer(
        "📝 Izoh kiriting (ixtiyoriy):\n"
        "Yoki 'O'tkazish' deb yozing",
        reply_markup=kb.bekor_qilish()
    )

async def xarajat_izoh(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=kb.admin_asosiy())
        return

    data = await state.get_data()
    izoh = None if message.text == "O'tkazish" else message.text.strip()
    admin_id = await admin_id_olish(message.from_user.id)
    await state.clear()

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO expenses (tur, summa, izoh, admin_id)
            VALUES ($1, $2, $3, $4)
        """, data["tur"], data["summa"], izoh, admin_id)

    await message.answer(
        f"✅ Xarajat qo'shildi!\n\n"
        f"📌 Tur: {data['tur']}\n"
        f"💵 Summa: {data['summa']:,.0f} so'm\n"
        f"📝 Izoh: {izoh or '-'}",
        reply_markup=kb.admin_asosiy()
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGISTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def register(dp: Dispatcher):
    dp.message.register(start, CommandStart())
    dp.message.register(statistika, F.text == "📊 Statistika")
    dp.message.register(buyurtmalar, F.text == "📦 Buyurtmalar")
    dp.message.register(yetkazuvchilar, F.text == "👥 Yetkazuvchilar")
    dp.message.register(qarzlar, F.text == "💰 Qarzlar")
    dp.message.register(xarajatlar, F.text == "💸 Xarajatlar")
    dp.message.register(xarajat_tur, AdminHolat.xarajat_tur)
    dp.message.register(xarajat_summa, AdminHolat.xarajat_summa)
    dp.message.register(xarajat_izoh, AdminHolat.xarajat_izoh)
    dp.callback_query.register(
        tayinlash_callback, F.data.startswith("tasdiq_")
    )