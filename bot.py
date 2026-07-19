import os
from web3 import Web3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

PRIVATE_KEY = None
BOT_TOKEN = None

for key, value in os.environ.items():
    if 'PRIVATE_KEY' in key:
        PRIVATE_KEY = value.strip()
    if 'BOT_TOKEN' in key:
        BOT_TOKEN = value.strip()

if not PRIVATE_KEY or not BOT_TOKEN:
    raise ValueError("BOT_TOKEN atau PRIVATE_KEY KOSONG!")

# RPC ETHEREUM L1 - KARENA DEPOSIT DILAKUIN DI L1
RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/7EAMKBlBmPENaZeJ4uuRt"  # BENER
L1_BRIDGE = Web3.to_checksum_address("0x919aa27d5278BC98bf40BA5A79be468B91f061dA")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eth_balance = w3.from_wei(w3.eth.get_balance(acct.address), 'ether')
        await update.message.reply_text(
            f'Bot Teqoin Bridge L1→L2 Aktif!\n\n'
            f'Wallet: `{acct.address}`\n'
            f'Balance L1: {eth_balance:.4f} ETH\n\n'
            f'Pake: /deposit 0.01\n'
            f'⚠️ Deposit butuh 15 menit & gas L1 $10-50'
        )
    except Exception as e:
        await update.message.reply_text(f'RPC Error: {e}\n\nCek API Key Alchemy')
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text('Pake: /deposit 0.01\n\nMin 0.01 ETH')
            return

        amount = float(context.args[0])
        if amount < 0.01:
            await update.message.reply_text('Min deposit 0.01 ETH bro, gas L1 mahal')
            return

        balance = w3.eth.get_balance(acct.address)
        if balance < w3.to_wei(amount + 0.01, 'ether'): # +0.01 buat gas
            await update.message.reply_text(f'ETH L1 kurang bro. Balance: {w3.from_wei(balance, "ether"):.4f} ETH')
            return

        tx = {
            'to': L1_BRIDGE,
            'value': w3.to_wei(amount, 'ether'),
            'gas': 100000,
            'gasPrice': w3.eth.gas_price, # pake gas price real-time L1
            'nonce': w3.eth.get_transaction_count(acct.address),
            'chainId': 1, # Ethereum Mainnet
        }
        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

        await update.message.reply_text(
            f'✅ Deposit dikirim ke L1!\n\n'
            f'Amount: {amount} ETH\n'
            f'TX: {tx_hash.hex()}\n'
            f'Etherscan: https://etherscan.io/tx/{tx_hash.hex()}\n\n'
            f'⏱️ Tunggu ~15 menit. ETH bakal muncul di TeQoin L2 otomatis.\n'
            f'Cek di: https://explorer.teqoin.io'
        )
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("deposit", deposit)) # ganti nama command
app.add_handler(CommandHandler("bridge", deposit)) # alias biar gak bingung
print("Bot jalan...")
app.run_polling()
