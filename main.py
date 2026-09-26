import logging
import math
import aiohttp
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# --- CONFIGURATION ---
TOKEN = "8986389422:AAFLALfo_GQ133AWtXplLQWh7vvGJbk5Oek"
ADMIN_ID = 8741292312 # Your Telegram ID
CHANNEL_ID = "@IdeasToClientsOfficial"  # Your Private Channel ID
WEBHOOK_URL = "https://course-enrollment-bot.onrender.com/webhook" # You will get this in Step 3
COURSE_PRICE_STARS = 100  # Amount in Telegram Stars

# Telegram Fragment payout rate ($0.0133 per Star) guarantees you receive the exact Naira equivalent.
STAR_PAYOUT_USD = 0.0133

bot = Bot(token=TOKEN)
dp = Dispatcher()


class Payment(StatesGroup):
    waiting_for_receipt = State()


# --- DYNAMIC EXCHANGE RATE CALCULATION ---
async def get_stars_amount(naira_price: int) -> int:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://open.er-api.com/v6/latest/USD") as resp:
                data = await resp.json()
                ngn_rate = data['rates']['NGN']
                usd_amount = naira_price / ngn_rate
                return math.ceil(usd_amount / STAR_PAYOUT_USD)
    except Exception:
        # Emergency fallback rate if the API goes offline
        return math.ceil((naira_price / 1500) / STAR_PAYOUT_USD)


# --- BOT LOGIC: START MENU ---
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 IdeasToClients Course (₦20,000)", callback_data="menu_course")],
        [InlineKeyboardButton(text="🛒 Shop: Lovable Pro Lite (₦15,000)", callback_data="menu_lovable")]
    ])
    await message.answer("Welcome! Please select the item you want to purchase:", reply_markup=keyboard)


# --- BOT LOGIC: SUB-MENUS ---
@dp.callback_query(F.data == "menu_course")
async def course_menu(callback: types.CallbackQuery):
    await callback.answer()
    stars_price = await get_stars_amount(20000)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Pay with {stars_price} Stars ⭐️", callback_data=f"stars_course_{stars_price}")],
        [InlineKeyboardButton(text="Pay ₦20,000 via Bank Transfer 🏦", callback_data="bank_course")]
    ])
    await callback.message.edit_text("🎓 **IdeasToClients Course**\nPrice: ₦20,000\n\nChoose your payment method:",
                                     reply_markup=keyboard, parse_mode="Markdown")


@dp.callback_query(F.data == "menu_lovable")
async def lovable_menu(callback: types.CallbackQuery):
    await callback.answer()
    stars_price = await get_stars_amount(15000)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Pay with {stars_price} Stars ⭐️", callback_data=f"stars_lovable_{stars_price}")],
        [InlineKeyboardButton(text="Pay ₦15,000 via Bank Transfer 🏦", callback_data="bank_lovable")]
    ])
    description = (
        "🛒 **Lovable Pro Lite**\n"
        "• 300 Credits + 5 Credits Daily\n"
        "• 1 Year Duration\n"
        "• Fast Activation\n\n"
        "Price: ₦15,000\n\n"
        "Choose your payment method:"
    )
    await callback.message.edit_text(description, reply_markup=keyboard, parse_mode="Markdown")


# --- STARS PAYMENT ROUTING ---
@dp.callback_query(F.data.startswith("stars_"))
async def process_stars_payment(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    item_type = parts[1]  # "course" or "lovable"
    amount = int(parts[2])

    title = "IdeasToClients Course" if item_type == "course" else "Lovable Pro Lite"
    payload = f"payload_{item_type}"

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description="Fast and secure payment via Telegram Stars.",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=amount)]
    )


@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload

    if payload == "payload_course":
        invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await message.answer(
            f"Payment successful! ⭐️ Here is your access link to IdeasToClients:\n{invite_link.invite_link}")
        await bot.send_message(ADMIN_ID,
                               f"⭐️ New Stars payment for IdeasToClients Course from ID {message.from_user.id}!")

    elif payload == "payload_lovable":
        await message.answer(
            "Payment successful! ⭐️ Your Lovable Pro Lite activation is being processed. The admin will contact you shortly.")
        await bot.send_message(ADMIN_ID,
                               f"⭐️ New Stars payment for Lovable Pro Lite from @{message.from_user.username or message.from_user.id}! Please activate their account.")


# --- BANK TRANSFER ROUTING ---
@dp.callback_query(F.data.startswith("bank_"))
async def process_bank_payment(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    item_type = callback.data.split("_")[1]
    await state.update_data(item_type=item_type)

    price = "₦20,000" if item_type == "course" else "₦15,000"
    item_name = "IdeasToClients Course" if item_type == "course" else "Lovable Pro Lite"

    account_details = (
        f"🏦 **Bank Details for {item_name}**\n"
        f"Amount: {price}\n"
        "Bank: OPay\n"
        "Acct: 1234567890\n"
        "Name: ONIPEDE BOLAJI VICTOR\n\n"
        "Please transfer the exact amount and send a screenshot of the receipt here."
    )
    await callback.message.edit_text(account_details, parse_mode="Markdown")
    await state.set_state(Payment.waiting_for_receipt)


@dp.message(Payment.waiting_for_receipt, F.photo)
async def receipt_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item_type = data.get("item_type", "unknown")
    username = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
    item_name = "IdeasToClients Course (₦20,000)" if item_type == "course" else "Lovable Pro Lite (₦15,000)"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Approve ✅", callback_data=f"approve_{item_type}_{message.from_user.id}")],
        [InlineKeyboardButton(text="Reject ❌", callback_data=f"reject_{item_type}_{message.from_user.id}")]
    ])

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"🧾 **New Bank Transfer**\nFrom: {username}\nItem: {item_name}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await message.answer(
        "Receipt sent to admin (@miniapploverofficial) for verification. You will be notified shortly.")
    await state.clear()


# --- ADMIN APPROVAL LOGIC ---
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    item_type = parts[1]
    user_id = int(parts[2])

    if item_type == "course":
        invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await bot.send_message(chat_id=user_id,
                               text=f"Payment Approved! ✅ Here is your link to IdeasToClients:\n{invite_link.invite_link}")
    elif item_type == "lovable":
        await bot.send_message(chat_id=user_id,
                               text="Payment Approved! ✅ Your Lovable Pro Lite is now active. Please check your email or await further instructions.")

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n**Status:** Approved ✅",
                                        parse_mode="Markdown")


@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    user_id = int(parts[2])

    await bot.send_message(chat_id=user_id,
                           text="Your payment was rejected. Please contact @miniapploverofficial for support.")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n**Status:** Rejected ❌",
                                        parse_mode="Markdown")


# --- FASTAPI WEBHOOK LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}


@app.get("/keepalive")
async def keepalive():
    return {"status": "awake"}