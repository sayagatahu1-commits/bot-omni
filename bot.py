import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

# === CONFIG RAILWAY ENV ===
BOT_TOKEN = os.environ['BOT_TOKEN']
RPC_URL = "https://rpc.teqoin.io"
PRIVATE_KEY = os.environ['PRIVATE_KEY']
WALLET_ADDRESS = Web3.to_checksum_address(os.environ['WALLET_ADDRESS'])
CHAIN_ID = 12001

web3 = Web3(Web3.HTTPProvider(RPC_URL))

TOKEN_LIST = {
    "DAI": {
        "address": Web3.to_checksum_address("0x3d01aE3e8b5c5fF26B0c4B9E9b3A0F1D4A8e2E7b"),
        "decimals": 18
    },
    "USDT": {
        "address": Web3.to_checksum_address("0x4c21E5dB8b8d6B5e6C7F7a7F7a7F7a7F"),
        "decimals": 6
    },
    "USDC": {
        "address": Web3.to_checksum_address("0x6b17A7c5D8E5F6A9B8C7D6E5F4A3B2C1D0E9F8A7"),
        "decimals": 6
    }
}

ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gas = web3.eth.gas_price / 10**18
        msg = f"=== TeQoin Bot Testnet ===\nGas ETH: {gas:.10f}\n\n"
        for token, data in TOKEN_LIST.items():
            contract = web3.eth.contract(address=data["address"], abi=ERC20_ABI)
            balance = contract.functions.balanceOf(WALLET_ADDRESS).call() / 10**data["decimals"]
            msg += f"{token}: {balance:.4f}\n"
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

        if token == "DAI":
            amount = 10**13 # 0.01 DAI
        elif token in ["USDT", "USDC"]:
            amount = 10000 # 0.01 USDT/USDC
        else:
            amount = 1

        balance = contract.functions.balanceOf(WALLET_ADDRESS).call()
        if balance < amount * repeat:
            await update.message.reply_text(f"Saldo {token} kurang. Butuh minimal {amount * repeat / 10**decimals} {token}")
            return

        await update.message.reply_text(f"Mulai spam {repeat}x {amount/10**decimals} {token} ke {to_address[:10]}...")

        sukses = 0
        for i in range(repeat):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
                gas_price = int(web3.eth.gas_price * 1.5)

                tx = contract.functions.transfer(to_address, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': gas_price,
                    'chainId': CHAIN_ID
                })

                signed = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)

                await update.message.reply_text(f"[{i+1}/{repeat}] Broadcast: {tx_hash.hex()}")

                try:
                    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                    if receipt.status == 1:
                        sukses += 1
                        await update.message.reply_text(f"[{i+1}/{repeat}] ✅ CONFIRMED Block {receipt.blockNumber}")
                    else:
                        await update.message.reply_text(f"[{i+1}/{repeat}] ❌ FAILED: TX Reverted")
                except Exception as e:
                    await update.message.reply_text(f"[{i+1}/{repeat}] ⚠️ TIMEOUT: {type(e).__name__}")

                await asyncio.sleep(5)

            except Exception as e:
                await update.message.reply_text(f"Gagal TX ke-{i+1}: {str(e)[:100]}")
                break

        await update.message.reply_text(f"SELESAI. Berhasil {sukses}/{repeat}x kirim {token}")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("k", handle_k_command))
    app.run_polling()

if __name__ == "__main__":
    main()
