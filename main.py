import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

# --- CONFIGURATION ---
TOKEN = "8986389422:AAFLALfo_GQ133AWtXplLQWh7vvGJbk5Oek"  # Paste your real token
ADMIN_ID = 8741292312  # @miniapploverofficial
WEBHOOK_URL = "https://course-enrollment-bot.vercel.app/webhook"
COURSE_INVITE_LINK = "https://t.me/+05IthcLeP3xlZWQ0"

bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- BOT LOGIC: START MENU ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 IdeasToClients Course (₦20,000)", callback_data="buy_course")],
        [InlineKeyboardButton(text="🛒 Shop: Lovable Pro Lite (₦15,000)", callback_data="buy_lovable")]
    ])
    await message.answer("Welcome! Please select the item you want to purchase via Bank Transfer:",
                         reply_markup=keyboard)


# --- BUY ACTIONS (HTML Formatting to prevent crashes) ---
@dp.callback_query(F.data == "buy_course")
async def buy_course(callback: types.CallbackQuery):
    await callback.answer()
    account_details = (
        "🎓 <b>IdeasToClients Course</b>\n\n"
        "🏦 <b>Bank Details</b>\n"
        "Amount: ₦20,000\n"
        "Bank: OPay\n"
        "Acct: 1234567890\n"
        "Name: ONIPEDE BOLAJI VICTOR\n\n"
        "Please transfer the exact amount and send a screenshot of the receipt here."
    )
    await callback.message.edit_text(account_details, parse_mode="HTML")


@dp.callback_query(F.data == "buy_lovable")
async def buy_lovable(callback: types.CallbackQuery):
    await callback.answer()
    account_details = (
        "🛒 <b>Lovable Pro Lite</b>\n"
        "• 300 Credits + 5 Credits Daily\n"
        "• 1 Year Duration | Fast Activation\n\n"
        "🏦 <b>Bank Details</b>\n"
        "Amount: ₦15,000\n"
        "Bank: OPay\n"
        "Acct: 1234567890\n"
        "Name: ONIPEDE BOLAJI VICTOR\n\n"
        "Please transfer the exact amount and send a screenshot of the receipt here."
    )
    await callback.message.edit_text(account_details, parse_mode="HTML")


# --- STATELESS RECEIPT UPLOAD ---
@dp.message(F.photo)
async def receipt_received(message: types.Message):
    username = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)

    # Universal admin buttons. The admin looks at the amount and decides what to approve.
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Approve Course ✅", callback_data=f"approve_course_{message.from_user.id}")],
        [InlineKeyboardButton(text="Approve Lovable ✅", callback_data=f"approve_lovable_{message.from_user.id}")],
        [InlineKeyboardButton(text="Reject ❌", callback_data=f"reject_none_{message.from_user.id}")]
    ])

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"🧾 <b>New Receipt Uploaded</b>\nFrom: {username}\n\n<i>Verify the amount and select what they paid for:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await message.answer(
        "✅ Receipt sent to admin (@miniapploverofficial) for verification. You will be notified shortly.")


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
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n<b>Status:</b> Approved for Course ✅", parse_mode="HTML")

    elif item_type == "lovable":
        # ForceReply forces the user's Telegram app to reply directly to this specific message statelessly
        await bot.send_message(
            chat_id=user_id,
            text="🎉 Payment Approved for Lovable Pro Lite! ✅\n\nPlease <b>reply directly to this message</b> with your email address to receive your activation instructions.",
            parse_mode="HTML",
            reply_markup=ForceReply(selective=True)
        )
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n<b>Status:</b> Approved for Lovable ✅", parse_mode="HTML")


@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    await callback.answer()
    user_id = int(callback.data.split("_")[2])

    await bot.send_message(chat_id=user_id,
                           text="Your payment was rejected. Please contact @miniapploverofficial for support.")
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n<b>Status:</b> Rejected ❌",
                                        parse_mode="HTML")


# --- STATELESS EMAIL COLLECTION ---
@dp.message(F.reply_to_message)
async def email_received(message: types.Message):
    # Only process the email if they are replying to the specific Lovable approval message
    if "Lovable Pro Lite" in message.reply_to_message.text:
        email = message.text
        await message.answer(
            "✅ Thank you! Your email has been confirmed. Your Lovable Pro Lite items and instructions will be sent to you shortly.")

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🛒 <b>Lovable Pro Lite Delivery Info</b>\n"
                 f"User: @{message.from_user.username or message.from_user.id}\n"
                 f"Email: <code>{email}</code>\n\n"
                 f"Please email them the activation instructions.",
            parse_mode="HTML"
        )


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