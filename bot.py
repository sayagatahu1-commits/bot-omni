import os
import logging
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = int(os.getenv("CHAIN_ID", "97"))
RPC_URL = "https://rpc.teqoin.io/testnet"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
sender_address = w3.eth.account.from_key(PRIVATE_KEY).address

# List token lu
TOKENS = {
    "USDT": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9",
    "USDC": "0xe819eb5be34b20f1fec012c0daf960397a0fb386",
    "DAI": "0xb96a869c74be2ed561d95a77408505371f287d16",
    "TTEQ": "NATIVE" # Buat kirim coin native
}

# ABI standar ERC20 buat transfer
erc20_abi = [{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot TeQoin Testnet Ready!\n\n"
        "Format:\n"
        "/send USDT 0xAlamat 1.5\n"
        "/send TTEQ 0xAlamat 0.01\n"
        "/balance USDT\n"
        "/balance TTEQ"
    )

async def send_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args)!= 3:
            await update.message.reply_text("Format: /send TOKEN 0xAlamat 1.5\nContoh: /send USDT 0xE26175623a2A923F076c78da46f3C03ec89f802C 0.01")
            return

        token_symbol = context.args[0].upper()
        to_address = Web3.to_checksum_address(context.args[1])
        amount = float(context.args[2])

        if token_symbol not in TOKENS:
            await update.message.reply_text(f"Token ga ada woy. Pilih: {', '.join(TOKENS.keys())}")
            return

        # Kalo kirim native TTEQ
        if TOKENS[token_symbol] == "NATIVE":
            tx = {
                'nonce': w3.eth.get_transaction_count(sender_address),
                'to': to_address,
                'value': w3.to_wei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': w3.to_wei('5', 'gwei'),
                'chainId': CHAIN_ID
            }
        # Kalo kirim token ERC20
        else:
            contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]), abi=erc20_abi)
            amount_wei = w3.to_wei(amount, 'ether') # Asumsi semua token 18 decimal
            tx = contract.functions.transfer(to_address, amount_wei).build_transaction({
                'from': sender_address,
                'nonce': w3.eth.get_transaction_count(sender_address),
                'gas': 100000,
                'gasPrice': w3.to_wei('5', 'gwei'),
                'chainId': CHAIN_ID
            })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        await update.message.reply_text(f"✅ {token_symbol} Terkirim!\nTx: 0x{tx_hash.hex()}")

    except Exception as e:
        await update.message.reply_text(f"Error woy: {e}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args)!= 1:
            await update.message.reply_text("Format: /balance TOKEN\nContoh: /balance USDT")
            return

        token_symbol = context.args[0].upper()
        if token_symbol not in TOKENS:
            await update.message.reply_text(f"Token ga ada woy. Pilih: {', '.join(TOKENS.keys())}")
            return

        if TOKENS[token_symbol] == "NATIVE":
            balance = w3.eth.get_balance(sender_address)
            await update.message.reply_text(f"Saldo TTEQ: {w3.from_wei(balance, 'ether')}")
        else:
            contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]), abi=erc20_abi)
            balance = contract.functions.balanceOf(sender_address).call()
            await update.message.reply_text(f"Saldo {token_symbol}: {w3.from_wei(balance, 'ether')}")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("send", send_token))
app.add_handler(CommandHandler("balance", balance))
app.run_polling()
