import os
from web3 import Web3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio

# ========== AMBIL DARI RAILWAY ENV ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY") 
WALLET_ADDRESS = Web3.to_checksum_address(os.environ.get("WALLET_ADDRESS"))
RPC_URL = "https://rpc.teqoin.io/testnet"
CHAIN_ID = 420377

# ========== CONTRACT TEQOIN TESTNET ASLI ==========
# ========== CONTRACT TEQOIN TESTNET ASLI ==========
TOKEN_LIST = {
    "DAI": {
        "address": Web3.to_checksum_address("0xb96a869c74be2ed561d95a77408505371f287d16"),
        "decimals": 18
    },
    "USDT": {
        "address": Web3.to_checksum_address("0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9"),
        "decimals": 6
    },
    "USDC": {
        "address": Web3.to_checksum_address("0xe819eb5be34b20f1fec012c0daf960397a0fb386"),
        "decimals": 6
    },
}

ERC20_ABI = [
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}
]

web3 = Web3(Web3.HTTPProvider(RPC_URL))

# ========== SISANYA SAMA PERSIS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = "=== TeQoin Bot Testnet ===\n"
        eth_bal = web3.from_wei(web3.eth.get_balance(WALLET_ADDRESS), 'ether')
        msg += f"Gas ETH: {eth_bal:.8f}\n\n"

        for name, data in TOKEN_LIST.items():
            contract = web3.eth.contract(address=data["address"], abi=ERC20_ABI)
            balance = contract.functions.balanceOf(WALLET_ADDRESS).call()
            human_bal = balance / 10**data["decimals"]
            msg += f"{name}: {human_bal:.4f}\n"

        msg += "\nCommand:\n/k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x123... 5"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error /start: {str(e)}")

async def handle_k_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args)!= 3:
            await update.message.reply_text("Format: /k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x7382... 5")
            return

        token = args[0].upper()
        to_address = Web3.to_checksum_address(args[1])
        repeat = int(args[2])

        if token not in TOKEN_LIST:
            await update.message.reply_text(f"Token {token} ga ada. Pilih: DAI, USDT, USDC")
            return

        if repeat < 1 or repeat > 20:
            await update.message.reply_text("Jumlah spam 1-20x aja bre")
            return

        token_data = TOKEN_LIST[token]
        contract = web3.eth.contract(address=token_data["address"], abi=ERC20_ABI)
        decimals = token_data["decimals"]

        # === PASTE BLOK INI BUAT GANTI amount = 1 ===
        if token == "DAI":
            amount = 10**13 # 0.01 DAI
        elif token in ["USDT", "USDC"]:
            amount = 10000 # 0.01 USDT/USDC
        else:
            amount = 1
        # === SAMPE SINI ===

        balance = contract.functions.balanceOf(WALLET_ADDRESS).call()
        if balance < amount * repeat:
            await update.message.reply_text(f"Saldo {token} kurang. Butuh minimal {amount * repeat / 10**decimals} {token}")
            return

        await update.message.reply_text(f"Mulai spam {repeat}x {amount/10**decimals} {token} ke {to_address[:10]}...")
        
        sukses = 0
for i in range(repeat):
    try:
        nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
        gas_price = int(web3.eth.gas_price * 1.3)

        tx = contract.functions.transfer(to_address, amount).build_transaction({
            'from': WALLET_ADDRESS,
            'nonce': nonce,
            'gas': 80000,
            'gasPrice': gas_price,
            'chainId': CHAIN_ID
        })

        signed = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
        
        # === TAMBAHIN INI BIAR NUNGGU SAMPE CONFIRMED ===
        await update.message.reply_text(f"[{i+1}/{repeat}] Broadcast: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            sukses += 1
            await update.message.reply_text(f"[{i+1}/{repeat}] ✅ SUKSES CONFIRMED")
        else:
            await update.message.reply_text(f"[{i+1}/{repeat}] ❌ FAILED DI CHAIN")
        # === SAMPE SINI ===
        
        await asyncio.sleep(3)

    except Exception as e:
        await update.message.reply_text(f"Gagal TX ke-{i+1}: {str(e)[:80]}")
        break
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("k", handle_k_command))
    print("Bot jalan...")
    app.run_polling()

if __name__ == '__main__':
    main()
