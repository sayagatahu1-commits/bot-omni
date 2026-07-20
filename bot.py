import os
import logging
import time
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application

BOT_TOKEN = os.getenv("BOT_TOKEN")
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = int(os.getenv("CHAIN_ID"))

# UDAH GUA ISI DARI SS LU
BRIDGE_CONTRACT = "0xbc6ad4965241ea4260eb571c936576a4f537d67b"
BRIDGE_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_token", "type": "address"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "uint256", "name": "_destChainId", "type": "uint256"}
        ],
        "name": "bridge", # Tebakan nama function, kalo error ganti 'send' atau 'deposit'
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# UDAH GUA ISI DARI SS LU
TOKENS = {
    "USDT": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9",
    "USDC": "0xe819eb5be34b20f1fec012c0daf960397a0fb386",
    "DAI": "0xb96a869c74be2ed561d95a7740850371f287d16",
    "ETH": "0xEeeeeEeeeEeEeeEeEeeEEEeeeeEeeeeeeeEEeE"
}

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
sender_address = w3.eth.account.from_key(PRIVATE_KEY).address
logging.basicConfig(level=logging.INFO)

# ISI DEST CHAIN ID TEQOIN TUJUAN LU DISINI
DST_CHAIN_ID = 1 # GANTI INI! Tanya dev Teqoin, misal chain tujuan ID nya 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eth_balance = w3.from_wei(w3.eth.get_balance(sender_address), 'ether')
    await update.message.reply_text(
        f"Wallet: `{sender_address}`\n"
        f"Saldo Native: {eth_balance}\n"
        f"Chain ID: {CHAIN_ID}\n\n"
        f"/bridge USDT 0.01 10\n"
        f"/balance USDT",
        parse_mode='Markdown'
    )

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Format: /bridge USDT 0.01 [jumlah]")
            return

        token = context.args[0].upper()
        amount = float(context.args[1])
        loop_count = int(context.args[2]) if len(context.args) > 2 else 1

        if token not in TOKENS:
            await update.message.reply_text(f"Token {token} ga ada")
            return

        token_address = TOKENS[token]
        token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        bridge_contract = w3.eth.contract(address=Web3.to_checksum_address(BRIDGE_CONTRACT), abi=BRIDGE_ABI)
        decimals = token_contract.functions.decimals().call()
        amount_wei = int(amount * 10**decimals)

        await update.message.reply_text(f"Bridge {token} {amount} x{loop_count} ke chain {DST_CHAIN_ID}...")

        success_count = 0
        for i in range(loop_count):
            try:
                # 1. Approve
                nonce = w3.eth.get_transaction_count(sender_address, 'pending')
                approve_tx = token_contract.functions.approve(
                    BRIDGE_CONTRACT,
                    amount_wei
                ).build_transaction({
                    'chainId': CHAIN_ID,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                })
                signed_approve = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
                w3.eth.send_raw_transaction(signed_approve.rawTransaction)
                await update.message.reply_text(f"Approve {i+1}/{loop_count}...")
                time.sleep(8)

                # 2. Bridge
                nonce = w3.eth.get_transaction_count(sender_address, 'pending')
                tx = bridge_contract.functions.bridge( # KALO ERROR GANTI 'send' / 'deposit'
                    Web3.to_checksum_address(token_address), # _token
                    amount_wei, # _amount
                    DST_CHAIN_ID # _destChainId
                ).build_transaction({
                    'chainId': CHAIN_ID,
                    'gas': 300000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                })
                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                success_count += 1
                await update.message.reply_text(f"✅ Bridge {i+1}/{loop_count}: {tx_hash.hex()}")
                time.sleep(3)

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
        token_address = TOKENS.get(token)
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        bal = contract.functions.balanceOf(sender_address).call()
        await update.message.reply_text(f"Saldo {token}: {bal / 10**decimals}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Cek wallet"),
        ("bridge", "Bridge ke Teqoin lain"),
        ("balance", "Cek saldo")
    ])

application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("bridge", bridge))
application.add_handler(CommandHandler("balance", balance))

if __name__ == "__main__":
    application.run_polling()
