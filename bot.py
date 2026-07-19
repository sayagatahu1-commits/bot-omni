import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(PRIVATE_KEY)

TOKEN_LIST = {
    "USDT": {"address": "0xfcc025a3e170df62de0e25af7ceaf1c89abfe6e9", "decimals": 6},
    "DAI": {"address": "0xb96a869c74be2ed561d95a77408505371f287d16", "decimals": 18},
    "USDC": {"address": "0x0000000000000000", "decimals": 6}  # Dummy biar muncul
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        eth_bal = w3.from_wei(w3.eth.get_balance(acct.address), 'ether')
        msg = f'Bot TeQoin TESTNET Aktif!\nWallet: `{acct.address}`\n\n'
        msg += f'ETH: {eth_bal:.4f}\n'
        for symbol, data in TOKEN_LIST.items():
            if data["address"] == "0x0000000000000000000000000000000000000000":
                msg += f'{symbol}: 0.0000\n'  # USDC dummy
                continue
            try:
                contract = w3.eth.contract(address=Web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
                bal = contract.functions.balanceOf(acct.address).call()
                human_bal = bal / 10**data["decimals"]
                msg += f'{symbol}: {human_bal:.4f}\n'
            except:
                msg += f'{symbol}: 0.0000\n'
        msg += f'\n/k 0xalamat 5 → 0.01 USDT 5x\n/k eth 0xalamat → 0.0001 ETH 1x'
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

async def k(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        token = "USDT"
        amount = 0.01
        repeat = 1

        if len(args) == 0:
            await update.message.reply_text('Pake: /k 0xalamat')
            return

        # Default
        to_addr = Web3.to_checksum_address(args[0])

        # /k 0xalamat 5
        if len(args) == 2:
            if args[0].upper() in TOKEN_LIST or args[0].upper() == "ETH":
                token = args[0].upper()
                to_addr = Web3.to_checksum_address(args[1])
                if token == "ETH": amount = 0.0001
            else:
                to_addr = Web3.to_checksum_address(args[0])
                x = args[1].lower().replace('x', '')
                try:
                    if '.' not in x: # angka bulat = repeat
                        repeat = int(x)
                    else: # ada koma = amount
                        amount = float(x)
                except:
                    pass

        # /k dai 0xalamat 5
        elif len(args) == 3:
            if args[0].upper() in TOKEN_LIST or args[0].upper() == "ETH":
                token = args[0].upper()
                to_addr = Web3.to_checksum_address(args[1])
                x = args[2].lower().replace('x', '')
                try:
                    if '.' not in x:
                        repeat = int(x)
                        if token == "ETH": amount = 0.0001
                    else:
                        amount = float(x)
                        if token == "ETH" and amount == 0.01: amount = 0.0001
                except:
                    pass
            else:
                to_addr = Web3.to_checksum_address(args[0])
                amount = float(args[1])
                repeat = int(args[2].lower().replace('x', ''))

        # /k dai 0xalamat 0.1 5
        elif len(args) == 4:
            token = args[0].upper()
            to_addr = Web3.to_checksum_address(args[1])
            amount = float(args[2])
            repeat = int(args[3].lower().replace('x', ''))

        if repeat > 20:
            await update.message.reply_text('Maks 20x bre')
            return
        if token!= "ETH" and token not in TOKEN_LIST:
            await update.message.reply_text(f'Token {token} gak ada')
            return

        await update.message.reply_text(f'Spam {amount} {token} ke {to_addr[:8]}... {repeat}x 🏃💨')

        nonce = w3.eth.get_transaction_count(acct.address)
        chain_id = w3.eth.chain_id
        gas_price = w3.eth.gas_price
        success = 0

        for i in range(repeat):
            try:
                if token == "ETH":
                    tx = {'to': to_addr,'value': w3.to_wei(amount, 'ether'),'gas': 21000,'gasPrice': gas_price,'nonce': nonce + i,'chainId': chain_id}
                else:
                    data = TOKEN_LIST[token]
                    contract = w3.eth.contract(address=Web3.to_checksum_address(data["address"]), abi=ERC20_ABI)
                    amount_wei = int(amount * 10**data["decimals"])
                    tx = contract.functions.transfer(to_addr, amount_wei).build_transaction({'gas': 100000,'gasPrice': gas_price,'nonce': nonce + i,'chainId': chain_id})

                signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                success += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                await update.message.reply_text(f'TX ke-{i+1} gagal: {str(e)[:60]}')
                break

        total = amount * success
        await update.message.reply_text(f'✅ Done {success}x! Total: {total:.4f} {token}')
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("k", k))
    print("Bot jalan...")
    app.run_polling()

if __name__ == '__main__':
    main()
