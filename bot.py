import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3
import asyncio

BOT_TOKEN = os.environ['BOT_TOKEN']
PRIVATE_KEY = os.environ['PRIVATE_KEY']
WALLET_ADDRESS = Web3.to_checksum_address(os.environ['WALLET_ADDRESS'])
RPC_URL = os.environ.get('RPC_URL', 'https://rpc.teqoin.io/testnet')

web3 = Web3(Web3.HTTPProvider(RPC_URL))
CHAIN_ID = 22888

# ALAMAT TOKEN TEQOIN TESTNET LU - UDAH GW MASUKIN
CONTRACTS = {
    'usdt': Web3.to_checksum_address('0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9'),
    'usdc': Web3.to_checksum_address('0xe819eb5be34b20f1fec012c0daf960397a0fb386'),
    'dai': Web3.to_checksum_address('0xb96a869c74be2ed561d95a77408505371f287d16')
}

ERC20_ABI = [
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":False,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eth = web3.from_wei(web3.eth.get_balance(WALLET_ADDRESS), 'ether')
    msg = f"Wallet: {WALLET_ADDRESS}\nGas ETH: {eth:.10f}\n\n"
    for name, addr in CONTRACTS.items():
        c = web3.eth.contract(address=addr, abi=ERC20_ABI)
        dec = c.functions.decimals().call()
        bal = c.functions.balanceOf(WALLET_ADDRESS).call() / (10 ** dec)
        msg += f"{name.upper()}: {bal:.4f}\n"
    msg += "\nCommand:\n/k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x123... 5"
    await update.message.reply_text(msg)

async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pk_addr = web3.eth.account.from_key(PRIVATE_KEY).address
        eth = web3.from_wei(web3.eth.get_balance(WALLET_ADDRESS), 'ether')
        status = "✅ Private Key COCOK" if pk_addr.lower() == WALLET_ADDRESS.lower() else "❌ Private Key BEDA"
        msg = f"RPC: {RPC_URL}\nWALLET_ADDRESS ENV:\n{WALLET_ADDRESS}\nAddress dari PRIVATE_KEY:\n{pk_addr}\nSaldo ETH Gas: {eth:.6f}\n{status}"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_k_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 3:
            await update.message.reply_text("Format salah bre.\n/k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x123... 5")
            return

        token = context.args[0].lower()
        if token not in CONTRACTS:
            await update.message.reply_text(f"Token {token} ga ada. Pilih: dai, usdt, usdc")
            return

        to_address = Web3.to_checksum_address(context.args[1])
        jumlah = int(context.args[2])

        contract = web3.eth.contract(address=CONTRACTS[token], abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount = int(0.01 * (10 ** decimals))

        await update.message.reply_text(f"Mulai spam {jumlah}x 0.01 {token.upper()} ke {to_address[:10]}...")

        sukses = 0
        for i in range(jumlah):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'latest')
                gas_price = web3.eth.gas_price # ga pake * 1.5 biar murah

                tx = contract.functions.transfer(to_address, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': nonce,
                    'gas': 65000, # turunin dari 100000 biar ga boros
                    'gasPrice': gas_price,
                    'chainId': CHAIN_ID
                })

                signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                sukses += 1
                await asyncio.sleep(2)

            except Exception as e:
                await update.message.reply_text(f"Gagal TX ke-{i+1}: {str(e)}")
                break

        await update.message.reply_text(f"SELESAI. Berhasil {sukses}/{jumlah}x kirim {token.upper()}")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cek", cek))
    app.add_handler(CommandHandler("k", handle_k_command))
    app.run_polling()

if __name__ == '__main__':
    main()
