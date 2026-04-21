from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIJOZ BOT TUGMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mijoz_asosiy():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Buyurtma berish")],
            [KeyboardButton(text="📋 Buyurtmalarim")],
            [KeyboardButton(text="💰 Qarzlarim")],
        ],
        resize_keyboard=True
    )

def mahsulot_turi():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💧 Baklashka (18.9L)")],
            [KeyboardButton(text="🚰 Litr suv")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

def bekor_qilish():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

def tolov_turi():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💵 Naqt")],
            [KeyboardButton(text="📱 Click")],
            [KeyboardButton(text="📝 Qarz")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

def buyurtma_bekor_inline(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Buyurtmani bekor qilish",
                callback_data=f"bekor_{order_id}"
            )]
        ]
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YETKAZUVCHI BOT TUGMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def courier_asosiy():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Buyurtmalarim")],
            [KeyboardButton(text="✅ Yetkazdim")],
            [KeyboardButton(text="❌ Yetkazolmadim")],
            [KeyboardButton(text="📊 Kunlik hisobot")],
        ],
        resize_keyboard=True
    )

def courier_buyurtma_inline(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yetkazdim",
                    callback_data=f"yetkazdi_{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Yetkazolmadim",
                    callback_data=f"yetkazolmadi_{order_id}"
                )
            ]
        ]
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADMIN BOT TUGMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def admin_asosiy():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📦 Buyurtmalar")],
            [KeyboardButton(text="👥 Yetkazuvchilar")],
            [KeyboardButton(text="💰 Qarzlar")],
            [KeyboardButton(text="💸 Xarajatlar")],
        ],
        resize_keyboard=True
    )

def admin_tasdiqlash_inline(order_id, courier_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"tasdiq_{order_id}_{courier_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"rad_{order_id}_{courier_id}"
                )
            ]
        ]
    )