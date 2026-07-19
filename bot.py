import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

# === CONFIG RAILWAY ENV ===
BOT_TOKEN = os.environ['BOT_TOKEN']
PRIVATE_KEY = os.environ['PRIVATE_KEY']
WALLET_ADDRESS = Web3.to_checksum_address(os.environ['WALLET_ADDRESS'])
CHAIN_ID = 12001

# === RPC AUTO PICK ===
RPC_LIST = [
    "https://rpc.teqoin.io/testnet",
    "https://rpc.teqoin.io",
    "https://testnet.teqoin.io/rpc"
]

web3 = None
RPC_URL = ""
for rpc in RPC_LIST:
    try:
        temp_web3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
        if temp_web3.is_connected():
            web3 = temp_web3
            RPC_URL = rpc
            print(f"Connected to {rpc}")
            break
    except Exception:
        continue

if not web3:
    raise Exception("Semua RPC TeQoin mati bre")

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
    }
}

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gas = web3.eth.gas_price / 10**18
        msg = f"=== TeQoin Bot Testnet ===\nRPC: {RPC_URL}\nGas ETH: {gas:.10f}\n\n"
        for token, data in TOKEN_LIST.items():
            contract = web3.eth.contract(address=data["address"], abi=ERC20_ABI)
            balance = contract.functions.balanceOf(WALLET_ADDRESS).call() / 10**data["decimals"]
            msg += f"{token}: {balance:.4f}\n"
        msg += "\nCommand:\n/k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x123... 5"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error /start: {str(e)}")

async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        addr_from_pk = web3.eth.account.from_key(PRIVATE_KEY).address
        eth_balance = web3.eth.get_balance(WALLET_ADDRESS) / 10**18

        msg = f"RPC: {RPC_URL}\n"
        msg += f"WALLET_ADDRESS ENV: {WALLET_ADDRESS}\n"
        msg += f"Address dari PRIVATE_KEY: {addr_from_pk}\n"
        msg += f"Saldo ETH Gas: {eth_balance:.6f}\n"

        if WALLET_ADDRESS.lower() == addr_from_pk.lower():
            msg += "✅ Private Key COCOK"
        else:
            msg += "❌ Private Key BEDA SAMA ADDRESS"

        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

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
            amount = 10**13
        elif token in ["USDT", "USDC"]:
            amount = 10000
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
    app.add_handler(CommandHandler("cek", cek))
    app.add_handler(CommandHandler("k", handle_k_command))
    app.run_polling()

if __name__ == "__main__":
    main()
