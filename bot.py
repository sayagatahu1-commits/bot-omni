import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

BOT_TOKEN = os.environ['BOT_TOKEN']
PRIVATE_KEY = os.environ['PRIVATE_KEY'].strip()
WALLET_ADDRESS = Web3.to_checksum_address(os.environ['WALLET_ADDRESS'])
RPC_URL = os.environ.get('RPC_URL', 'https://testnet.teqoin.com/rpc')

web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 60}))
CHAIN_ID = 22888

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
    try:
        eth = web3.from_wei(web3.eth.get_balance(WALLET_ADDRESS), 'ether')
        msg = f"Wallet: {WALLET_ADDRESS}\nGas ETH: {eth:.10f}\nRPC: OK\n\n"
    except Exception as e:
        msg = f"Wallet: {WALLET_ADDRESS}\nRPC ERROR: {str(e)[:100]}\n\n"

    for name, addr in CONTRACTS.items():
        try:
            c = web3.eth.contract(address=addr, abi=ERC20_ABI)
            dec = c.functions.decimals().call()
            bal = c.functions.balanceOf(WALLET_ADDRESS).call() / (10 ** dec)
            msg += f"{name.upper()}: {bal:.4f}\n"
        except:
            msg += f"{name.upper()}: RPC Error\n"

    msg += "\nCommand:\n/k TOKEN ALAMAT JUMLAH\nContoh: /k usdt 0x123... 5"
    await update.message.reply_text(msg)

async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        pk_addr = web3.eth.account.from_key(PRIVATE_KEY).address
        eth = web3.from_wei(web3.eth.get_balance(WALLET_ADDRESS), 'ether')
        block = web3.eth.block_number
        base_fee = web3.eth.get_block('latest')['baseFeePerGas']
        status = "✅ Private Key COCOK" if pk_addr.lower() == WALLET_ADDRESS.lower() else "❌ Private Key BEDA"
        msg = f"RPC: {RPC_URL}\nChainID: {CHAIN_ID}\nBlock: {block}\nBaseFee: {web3.from_wei(base_fee, 'gwei'):.1f} gwei\n"
        msg += f"WALLET_ADDRESS ENV:\n{WALLET_ADDRESS}\nAddress dari PRIVATE_KEY:\n{pk_addr}\nSaldo ETH Gas: {eth:.6f}\n{status}"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"RPC MATI: {str(e)}")

async def handle_k_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not web3.is_connected():
            await update.message.reply_text("RPC MATI")
            return

        if len(context.args) < 3:
            await update.message.reply_text("Format: /k TOKEN ALAMAT JUMLAH")
            return

        token = context.args[0].lower()
        if token not in CONTRACTS:
            await update.message.reply_text(f"Token {token} ga ada. Pilih: dai, usdt, usdc")
            return

        to_address = Web3.to_checksum_address(context.args[1])
        jumlah = int(context.args[2])

        contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACTS[token]), abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount = int(0.01 * (10 ** decimals))

        # GAS SUPER MURAH KAYA DI WALLET LU
        gas_limit = 40000
        gas_price = web3.to_wei('0.0001', 'gwei') # 0.0001 GWEI = MIRIP FEE DI SS LU
        biaya_1_tx = gas_limit * gas_price

        eth_balance = web3.eth.get_balance(WALLET_ADDRESS)
        if eth_balance < biaya_1_tx:
            await update.message.reply_text(f"GAGAL. Saldo ETH {web3.from_wei(eth_balance, 'ether'):.12f} masih kurang buat 1 tx. Butuh {web3.from_wei(biaya_1_tx, 'ether'):.12f} ETH.")
            return

        await update.message.reply_text(f"Mulai spam {jumlah}x 0.01 {token.upper()} ke {to_address[:10]}...\nGas: {web3.from_wei(gas_price, 'gwei')} gwei")

        sukses = 0
        for i in range(jumlah):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')

                # PAKE LEGACY TX + GAS MURAH
                tx = contract.functions.transfer(to_address, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': nonce,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'chainId': CHAIN_ID
                })
                signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                sukses += 1
                await update.message.reply_text(f"TX {i+1}/{jumlah} sukses: {tx_hash.hex()[:10]}...")
                await asyncio.sleep(5)
            except Exception as e:
                await update.message.reply_text(f"Gagal TX ke-{i+1}: {str(e)[:200]}")
                break

        await update.message.reply_text(f"SELESAI. Berhasil {sukses}/{jumlah}x kirim {token.upper()}")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# INI YG BENER BUAT HAPUS WEBHOOK + CONFLICT
async def post_init(application: Application):
    await application.bot.delete_webhook(drop_pending_updates=True)

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cek", cek))
    app.add_handler(CommandHandler("k", handle_k_command))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
