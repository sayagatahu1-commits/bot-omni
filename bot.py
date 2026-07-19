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
        "address": "0xb96a869c74be2ed561d95a77408505371f287d16", # Klik DAI di wallet → Copy Contract
        "decimals": 18
    },
    "USDT": {
        "address": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9", # Klik USDT di wallet → Copy Contract
        "decimals": 6
    },
    "USDC": {
        "address": "0xe819eb5be34b20f1fec012c0daf960397a0fb386", # Klik USDC di wallet → Copy Contract
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
def handle_k_command(update, context):
    try:
        args = context.args
        if len(args)!= 3:
            update.message.reply_text("Format: /k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x123... 5")
            return

        token = args[0].upper()
        to_address = Web3.to_checksum_address(args[1])
        repeat = int(args[2])

        if token not in TOKEN_LIST:
            update.message.reply_text(f"Token {token} ga ada. Pilih: DAI, USDT, USDC")
            return
        
        if repeat > 20:
            update.message.reply_text("Max 20x sekali spam bre biar ga ngelag")
            return

        token_data = TOKEN_LIST[token]
        contract = web3.eth.contract(address=token_data["address"], abi=ERC20_ABI)
        decimals = token_data["decimals"]
        
        # KIRIM PALING KECIL = 1 unit terkecil
        amount = 1 # 1 wei token = 0.000001 USDT/USDC atau 0.000000000000000001 DAI
        
        # Cek balance dulu
        balance = contract.functions.balanceOf(WALLET_ADDRESS).call()
        if balance < amount * repeat:
            update.message.reply_text(f"Saldo {token} kurang. Butuh {amount * repeat / 10**decimals} {token}")
            return

        update.message.reply_text(f"Gas spam {repeat}x {token} ke {to_address[:10]}...")
        
        sukses = 0
        for i in range(repeat):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
                gas_price = int(web3.eth.gas_price * 1.3) # Naikin 30% biar tembus
                
                tx = contract.functions.transfer(to_address, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': nonce,
                    'gas': 80000,
                    'gasPrice': gas_price,
                    'chainId': CHAIN_ID
                })

                signed = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
                sukses += 1
                time.sleep(3) # Delay 3 detik biar nonce aman
                
            except Exception as e:
                update.message.reply_text(f"Gagal ke-{i+1}: {str(e)[:50]}")
                break

        update.message.reply_text(f"Done. Berhasil {sukses}/{repeat}x kirim {amount/10**decimals} {token}")

    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("k", handle_k_command))
    print("Bot jalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
