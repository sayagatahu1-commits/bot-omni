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
        chain_id = web3.eth.chain_id # AMBIL LANGSUNG DARI RPC

        eth_balance = web3.eth.get_balance(WALLET_ADDRESS)
        biaya_aktivasi = 21000 * gas_price + web3.to_wei('0.0001', 'ether')

        if eth_balance < biaya_aktivasi:
            await update.message.reply_text(f"Saldo ETH {web3.from_wei(eth_balance, 'ether'):.12f} kurang. Butuh {web3.from_wei(biaya_aktivasi, 'ether'):.12f} buat aktivasi.")
            return

        await update.message.reply_text(f"Aktivasi wallet: kirim 0.0001 ETH ke diri sendiri...")

        # 1. AKTIVASI
        try:
            nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
            tx_aktivasi = {
                'from': WALLET_ADDRESS,
                'to': WALLET_ADDRESS,
                'value': web3.to_wei('0.0001', 'ether'),
                'nonce': nonce,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': chain_id # PAKE : BUKAN =
            }
            signed_tx = web3.eth.account.sign_transaction(tx_aktivasi, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction) # WEB3 V6 PAKE UNDERSCORE
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            await update.message.reply_text("Wallet aktif. Mulai spam token...")
            await asyncio.sleep(5)
        except Exception as e:
            await update.message.reply_text(f"Gagal aktivasi: {str(e)[:200]}")
            return

        # 2. SPAM TOKEN
        contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACTS[token]), abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount = int(0.01 * (10 ** decimals))

        sukses = 0
        for i in range(jumlah):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
                tx = contract.functions.transfer(to_address, amount).build_transaction({
                    'from': WALLET_ADDRESS,
                    'nonce': nonce,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'chainId': chain_id # PAKE : BUKAN =
                })
                signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction) # WEB3 V6 PAKE UNDERSCORE
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

@bot.message_handler(commands=['testkey'])
async def handle_testkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from eth_account import Account
    try:
        derived_addr = Account.from_key(PRIVATE_KEY).address
        await update.message.reply_text(f"Alamat dari PRIVATE_KEY:\n{derived_addr}\n\nAlamat di WALLET_ADDRESS:\n{WALLET_ADDRESS}")
        if derived_addr.lower() != WALLET_ADDRESS.lower():
            await update.message.reply_text("SALAH TOTAL. Private key lu bukan buat alamat ini. Makanya invalid sender.")
        else:
            await update.message.reply_text("Private key bener. Lanjut cek 2.")
    except Exception as e:
        await update.message.reply_text(f"Private key lu ga valid: {str(e)}")
        to_address = Web3.to_checksum_address(context.args[1])
        jumlah = int(context.args[2])

        gas_limit = 40000
        gas_price = web3.to_wei('0.0001', 'gwei')

        eth_balance = web3.eth.get_balance(WALLET_ADDRESS)
        if eth_balance < gas_limit * gas_price:
            await update.message.reply_text(f"Saldo ETH {web3.from_wei(eth_balance, 'ether'):.12f} kurang buat gas.")
            return

        await update.message.reply_text(f"Aktivasi wallet dulu...")

        # 1. KIRIM 0 ETH KE DIRI SENDIRI BIAR AKTIF
        try:
            nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
            tx = contract.functions.transfer(to_address, amount).build_transaction({
    'from': WALLET_ADDRESS,
    'nonce': nonce,
    'gas': gas_limit,
    'gasPrice': gas_price,
    'chainId': web3.eth.chain_id # Pake : bukan =, key-nya 'chainId'
})
            signed_tx = web3.eth.account.sign_transaction(tx_aktivasi, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction) # pake underscore
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            await update.message.reply_text("Wallet aktif. Mulai spam token...")
            await asyncio.sleep(3)
        except Exception as e:
            await update.message.reply_text(f"Gagal aktivasi: {str(e)[:200]}. Coba kirim 0.001 ETH dari wallet lu ke alamat ini dulu manual.")
            return

        # 2. BARU SPAM TOKEN
        contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACTS[token]), abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount = int(0.01 * (10 ** decimals))

        sukses = 0
        for i in range(jumlah):
            try:
                nonce = web3.eth.get_transaction_count(WALLET_ADDRESS, 'pending')
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
