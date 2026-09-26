import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.base import StorageKey

# --- CONFIGURATION ---
TOKEN = "8986389422:AAFLALfo_GQ133AWtXplLQWh7vvGJbk5Oek" # Paste your real token
ADMIN_ID = 8741292312  # @miniapploverofficial
WEBHOOK_URL = "https://course-enrollment-bot.vercel.app/webhook"

COURSE_INVITE_LINK = "https://t.me/+05IthcLeP3xlZWQ0"

bot = Bot(token=TOKEN)
dp = Dispatcher()


class Payment(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_email = State()


# --- BOT LOGIC: START MENU ---
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 IdeasToClients Course (₦20,000)", callback_data="buy_course")],
        [InlineKeyboardButton(text="🛒 Shop: Lovable Pro Lite (₦15,000)", callback_data="buy_lovable")]
    ])
    await message.answer("Welcome! Please select the item you want to purchase via Bank Transfer:",
                         reply_markup=keyboard)


# --- BUY ACTIONS (Shows Bank Details) ---
@dp.callback_query(F.data == "buy_course")
async def buy_course(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(item_type="course")

    account_details = (
        "🎓 **IdeasToClients Course**\n\n"
        "🏦 **Bank Details**\n"
        "Amount: ₦20,000\n"
        "Bank: OPay\n"
        "Acct: 1234567890\n"
        "Name: ONIPEDE BOLAJI VICTOR\n\n"
        "Please transfer the exact amount and send a screenshot of the receipt here."
    )
    await callback.message.edit_text(account_details, parse_mode="Markdown")
    await state.set_state(Payment.waiting_for_receipt)


@dp.callback_query(F.data == "buy_lovable")
async def buy_lovable(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(item_type="lovable")

    account_details = (
        "🛒 **Lovable Pro Lite**\n"
        "• 300 Credits + 5 Credits Daily\n"
        "• 1 Year Duration | Fast Activation\n\n"
        "🏦 **Bank Details**\n"
        "Amount: ₦15,000\n"
        "Bank: OPay\n"
        "Acct: 1234567890\n"
        "Name: ONIPEDE BOLAJI VICTOR\n\n"
        "Please transfer the exact amount and send a screenshot of the receipt here."
    )
    await callback.message.edit_text(account_details, parse_mode="Markdown")
    await state.set_state(Payment.waiting_for_receipt)


# --- RECEIPT UPLOAD ROUTING ---
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
        await bot.send_message(chat_id=user_id,
                               text=f"🎉 Payment Approved! ✅\n\nCongratulations! Here is your link to join the PAID group:\n{COURSE_INVITE_LINK}")

    elif item_type == "lovable":
        # Force the user into the waiting_for_email state from the admin's chat
        user_state = FSMContext(
            storage=dp.storage,
            key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        )
        await user_state.set_state(Payment.waiting_for_email)
        await bot.send_message(chat_id=user_id,
                               text="🎉 Payment Approved! ✅\n\nPlease reply to this message with your **email address** to receive your Lovable Pro Lite activation and instructions.")

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


# --- POST-PAYMENT EMAIL COLLECTION ---
@dp.message(Payment.waiting_for_email, F.text)
async def email_received(message: types.Message, state: FSMContext):
    email = message.text
    await message.answer(
        "✅ Thank you! Your email has been confirmed. Your Lovable Pro Lite items and instructions will be sent to you shortly.")

    # Notify Admin to fulfill the order
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛒 **Lovable Pro Lite Delivery Info**\n"
             f"User: @{message.from_user.username or message.from_user.id}\n"
             f"Email: `{email}`\n\n"
             f"Please email them the activation instructions.",
        parse_mode="Markdown"
    )
    await state.clear()


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