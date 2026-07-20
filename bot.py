import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from web3 import Web3
from eth_account import Account

# --- KONFIGURASI ---
TOKEN = os.getenv("TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")

# Alamat Token
TOKEN_CONTRACTS = {
    "usdt": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    "eth": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
    "btc": "0x152b9d0FdC40C096757F570A51E494bd4b943E50"
}

# ABI standar buat token
ERC20_ABI = [
    {"constant": True,"inputs": [{"name": "_owner","type": "address"}],"name": "balanceOf","outputs": [{"name": "balance","type": "uint256"}],"type": "function"},
    {"constant": True,"inputs": [],"name": "decimals","outputs": [{"name": "","type": "uint8"}],"type": "function"},
    {"constant": False,"inputs": [{"name": "_to","type": "address"},{"name": "_value","type": "uint256"}],"name": "transfer","outputs": [{"name": "","type": "bool"}],"type": "function"}
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- INISIALISASI ---
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    print("FATAL: Gagal konek ke RPC_URL")
    exit()

account = Account.from_key(PRIVATE_KEY)
SENDER_ADDRESS = account.address

# --- FUNGSI BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Bot Omni Kirim Token\n"
        f"Wallet: `{SENDER_ADDRESS}`\n\n"
        f"Perintah:\n"
        f"/cek - Cek saldo semua token\n"
        f"/testkey - Test private key\n"
        f"/k usdt 0xAlamat 1.5 - Kirim 1.5 USDT"
    )

async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Cek saldo...")
    try:
        native_balance = web3.from_wei(web3.eth.get_balance(SENDER_ADDRESS), 'ether')
        report = f"Saldo `{SENDER_ADDRESS}`\n\nARBI: {native_balance:.6f} ETH\n\n"
        for symbol, address in TOKEN_CONTRACTS.items():
            token_contract = web3.eth.contract(address=web3.to_checksum_address(address), abi=ERC20_ABI)
            balance = token_contract.functions.balanceOf(SENDER_ADDRESS).call()
            decimals = token_contract.functions.decimals().call()
            report += f"{symbol.upper()}: {balance / (10**decimals):.4f}\n"
        await msg.edit_text(report)
    except Exception as e:
        await msg.edit_text(f"Error cek saldo: {e}")

async def testkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if account.address.lower() == SENDER_ADDRESS.lower():
            await update.message.reply_text(f"PRIVATE_KEY COCOK\nAlamat: `{SENDER_ADDRESS}`")
        else:
            await update.message.reply_text(f"PRIVATE_KEY SALAH\nHasil: `{account.address}`\nHarusnya: `{SENDER_ADDRESS}`")
    except Exception as e:
        await update.message.reply_text(f"Error testkey: {e}")

async def kirim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args)!= 3:
            await update.message.reply_text("Format: /k usdt 0xAlamat 1.5")
            return

        token_symbol, to_address, amount_str = args[0].lower(), args[1], args[2]
        to_address = web3.to_checksum_address(to_address)
        amount = float(amount_str)

        if token_symbol not in TOKEN_CONTRACTS:
            await update.message.reply_text(f"Token salah. Pilihan: {', '.join(TOKEN_CONTRACTS.keys())}")
            return

        msg = await update.message.reply_text(f"Siap kirim {amount} {token_symbol.upper()}...")

        token_address = web3.to_checksum_address(TOKEN_CONTRACTS[token_symbol])
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        decimals = token_contract.functions.decimals().call()
        amount_wei = int(amount * (10**decimals))

        # 1. Aktivasi wallet kalo saldo 0
        if web3.eth.get_balance(SENDER_ADDRESS) == 0:
            await msg.edit_text("Wallet belum aktif. Aktivasi dulu...")
            activation_tx = {
                'from': SENDER_ADDRESS,
                'to': SENDER_ADDRESS,
                'value': 0,
                'nonce': web3.eth.get_transaction_count(SENDER_ADDRESS),
                'gas': 21000,
                'gasPrice': web3.eth.gas_price,
                'chainId': web3.eth.chain_id
            }
            signed_activation = account.sign_transaction(activation_tx)
            tx_hash = web3.eth.send_raw_transaction(signed_activation.rawTransaction) # v6 pake T besar
            await msg.edit_text(f"Aktivasi terkirim: `{tx_hash.hex()}`\nNunggu konfirmasi...")
            web3.eth.wait_for_transaction_receipt(tx_hash)

        # 2. Kirim token
        await msg.edit_text("Bikin transaksi token...")
        nonce = web3.eth.get_transaction_count(SENDER_ADDRESS)
        tx = token_contract.functions.transfer(to_address, amount_wei).build_transaction({
            'from': SENDER_ADDRESS,
            'nonce': nonce,
            'gasPrice': web3.eth.gas_price,
            'chainId': web3.eth.chain_id
        })

        gas_estimate = web3.eth.estimate_gas(tx)
        tx['gas'] = int(gas_estimate * 1.2) # Kasih buffer 20%

        signed_tx = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction) # v6 pake T besar
        await msg.edit_text(f"Sukses! Tx Hash:\n`{tx_hash.hex()}`\n\nCek di Arbiscan.")

    except Exception as e:
        await update.message.reply_text(f"GAGAL KIRIM: {e}")

# --- JALANKAN BOT ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cek", cek))
    app.add_handler(CommandHandler("testkey", testkey))
    app.add_handler(CommandHandler("k", kirim))

    print("Bot jalan...")
    # Ini penting biar nendang bot lain + buang update numpuk
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
