import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

RPC_URL = "https://rpc.teqoin.io/testnet" # ← INI YG BENER
CHAIN_ID = 420377

web3 = Web3(Web3.HTTPProvider(RPC_URL))

# ========== ABI UNTUK BACA TOKEN ERC20 ==========
ERC20_ABI = [
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
]

# ========== TEMPEL 3 CONTRACT ASLI DARI TEQOIN WALLET DI SINI ==========
TOKEN_LIST = {
    "DAI": {
        "address": "0xE26175623a2A923F076c78da46f3C03ec89f802C", # Klik DAI di wallet → Copy Contract
        "decimals": 18
    },
    "USDT": {
        "address": "0xE26175623a2A923F076c78da46f3C03ec89f802C", # Klik USDT di wallet → Copy Contract
        "decimals": 6
    },
    "USDC": {
        "address": "0xE26175623a2A923F076c78da46f3C03ec89f802C", # Klik USDC di wallet → Copy Contract
        "decimals": 6
    },
}

# ========== COMMAND /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not web3.is_connected():
            await update.message.reply_text("RPC mati bre. Coba lagi ntar.")
            return

        msg = ""
        eth_balance = web3.eth.get_balance(WALLET_ADDRESS)
        msg += f"ETH: {web3.from_wei(eth_balance, 'ether'):.8f}\n"

        for name, data in TOKEN_LIST.items():
            try:
                contract = web3.eth.contract(address=web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
                balance = contract.functions.balanceOf(WALLET_ADDRESS).call()
                decimals = data["decimals"]
                formatted = balance / 10**decimals
                msg += f"{name}: {formatted:.4f}\n"
            except Exception as e:
                msg += f"{name}: Error - Contract salah\n"

        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ========== COMMAND /k ==========
async def handle_k_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Format: /k <eth/dai/usdt/usdc> <address> <jumlah>\nContoh: /k eth 0x123... 5")
        return

    token_type = args[0].lower()
    to_address = args[1]

    try:
        count = int(args[2])
    except:
        await update.message.reply_text("Jumlah harus angka")
        return

    if not web3.is_address(to_address):
        await update.message.reply_text("Address ga valid")
        return

    to_address = web3.to_checksum_address(to_address)

    if token_type == "eth":
        amount = 0.0001
        success_count = 0
        for i in range(count):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
                tx = {
                    'to': to_address,
                    'value': web3.to_wei(amount, 'ether'),
                    'gas': 21000,
                    'gasPrice': web3.eth.gas_price,
                    'nonce': nonce,
                    'chainId': CHAIN_ID
                }
                signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash)
                success_count += 1
                await update.message.reply_text(f"TX ke-{i+1} sukses")
            except Exception as e:
                await update.message.reply_text(f"TX ke-{i+1} gagal: {e}")
                break
        await update.message.reply_text(f"✅ Done {success_count}x! Total: {success_count*amount} ETH")
        return

    if token_type.upper() in TOKEN_LIST:
        token_data = TOKEN_LIST[token_type.upper()]
        amount = 0.01
        decimals = token_data["decimals"]
        contract = web3.eth.contract(address=web3.to_checksum_address(token_data["address"]), abi=ERC20_ABI)
        success_count = 0

        for i in range(count):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
                tx = contract.functions.transfer(
                    to_address,
                    int(amount * 10**decimals)
                ).build_transaction({
                    'chainId': CHAIN_ID,
                    'gas': 100000,
                    'gasPrice': web3.eth.gas_price,
                    'nonce': nonce,
                })
                signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash)
                success_count += 1
                await update.message.reply_text(f"TX ke-{i+1} sukses")
            except Exception as e:
                await update.message.reply_text(f"TX ke-{i+1} gagal: {e}")
                break
        await update.message.reply_text(f"✅ Done {success_count}x! Total: {success_count*amount} {token_type.upper()}")
    else:
        await update.message.reply_text("Token ga dikenal. Pake: eth/dai/usdt/usdc")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("k", handle_k_command))
    print("Bot jalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
