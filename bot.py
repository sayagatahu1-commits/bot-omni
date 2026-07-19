import os
from web3 import Web3

BOT_TOKEN = os.getenv("8686470947:AAHEhEuZ1PN2wDZzCFpHgjIcbcx6ezB9nPo")
PRIVATE_KEY = os.getenv("0x4cb91ae51c9f26e961ce3f7d0410a3091a3b2c6c16e1e067b234bf47dd93be42")
print(f"BOT_TOKEN ada gak: {BOT_TOKEN is not None}") # buat debug
print(f"PRIVATE_KEY ada gak: {PRIVATE_KEY is not None}") # buat debug

if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY KOSONG! Cek Variables Railway")

RPC_URL = "https://omni-testnet.blastapi.io/1b3c4d2e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"
# ... kode sisanya
BRIDGE = Web3.to_checksum_address("0x2D6e44f44A83D5B99BC0745f10d1C4b8BFFF0e7d")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
        await update.message.reply_text(f'Sent! TX: {tx_hash.hex()}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("bridge", bridge))
app.run_polling()
