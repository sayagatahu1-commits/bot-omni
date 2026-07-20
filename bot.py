import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3
from eth_account import Account

# --- KONFIGURASI ---
TOKEN = os.getenv("TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
import os
import logging
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from eth_account import Account

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
RPC_URL = os.getenv("RPC_URL")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

TOKEN_CONTRACTS = {
    "usdt": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9",
    "usdc": "0xe819eb5be34b20f1fec012c0daf960397a0fb386",
    "dai": "0xb96a869c74be2ed561d95a77408505371f287d16"
}

ERC20_ABI = [{"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot TeQoin Testnet Spam Ready!\n\n"
        "/send usdt 0xAlamat 1.5\n"
        "/balance usdt\n"
        "/debug"
    )

async def send_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        token = context.args[0].lower()
        to_addr = context.args[1]
        amount = float(context.args[2])

        if token not in TOKEN_CONTRACTS:
            await update.message.reply_text("Token ga ada. Pilih: usdt / usdc / dai")
            return

        msg = await update.message.reply_text(f"Kirim {amount} {token.upper()} ke {to_addr[:10]}...")

        contract = w3.eth.contract(address=TOKEN_CONTRACTS[token], abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount_wei = int(amount * 10**decimals)
        nonce = w3.eth.get_transaction_count(account.address, 'pending')

        tx = contract.functions.transfer(to_addr, amount_wei).build_transaction({
            'chainId': CHAIN_ID,
            'gas': 100000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': nonce,
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()

        await msg.edit_text(f"Done! ✅\nTx: https://explorer.teqoin.io/testnet/tx/{tx_hash}")

    except Exception as e:
        await update.message.reply_text(f"Error woy: {str(e)}")

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        token = context.args[0].lower() if context.args else "usdt"
        contract = w3.eth.contract(address=TOKEN_CONTRACTS[token], abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        bal = contract.functions.balanceOf(account.address).call()
        await update.message.reply_text(f"Saldo {token.upper()}: {bal / 10**decimals}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def debug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    native = w3.from_wei(w3.eth.get_balance(account.address), 'ether')
    await update.message.reply_text(
        f"Wallet: {account.address}\n"
        f"Connected: {w3.is_connected()}\n"
        f"Block: {w3.eth.block_number}\n"
        f"Gas Native: {native}"
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", send_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("debug", debug_cmd))
    app.run_polling()
