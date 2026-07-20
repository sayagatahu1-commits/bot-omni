import os
import logging
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application  # <<< TAMBAHIN Application

TOKEN = os.getenv("TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = int(os.getenv("CHAIN_ID", "28516"))
RPC_URL = os.getenv("RPC_URL", "https://rpc.teqoin.io/testnet")

TOKENS = {
    "USDT": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9",
    "USDC": "0xe819eb5be34b20f1fec012c0daf960397a0fb386", 
    "DAI": "0xb96a869c74be2ed561d95a77408505371f287d16",
    "ETH": "NATIVE"
}

# <<< TEMPEL DI SINI >>>
ERC20_ABI = [
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}
]

BRIDGE_CONTRACT = "0xbc6ad4965241ea4260eb571c936576a4f537d67b"
BRIDGE_ABI = [{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"uint256","name":"_amount","type":"uint256"},{"internalType":"uint256","name":"_destinationChainId","type":"uint256"}],"name":"bridgeToken","outputs":[],"stateMutability":"payable","type":"function"}]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
sender_address = w3.eth.account.from_key(PRIVATE_KEY).address

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eth_balance = w3.from_wei(w3.eth.get_balance(sender_address), 'ether')
    await update.message.reply_text(
        f"Wallet:\n{sender_address}\n"
        f"Saldo ETH: {eth_balance}\n"
        f"Chain ID RPC: {CHAIN_ID}\n\n"
        f"Format:\n"
        f"/send TOKEN 0xAlamat 0.01 [jumlah]\n"
        f"/bridge TOKEN 0.01 [jumlah]\n"
        f"/balance TOKEN\n\n"
        f"Contoh farming poin:\n"
        f"/bridge USDT 0.01 10"
    )

async def send_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Format: /send TOKEN 0xAlamat 0.01 5
        if len(context.args) < 3 or len(context.args) > 4:
            await update.message.reply_text("Format: /send TOKEN 0xAlamat 1.5 [jumlah]\nContoh: /send DAI 0x123.. 0.01 5")
            return

        token_symbol = context.args[0].upper()
        to_address = Web3.to_checksum_address(context.args[1])
        amount = float(context.args[2])
        repeat = int(context.args[3]) if len(context.args) == 4 else 1

        if repeat > 20:
            await update.message.reply_text("Maks 20x sekali kirim biar ga spam woy")
            return

        if token_symbol not in TOKENS:
            await update.message.reply_text(f"Token ga ada. Pilih: {', '.join(TOKENS.keys())}")
            return

        await update.message.reply_text(f"Proses kirim {token_symbol} {amount} sebanyak {repeat}x...")

        success_count = 0
        total_fee = 0

        for i in range(repeat):
            try:
                nonce = w3.eth.get_transaction_count(sender_address)
                base_fee = w3.eth.get_block('latest')['baseFeePerGas']
                max_priority_fee = 0
                max_fee_per_gas = base_fee

                if TOKENS[token_symbol] == "NATIVE":
                    tx = {
                        'nonce': nonce,
                        'to': to_address,
                        'value': w3.to_wei(amount, 'ether'),
                        'maxFeePerGas': max_fee_per_gas,
                        'maxPriorityFeePerGas': max_priority_fee,
                        'chainId': CHAIN_ID,
                        'type': 2,
                        'gas': 21000
                    }
                else:
                    contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]), abi=erc20_abi)
                    decimals = contract.functions.decimals().call()
                    amount_wei = int(amount * 10**decimals)

                    tx = contract.functions.transfer(to_address, amount_wei).build_transaction({
                        'from': sender_address,
                        'nonce': nonce,
                        'maxFeePerGas': max_fee_per_gas,
                        'maxPriorityFeePerGas': max_priority_fee,
                        'chainId': CHAIN_ID,
                        'type': 2,
                        'gas': 65000
                    })

                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                fee = w3.from_wei(receipt.gasUsed * receipt.effectiveGasPrice, 'ether')
                total_fee += float(fee)
                success_count += 1

            except Exception as e:
                await update.message.reply_text(f"Tx ke-{i+1} gagal: {e}")
                break

        await update.message.reply_text(
            f"✅ Selesai!\n"
            f"Berhasil: {success_count}/{repeat}x\n"
            f"Total Fee: {total_fee:.13f} ETH"
        )

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
            await update.message.reply_text(f"Saldo ETH: {w3.from_wei(balance, 'ether')}")
        else:
            contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS[token_symbol]), abi=erc20_abi)
            decimals = contract.functions.decimals().call()
            balance = contract.functions.balanceOf(sender_address).call()
            await update.message.reply_text(f"Saldo {token_symbol}: {balance / 10**decimals}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
async def bridge_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Format: /bridge TOKEN 0.01 [jumlah]\nContoh: /bridge USDT 0.01 10")
        return

    token = context.args[0].upper()
    amount = float(context.args[1])
    loop_count = int(context.args[2]) if len(context.args) > 2 else 1

    if token not in TOKENS:
        await update.message.reply_text(f"Token {token} ga ada. Pilih: {', '.join(TOKENS.keys())}")
        return

    if token == "ETH":
        await update.message.reply_text("ETH belum support bridge, pake USDT/USDC/DAI dulu")
        return

    token_address = TOKENS[token]
    contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    decimals = contract.functions.decimals().call()
    amount_wei = int(amount * 10**decimals)

    await update.message.reply_text(f"Proses bridge {token} {amount} ke Sepolia {loop_count}x...\n1x bridge = 1000 poin")

    success_count = 0
    for i in range(loop_count):
        try:
            nonce = w3.eth.get_transaction_count(sender_address)
            tx = contract.functions.transfer(
                "0x0000000000000001", # Dummy bridge address, ganti sesuai protokol lu
                amount_wei
            ).build_transaction({
                'chainId': CHAIN_ID,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            success_count += 1
            await update.message.reply_text(f"Bridge {i+1}/{loop_count} done: {tx_hash.hex()}")

        except Exception as e:
            await update.message.reply_text(f"Bridge {i+1}/{loop_count} gagal: {str(e)}")
            break

    await update.message.reply_text(
        f"✅ Bridge Selesai!\n"
        f"Berhasil: {success_count}/{loop_count}x\n"
        f"Estimasi poin: {success_count * 1000} 🔥"
            )
async def post_init(application):  # <<< HAPUS : Application
    await application.bot.set_my_commands([
        ("start", "Cek wallet & menu"),
        ("send", "Kirim token ke address lain"),
        ("bridge", "Bridge token ke Sepolia - farming poin"),
        ("balance", "Cek saldo token")
    ])

from telegram.ext import ApplicationBuilder
application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("send", send_token))
application.add_handler(CommandHandler("bridge", bridge_token))
application.add_handler(CommandHandler("balance", balance))

if __name__ == '__main__':
    application.run_polling()
