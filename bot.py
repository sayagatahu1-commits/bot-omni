import os
import logging
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = int(os.getenv("CHAIN_ID", "28516"))
RPC_URL = os.getenv("RPC_URL", "https://rpc.teqoin.io/testnet") # Ambil dari Railway

w3 = Web3(Web3.HTTPProvider(RPC_URL))
sender_address = w3.eth.account.from_key(PRIVATE_KEY).address

TOKENS = {
    "USDT": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9",
    "USDC": "0xe819eb5be34b20f1fec012c0daf960397a0fb386",
    "DAI": "0xb96a869c74be2ed561d95a77408505371f287d16",
    "TTEQ": "NATIVE"
}

erc20_abi = [
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
]

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Bot TeQoin Testnet Ready!\n"
        f"Wallet: {sender_address}\n"
        f"RPC: {RPC_URL}\n"
        f"Chain ID: {CHAIN_ID}\n\n"
        "Format:\n/send USDT 0xAlamat 1.5\n/balance TTEQ"
    )

async def send_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args)!= 3:
            await update.message.reply_text("Format: /send TOKEN 0xAlamat 1.5")
            return

        token_symbol = context.args[0].upper()
        to_address = Web3.to_checksum_address(context.args[1])
        amount = float(context.args[2])

        if token_symbol not in TOKENS:
            await update.message.reply_text(f"Token ga ada. Pilih: {', '.join(TOKENS.keys())}")
            return

        if TOKENS[token_symbol] == "NATIVE":
            tx = {
                'nonce': w3.eth.get_transaction_count(sender_address),
                'to': to_address,
                'value': w3.to_wei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': w3.to_wei('5', 'gwei'),
                'chainId': CHAIN_ID
            }
        else:
            contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]), abi=erc20_abi)
            decimals = contract.functions.decimals().call()
            amount_wei = int(amount * 10**decimals)
            tx = contract.functions.transfer(to_address, amount_wei).build_transaction({
                'from': sender_address,
                'nonce': w3.eth.get_transaction_count(sender_address),
                'gas': 100000,
                'gasPrice': w3.to_wei('5', 'gwei'),
                'chainId': CHAIN_ID
            })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        await update.message.reply_text(f"✅ {token_symbol} Terkirim!\nhttps://testnet.teqchain.com/tx/0x{tx_hash.hex()}")

    except Exception as e:
        await update.message.reply_text(f"Error woy: {e}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args)!= 1:
            await update.message.reply_text("Format: /balance TOKEN")
            return

        token_symbol = context.args[0].upper()
        if TOKENS[token_symbol] == "NATIVE":
            balance = w3.eth.get_balance(sender_address)
            await update.message.reply_text(f"Saldo TTEQ: {w3.from_wei(balance, 'ether')}")
        else:
            contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]), abi=erc20_abi)
            decimals = contract.functions.decimals().call()
            balance = contract.functions.balanceOf(sender_address).call()
            await update.message.reply_text(f"Saldo {token_symbol}: {balance / 10**decimals}")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("send", send_token))
app.add_handler(CommandHandler("balance", balance))
app.run_polling()
