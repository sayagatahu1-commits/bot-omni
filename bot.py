import os
import logging
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application

BOT_TOKEN = os.getenv("BOT_TOKEN")
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = int(os.getenv("CHAIN_ID"))

# TULIS LOWERCASE AJA, BIARIN KODE YG URUS CHECKSUM
BRIDGE_CONTRACT = "0xbc6ad4965241ea4260eb571c936576a4f537d67b"
TOKENS = {
    "USDT": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9",
    "USDC": "0xe819eb5be34b20f1fec012c0daf960397a0fb386",
    "DAI": "0xb96a869c74be2ed561d95a7740850371f287d16",
}

BRIDGE_ABI = [
    {"inputs": [{"internalType": "address", "name": "token", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "bridgeTokens", "outputs": [{"internalType": "bytes32", "name": "withdrawalId", "type": "bytes32"}], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "token", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "quoteBridgeFee", "outputs": [{"internalType": "uint256", "name": "fee", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

TEQOIN_TOKEN_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "send", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0) # WAJIB BUAT TEQOIN
sender_address = w3.eth.account.from_key(PRIVATE_KEY).address
logging.basicConfig(level=logging.INFO)

# FUNGSI SAKTI: AUTO CHECKSUM APAPUN INPUTNYA
def addr(a): return Web3.to_checksum_address(a.strip().lower())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eth_balance = w3.from_wei(w3.eth.get_balance(sender_address), 'ether')
    await update.message.reply_text(
        f"TeQoin Testnet Wallet Bot\n"
        f"Wallet: `{sender_address}`\n"
        f"Saldo TEQ: {eth_balance}\n"
        f"Chain ID: {CHAIN_ID}\n\n"
        f"/send USDT 0x... 0.01\n"
        f"/bridge USDT 0.01 10\n"
        f"/balance USDT",
        parse_mode='Markdown'
    )

async def send_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 3:
            await update.message.reply_text("Format: /send TOKEN 0xAlamat 0.01")
            return

        token = context.args[0].upper()
        to_address = addr(context.args[1])
        amount = float(context.args[2])

        if token not in TOKENS:
            await update.message.reply_text(f"Token {token} ga ada. Pilih: {', '.join(TOKENS.keys())}")
            return

        token_address = addr(TOKENS[token])
        contract = w3.eth.contract(address=token_address, abi=TEQOIN_TOKEN_ABI)
        decimals = contract.functions.decimals().call()
        amount_wei = int(amount * 10**decimals)

        nonce = w3.eth.get_transaction_count(sender_address, 'pending')
        tx = contract.functions.send(to_address, amount_wei).build_transaction({
            'chainId': CHAIN_ID,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        await update.message.reply_text(f"✅ Sent: `{tx_hash.hex()}`", parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Send gagal: {str(e)}")

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Format: /bridge USDT 0.01 [jumlah]")
            return

        token = context.args[0].upper()
        amount = float(context.args[1])
        loop_count = int(context.args[2]) if len(context.args) > 2 else 1

        if token not in TOKENS:
            await update.message.reply_text(f"Token {token} ga ada. Pilih: {', '.join(TOKENS.keys())}")
            return

        token_address = addr(TOKENS[token])
        bridge_address = addr(BRIDGE_CONTRACT)
        token_contract = w3.eth.contract(address=token_address, abi=TEQOIN_TOKEN_ABI)
        bridge_contract = w3.eth.contract(address=bridge_address, abi=BRIDGE_ABI)

        # INI KUNCINYA: AMBIL DECIMALS DARI CONTRACT LANGSUNG
        decimals = token_contract.functions.decimals().call()
        amount_wei = int(amount * 10**decimals)

        await update.message.reply_text(f"Token {token} decimals: {decimals}\nAmount wei: {amount_wei}")

        # CEK SALDO
        balance = token_contract.functions.balanceOf(sender_address).call()
        if balance < amount_wei:
            await update.message.reply_text(f"❌ Saldo kurang. Punya: {balance / 10**decimals} {token}")
            return

        # CEK FEE + SIMULASI DULU BIAR TAU REVERT KENAPA
        try:
            bridge_fee = bridge_contract.functions.quoteBridgeFee(token_address, amount_wei).call()
            await update.message.reply_text(f"Fee bridge: {w3.from_wei(bridge_fee, 'ether')} ETH")
        except Exception as e:
            await update.message.reply_text(f"❌ quoteBridgeFee gagal: {str(e)}")
            return

        # SIMULASI TX SEBELUM KIRIM - BIAR TAU REVERT REASON
        try:
            bridge_contract.functions.bridgeTokens(token_address, amount_wei).call({'from': sender_address, 'value': bridge_fee})
        except Exception as e:
            await update.message.reply_text(f"❌ Simulasi gagal, bakal revert: {str(e)}\nCoba amount lebih gede, misal 0.1")
            return

        await update.message.reply_text(f"Bridge {token} {amount} x{loop_count} ke Sepolia...")

        success_count = 0
        for i in range(loop_count):
            try:
                # APPROVE
                nonce = w3.eth.get_transaction_count(sender_address, 'pending')
                approve_tx = token_contract.functions.approve(bridge_address, amount_wei).build_transaction({
                    'chainId': CHAIN_ID,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                })
                signed_approve = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
                approve_hash = w3.eth.send_raw_transaction(signed_approve.rawTransaction)
                await update.message.reply_text(f"Approve {i+1}/{loop_count}...")
                w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)

                # BRIDGE
                nonce = w3.eth.get_transaction_count(sender_address, 'pending')
                tx = bridge_contract.functions.bridgeTokens(token_address, amount_wei).build_transaction({
                    'chainId': CHAIN_ID,
                    'gas': 300000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                    'value': bridge_fee
                })
                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if receipt.status == 1:
                    success_count += 1
                    await update.message.reply_text(f"✅ Bridge {i+1}/{loop_count} Done\nTxHash: `{tx_hash.hex()}`", parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"❌ Bridge {i+1}/{loop_count} revert di blockchain")

                time.sleep(2)

            except Exception as e:
                await update.message.reply_text(f"❌ Bridge {i+1}/{loop_count} gagal: {str(e)}")

        await update.message.reply_text(f"🏁 Selesai. Berhasil: {success_count}/{loop_count}")

    except Exception as e:
        await update.message.reply_text(f"❌ Bridge error: {str(e)}")
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Format: /balance USDT")
            return
        token = context.args[0].upper()
        if token not in TOKENS:
            await update.message.reply_text(f"Token {token} ga ada")
            return
        token_address = addr(TOKENS[token])
        contract = w3.eth.contract(address=token_address, abi=TEQOIN_TOKEN_ABI)
        decimals = contract.functions.decimals().call()
        bal = contract.functions.balanceOf(sender_address).call()
        await update.message.reply_text(f"Saldo {token}: {bal / 10**decimals}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Cek wallet"),
        ("send", "Kirim token"),
        ("bridge", "Bridge ke Sepolia"),
        ("balance", "Cek saldo")
    ])

application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("send", send_token))
application.add_handler(CommandHandler("bridge", bridge))
application.add_handler(CommandHandler("balance", balance))

if __name__ == "__main__":
    application.run_polling(drop_pending_updates=True)
