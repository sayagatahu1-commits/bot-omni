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
                msg += f'{symbol}: Gagal load\n'

        msg += f'\nSimple mode:\n/k 0xalamat → 0.01 USDT 1x\n/k 0xalamat 5 → 0.01 USDT 5x\n/k eth 0xalamat → 0.0001 ETH 1x'
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def k(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        token = "USDT"
        amount = 0.01
        repeat = 1
        to_addr = None

        if len(args) == 0:
            await update.message.reply_text('Pake: /k 0xalamat')
            return

        first_arg = args[0].upper()

        if len(args) == 1:
            to_addr = Web3.to_checksum_address(args[0])

        elif len(args) == 2:
            if first_arg in TOKEN_LIST or first_arg == "ETH":
                token = first_arg
                to_addr = Web3.to_checksum_address(args[1])
                if token == "ETH": amount = 0.0001
            else:
                to_addr = Web3.to_checksum_address(args[0])
                val = args[1].lower().replace('x', '')
                try:
                    # Kalo bulat = repeat, kalo desimal = amount
                    if val.isdigit() and int(val) >= 1:
                        repeat = int(val)
                    else:
                        amount = float(val)
                except:
                    await update.message.reply_text(f'Angka gak valid: {args[1]}')
                    return

        elif len(args) == 3:
            if first_arg in TOKEN_LIST or first_arg == "ETH":
                token = first_arg
                to_addr = Web3.to_checksum_address(args[1])
                val = args[2].lower().replace('x', '')
                try:
                    if val.isdigit() and int(val) >= 1:
                        repeat = int(val)
                        if token == "ETH": amount = 0.0001
                    else:
                        amount = float(val)
                        if token == "ETH" and amount == 0.01: amount = 0.0001
                except:
                    await update.message.reply_text(f'Angka gak valid: {args[2]}')
                    return
            else:
                to_addr = Web3.to_checksum_address(args[0])
                amount = float(args[1])
                repeat = int(args[2].lower().replace('x', ''))

        elif len(args) == 4:
            token = args[0].upper()
            to_addr = Web3.to_checksum_address(args[1])
            amount = float(args[2])
            repeat = int(args[3].lower().replace('x', ''))
        else:
            await update.message.reply_text(
                'Format:\n'
                '/k 0xalamat → 0.01 USDT 1x\n'
                '/k 0xalamat 5 → 0.01 USDT 5x\n'
                '/k dai 0xalamat 5 → 0.01 DAI 5x\n'
                '/k dai 0xalamat 0.1 → 0.1 DAI 1x\n'
                '/k dai 0xalamat 0.1 5 → 0.1 DAI 5x'
            )
            return

        if repeat > 20:
            await update.message.reply_text('Maks 20x bre 😭')
            return
        if repeat < 1:
            await update.message.reply_text('Minimal 1x bre 😂')
            return

        if token!= "ETH" and token not in TOKEN_LIST:
            await update.message.reply_text(f'Token {token} gak ada di list bre')
            return

        await update.message.reply_text(f'Siap spam {amount} {token} ke {to_addr[:8]}... {repeat}x 🏃💨')

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
                await asyncio.sleep(0.3)
            except Exception as e:
                await update.message.reply_text(f'TX ke-{i+1} gagal: {str(e)[:80]}')
                break

        total = amount * success
        await update.message.reply_text(f'✅ Done {success}x! Total: {total:.4f} {token}')

    except Exception as e:
        await update.message.reply_text(f'Error fatal: {e}')
