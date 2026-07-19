import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

RPC_URL = "https://rpc.teqoin.io"
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

TOKEN_LIST = {
    "USDT": {"address": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9", "decimals": 6},
    "USDC": {"address": "0x8e19eb5be34b20f1fec012c0daf960397af0fb36", "decimals": 6},
    "DAI": {"address": "0xb96a869c74be2ed561d95a77408505371f287d16", "decimals": 18}
}

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eth_bal = w3.from_wei(w3.eth.get_balance(acct.address), 'ether')
        msg = f'Bot TeQoin TESTNET Aktif!\nWallet: `{acct.address}`\n\n'
        msg += f'ETH: {eth_bal:.4f}\n'

        for symbol, data in TOKEN_LIST.items():
            try:
                contract = w3.eth.contract(address=Web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
                bal = contract.functions.balanceOf(acct.address).call()
                human_bal = bal / 10**data["decimals"]
                msg += f'{symbol}: {human_bal:.4f}\n'
            except:
                msg += f'{symbol}: Gagal load\n' # Kalo error, skip aja

        msg += f'\nSimple mode:\n/k 0xalamat → 0.01 USDT 1x\n/k 0xalamat 5 → 0.01 USDT 5x\n/k eth 0xalamat → 0.0001 ETH 1x'
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def k(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        token = "USDT"
        amount = 0.01 # DEFAULT PALING MURAH
        repeat = 1
        to_addr = None

        # /k 0xalamat → 0.01 USDT 1x
        if len(args) == 1:
            to_addr = Web3.to_checksum_address(args[0])

        # /k 0xalamat 5 → 0.01 USDT 5x
        # /k 0xalamat 0.1 → 0.1 USDT 1x
        elif len(args) == 2:
            to_addr = Web3.to_checksum_address(args[0])
            if float(args[1]) >= 1 and float(args[1]).is_integer():
                repeat = int(args[1])
            else:
                amount = float(args[1])

        # /k 0xalamat 0.1 5 → 0.1 USDT 5x
        # /k ETH 0xalamat → 0.0001 ETH 1x
        elif len(args) == 3:
            if args[0].upper() in TOKEN_LIST or args[0].upper() == "ETH":
                token = args[0].upper()
                to_addr = Web3.to_checksum_address(args[1])
                amount = float(args[2])
                if token == "ETH": amount = 0.0001
            else:
                to_addr = Web3.to_checksum_address(args[0])
                amount = float(args[1])
                repeat = int(args[2])

        # /k ETH 0xalamat 0.0001 10 → 0.0001 ETH 10x
        elif len(args) == 4:
            token = args[0].upper()
            to_addr = Web3.to_checksum_address(args[1])
            amount = float(args[2])
            repeat = int(args[3])
        else:
            await update.message.reply_text(
                'Simple mode:\n'
                '/k 0xalamat → 0.01 USDT 1x\n'
                '/k 0xalamat 5 → 0.01 USDT 5x\n'
                '/k 0xalamat 0.1 10 → 0.1 USDT 10x\n'
                '/k eth 0xalamat → 0.0001 ETH 1x'
            )
            return

        if token == "ETH" and amount == 0.01: amount = 0.0001
        if repeat > 20:
            await update.message.reply_text('Maks 20x bre 😭')
            return
        if repeat < 1:
            await update.message.reply_text('Minimal 1x bre 😂')
            return

        msg = await update.message.reply_text(f'Spam {amount} {token} ke {to_addr[:8]}... {repeat}x 🏃💨')
        nonce = w3.eth.get_transaction_count(acct.address)
        chain_id = w3.eth.chain_id
        gas_price = w3.eth.gas_price

        success = 0
        for i in range(repeat):
            try:
                if token == "ETH":
                    tx = {
                        'to': to_addr,
                        'value': w3.to_wei(amount, 'ether'),
                        'gas': 21000,
                        'gasPrice': gas_price,
                        'nonce': nonce + i,
                        'chainId': chain_id
                    }
                else:
                    data = TOKEN_LIST[token]
                    contract = w3.eth.contract(address=Web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
                    amount_wei = int(amount * 10**data["decimals"])
                    tx = contract.functions.transfer(to_addr, amount_wei).build_transaction({
                        'gas': 100000,
                        'gasPrice': gas_price,
                        'nonce': nonce + i,
                        'chainId': chain_id
                    })

                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                success += 1
                if (i + 1) % 5 == 0 or i == repeat - 1:
                    await msg.edit_text(f'Progress: {i+1}/{repeat} ✅')
                await asyncio.sleep(0.3)
            except Exception as e:
                await update.message.reply_text(f'TX ke-{i+1} gagal: {str(e)[:80]}')
                break

        total = amount * success
        await update.message.reply_text(f'✅ Done {success}x! Total: {total:.4f} {token}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("k", k))
    app.run_polling()

if __name__ == '__main__':
    main()
