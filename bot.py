import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3
from eth_account import Account

TOKEN = os.getenv('TOKEN')
RPC_URL = os.getenv('RPC_URL')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = Web3.to_checksum_address(os.getenv('WALLET_ADDRESS'))

web3 = Web3(Web3.HTTPProvider(RPC_URL))

CONTRACTS = {
    'dai': '0x5fA5A0749C0718B7e9B6eA8B4b5F3F8b6a2b1c2d',
    'usdt': '0x7e3a3a4e4e5a6e7a8e9a0a1a2a3a4a5a6a7a8a9a',
    'usdc': '0x1a2a3a4a5a6a7a8a9a0a1a2a3a4a5a6a7a8a9a0a'
}

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Bot On. Wallet: {WALLET_ADDRESS}")

async def handle_cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eth_bal = web3.from_wei(web3.eth.get_balance(WALLET_ADDRESS), 'ether')
        chain_id = web3.eth.chain_id
        await update.message.reply_text(f"Saldo ETH: {eth_bal:.12f}\nChainID: {chain_id}\nRPC: Connected")
    except Exception as e:
        await update.message.reply_text(f"Error cek: {str(e)}")

async def handle_testkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        derived_addr = Account.from_key(PRIVATE_KEY).address
        await update.message.reply_text(
            f"Alamat dari PRIVATE_KEY:\n`{derived_addr}`\n\nAlamat di WALLET_ADDRESS:\n`{WALLET_ADDRESS}`",
            parse_mode='Markdown'
        )
        if derived_addr.lower() == WALLET_ADDRESS.lower():
            await update.message.reply_text("✅ Private key COCOK sama alamat.")
        else:
            await update.message.reply_text("❌ SALAH. Private key bukan buat alamat ini. Ini penyebab 'invalid sender'.")
    except Exception as e:
        await update.message.reply_text(f"Private key lu ga valid: {str(e)}")

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
        gas_limit = 40000
        gas_price = web3.to_wei('0.0001', 'gwei')
        chain_id = web3.eth.chain_id
        eth_balance = web3.eth.get_balance(WALLET_ADDRESS)
        biaya_aktivasi = 21000 * gas_price + web3.to_wei('0.0001', 'ether')
        if eth_balance < biaya_aktivasi:
            await update.message.reply_text(f"Saldo ETH {web3.from_wei(eth_balance, 'ether'):.12f} kurang. Butuh {web3.from_wei(biaya_aktivasi, 'ether'):.12f}")
            return
        await update.message.reply_text("Aktivasi wallet: kirim 0.0001 ETH ke diri sendiri...")
        try:
            nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
            tx_aktivasi = {
                'from': WALLET_ADDRESS, 'to': WALLET_ADDRESS,
                'value': web3.to_wei('0.0001', 'ether'), 'nonce': nonce,
                'gas': 21000, 'gasPrice': gas_price, 'chainId': chain_id
            }
            signed_tx = web3.eth.account.sign_transaction(tx_aktivasi, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            await update.message.reply_text("Wallet aktif. Mulai spam token...")
            await asyncio.sleep(5)
        except Exception as e:
            await update.message.reply_text(f"Gagal aktivasi: {str(e)[:200]}")
            return
        contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACTS[token]), abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount = int(0.01 * (10 ** decimals))
        sukses = 0
        for i in range(jumlah):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
                tx = contract.functions.transfer(to_address, amount).build_transaction({
                    'from': WALLET_ADDRESS, 'nonce': nonce, 'gas': gas_limit,
                    'gasPrice': gas_price, 'chainId': chain_id
                })
                signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
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

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("cek", handle_cek))
    application.add_handler(CommandHandler("k", handle_k_command))
    application.add_handler(CommandHandler("testkey", handle_testkey))
    application.run_polling()

if __name__ == '__main__':
    main()
