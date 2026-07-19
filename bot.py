import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

RPC_URL = "https://rpc.teqoin.io"
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

# Contract token TeQoin Testnet
TOKEN_LIST = {
    "USDT": {"address": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9", "decimals": 6},
    "USDC": {"address": "0xe819eb5be34b20f1fec012c0daf960397a0fb386", "decimals": 6},
    "DAI": {"address": "0xb96a869c74be2ed561d95a77408505371f287d16", "decimals": 18}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eth_bal = w3.from_wei(w3.eth.get_balance(acct.address), 'ether')
        msg = f'Bot TeQoin TESTNET Aktif!\n\nWallet: `{acct.address}`\n\n'
        msg += f'ETH: {eth_bal:.4f}\n'

        for symbol, data in TOKEN_LIST.items():
            contract = w3.eth.contract(address=Web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
            bal = contract.functions.balanceOf(acct.address).call()
            human_bal = bal / 10**data["decimals"] # INI KUNCINYA
            msg += f'{symbol}: {human_bal:.4f}\n'

        msg += '\nPake: /send ETH 0xalamat 0.01\nPake: /send DAI 0xalamat 25'
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args)!= 3:
            await update.message.reply_text('Pake: /send ETH 0xalamat 0.01\nAtau: /send DAI 0xalamat 25')
            return

        token = args[0].upper()
        to_addr = Web3.to_checksum_address(args[1])
        amount = float(args[2])

        nonce = w3.eth.get_transaction_count(acct.address)

        if token == "ETH":
            tx = {
                'to': to_addr,
                'value': w3.to_wei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
                'chainId': 4242424
            }
        elif token in TOKEN_LIST:
    data = TOKEN_LIST[token] # <-- PAKE 4 SPASI ATAU 1 TAB
    contract = w3.eth.contract(address=Web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
    amount_wei = int(amount * 10**data["decimals"])
    tx = contract.functions.transfer(to_addr, amount_wei).build_transaction({
        'from': acct.address,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
        'chainId': 4242424
    })
        else:
            await update.message.reply_text('Token cuma: ETH, DAI, USDT, USDC')
            return

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        await update.message.reply_text(
            f'✅ Dikirim {amount} {token} ke {to_addr}\n'
            f'TX: https://explorer.teqoin.io/tx/{tx_hash.hex()}'
        )
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", send))
    app.run_polling()

if __name__ == '__main__':
    main()
