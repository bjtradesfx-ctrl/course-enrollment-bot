import logging
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

bot = Bot(token=TOKEN)
dp = Dispatcher()

class Payment(StatesGroup):
    waiting_for_receipt = State()

# --- BOT LOGIC ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Pay with Telegram Stars ⭐️", callback_data="pay_stars")],
        [InlineKeyboardButton(text="Pay via Bank Transfer 🏦", callback_data="pay_bank")]
    ])
    await message.answer("Welcome! Choose how you want to enroll in the course:", reply_markup=keyboard)

@dp.callback_query(F.data == "pay_stars")
async def process_stars_payment(callback: types.CallbackQuery):
    await callback.answer() # Stops the loading spinner
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Course Enrollment",
        description="Full access to the private channel.",
        payload="course_payload",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Course", amount=COURSE_PRICE_STARS)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
    await message.answer(f"Payment successful! ⭐️ Here is your one-time access link:\n{invite_link.invite_link}")

@dp.callback_query(F.data == "pay_bank")
async def process_bank_payment(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer() # Stops the loading spinner
    account_details = "🏦 **Bank Details:**\nBank: OPay\nAcct: 1234567890\nName: ONIPEDE BOLAJI VICTOR\n\nPlease transfer and send a screenshot of the receipt here."
    await callback.message.answer(account_details, parse_mode="Markdown")
    await state.set_state(Payment.waiting_for_receipt)

@dp.message(Payment.waiting_for_receipt, F.photo)
async def receipt_received(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Approve ✅", callback_data=f"approve_{user_id}")],
        [InlineKeyboardButton(text="Reject ❌", callback_data=f"reject_{user_id}")]
    ])
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id,
                         caption=f"New payment from user ID: {user_id}", reply_markup=keyboard)
    await message.answer("Receipt sent to admin for verification. Please wait.")
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    await callback.answer() # Stops the loading spinner
    user_id = int(callback.data.split("_")[1])
    invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
    await bot.send_message(chat_id=user_id, text=f"Payment Approved! ✅ Here is your link:\n{invite_link.invite_link}")
    await callback.message.edit_caption(caption="Approved ✅")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    await callback.answer() # Stops the loading spinner
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(chat_id=user_id, text="Your payment was rejected. Please contact support.")
    await callback.message.edit_caption(caption="Rejected ❌")

# --- FASTAPI WEBHOOK LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(WEBHOOK_URL)
    yield
    # delete_webhook() intentionally removed

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}

@app.get("/keepalive")
async def keepalive():
    return {"status": "awake"}