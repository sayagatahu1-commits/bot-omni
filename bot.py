import os
from web3 import Web3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8686470947:AAHEhEuZ1PN2wDZzCFpHgjIcbcx6ezB9nPo"
PRIVKEY = "0x4cb91ae51c9f26e961ce3f7d0410a3091a3b2c6c16e1e067b234bf47dd93be42"
RPC = "https://omni-testnet.g.alchemy.com/v2/xxx"
BRIDGE = Web3.to_checksum_address("0x2D6e44F44A83D5B998C0745f10d1C4b8BffF0e7d")

w3 = Web3(Web3.HTTPProvider(RPC))
acct = w3.eth.account.from_key(PRIVKEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Omni nyala bro")

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(context.args[0])
        tx = {
            'to': BRIDGE,
            'value': w3.to_wei(amount, 'ether'),
            'gas': 100000,
            'gasPrice': w3.to_wei('5', 'gwei'),
            'nonce': w3.eth.get_transaction_count(acct.address),
            'chainId': 80002
        }
        signed = w3.eth.account.sign_transaction(tx, PRIVKEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        await update.message.reply_text(f"Sent! TX: {tx_hash.hex()}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("bridge", bridge))
app.run_polling()
