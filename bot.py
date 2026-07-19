import os
from web3 import Web3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Ambil env variable - anti typo
PRIVATE_KEY = None
BOT_TOKEN = None

for key, value in os.environ.items():
    if 'PRIVATE_KEY' in key:
        PRIVATE_KEY = value.strip()
    if 'BOT_TOKEN' in key:
        BOT_TOKEN = value.strip()

print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
print(f"PRIVATE_KEY: {PRIVATE_KEY[:10]}...")

if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY KOSONG!")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN KOSONG!")

RPC_URL = "https://testnet.omni.network"
BRIDGE = Web3.to_checksum_address("0x2D6e44f44A83D5B99BC0745f10d1C4b8BFFF0e7d")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text('Pake: /bridge 0.01')
            return

        amount = float(context.args[0])
        tx = {
            'to': BRIDGE,
            'value': w3.to_wei(amount, 'ether'),
            'gas': 100000,
            'gasPrice': w3.to_wei('5', 'gwei'),
            'nonce': w3.eth.get_transaction_count(acct.address),
            'chainId': 165,
        }
        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        await update.message.reply_text(f'Bridge sent! TX: {tx_hash.hex()}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("bridge", bridge))
print("Bot jalan...")
app.run_polling()
