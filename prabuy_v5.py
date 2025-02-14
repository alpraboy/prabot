import asyncio
import logging
import numpy as np
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# Token dan Chat ID langsung di dalam script (GANTI DENGAN YANG BENAR)
TOKEN = ""
CHAT_ID = ""

# Validasi token agar tidak menyebabkan error Unauthorized
if not TOKEN.startswith("8124") or ":" not in TOKEN:
    raise ValueError("[ERROR] Token bot Telegram tidak valid! Periksa kembali.")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
selected_market = "EURUSD=X"

async def get_forex_data():
    print(f"[INFO] Mengambil data untuk {selected_market}")
    data = yf.download(selected_market, period="7d", interval="15m")  # Timeframe lebih kecil (15 menit)

    if data.empty:
        print("[WARNING] Data market kosong. Tidak ada data terbaru.")
        return None

    return data["Close"].values

def calculate_indicators(close_prices):
    if close_prices is None or len(close_prices) < 50:
        print("[WARNING] Data tidak cukup untuk menghitung indikator.")
        return 0, 0, 0, 0, 50, 0

    def ema(values, period):
        alpha = 2 / (period + 1)
        ema_values = [float(values[0])]
        for price in values[1:]:
            ema_values.append((float(price) - ema_values[-1]) * alpha + ema_values[-1])
        return ema_values[-1]

    try:
        ema20 = ema(close_prices[-20:], 20)  # EMA lebih cepat
        ema50 = ema(close_prices[-50:], 50)

        macd = ema(close_prices[-12:], 12) - ema(close_prices[-26:], 26)
        signal = ema(close_prices[-9:], 9)

        deltas = np.diff(close_prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))

        atr = np.mean(np.abs(np.diff(close_prices[-14:])))  # ATR sederhana

        print(f"""
        [DEBUG] Indikator:
        - Harga Terakhir: {float(close_prices[-1]):.4f}
        - EMA20: {float(ema20):.4f}
        - EMA50: {float(ema50):.4f}
        - MACD: {float(macd):.4f}, Signal: {float(signal):.4f}
        - RSI: {float(rsi):.2f}
        - ATR: {float(atr):.5f}
        """)

        return ema20, ema50, macd, signal, rsi, atr

    except Exception as e:
        print(f"[ERROR] Gagal menghitung indikator: {e}")
        return 0, 0, 0, 0, 50, 0

async def check_signal():
    close_prices = await get_forex_data()
    if close_prices is None:
        return "HOLD"

    ema20, ema50, macd, signal, rsi, atr = calculate_indicators(close_prices)
    harga_terakhir = close_prices[-1]

    if atr > 0.0005 and rsi > 50 and harga_terakhir > ema20 > ema50 and macd > signal:
        return "BUY"
    elif atr > 0.0005 and rsi < 50 and harga_terakhir < ema20 < ema50 and macd < signal:
        return "SELL"
    return "HOLD"

async def send_signal():
    signal = await check_signal()
    if signal in ["BUY", "SELL"]:
        message = f"Sinyal Trading: {signal}\nMarket: {selected_market}"
        print(f"[INFO] Mengirim sinyal: {message}")
        await bot.send_message(CHAT_ID, message)
    else:
        print("[INFO] Sinyal HOLD diabaikan.")

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Bot aktif! Gunakan /market untuk memilih market.")

@dp.message(Command("market"))
async def market_command(message: types.Message):
    await message.answer(
        "Pilih market:\n"
        "/eurusd - EUR/USD\n"
        "/usdjpy - USD/JPY\n"
        "/gbpusd - GBP/USD"
    )

@dp.message(Command("eurusd"))
async def select_eurusd(message: types.Message):
    global selected_market
    selected_market = "EURUSD=X"
    await message.answer("Market diubah ke EUR/USD.")
    await send_signal()

@dp.message(Command("usdjpy"))
async def select_usdjpy(message: types.Message):
    global selected_market
    selected_market = "USDJPY=X"
    await message.answer("Market diubah ke USD/JPY.")
    await send_signal()

@dp.message(Command("gbpusd"))
async def select_gbpusd(message: types.Message):
    global selected_market
    selected_market = "GBPUSD=X"
    await message.answer("Market diubah ke GBP/USD.")
    await send_signal()

async def auto_send_signal():
    while True:
        await send_signal()
        print("[INFO] Menunggu 2 menit...")
        await asyncio.sleep(120)

async def main():
    print("[🚀] Bot berjalan...")
    asyncio.create_task(auto_send_signal())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
