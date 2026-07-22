import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from web3 import Web3
from eth_account import Account
from config import (
    TEQOIN_RPC_URL,
    TEQOIN_CHAIN_ID,
    TEQOIN_CURRENCY_SYMBOL,
    TEQOIN_BLOCK_EXPLORER,
    DEFAULT_GAS_LIMIT,
    DEFAULT_GAS_PRICE_GWEI,
    MAX_BATCH_SIZE,
    DELAY_BETWEEN_TX,
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(TEQOIN_RPC_URL))
account = Account.from_key(PRIVATE_KEY)
WALLET_ADDRESS = account.address

# Conversation states
AWAITING_BATCH_INPUT = 1
AWAITING_SINGLE_SEND = 2


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_balance(address: str) -> float:
    """Cek saldo ETH di TeQoin L2"""
    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
    return float(Web3.from_wei(balance_wei, 'ether'))


def get_nonce() -> int:
    """Ambil nonce terbaru"""
    return w3.eth.get_transaction_count(WALLET_ADDRESS)


def send_eth(to_address: str, amount_eth: float, nonce: int = None) -> dict:
    """Kirim ETH ke satu alamat"""
    to_address = Web3.to_checksum_address(to_address)
    
    if nonce is None:
        nonce = get_nonce()
    
    tx = {
        'chainId': TEQOIN_CHAIN_ID,
        'to': to_address,
        'value': Web3.to_wei(amount_eth, 'ether'),
        'gas': DEFAULT_GAS_LIMIT,
        'gasPrice': Web3.to_wei(DEFAULT_GAS_PRICE_GWEI, 'gwei'),
        'nonce': nonce,
    }
    
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    # Tunggu konfirmasi
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    return {
        'tx_hash': tx_hash.hex(),
        'status': receipt['status'],
        'to': to_address,
        'amount': amount_eth,
        'gas_used': receipt['gasUsed'],
    }


def parse_batch_input(text: str) -> list:
    """
    Parse input batch. Format yang didukung:
    
    Format 1 (per baris): 
        0xAddress1 0.1
        0xAddress2 0.2
    
    Format 2 (comma-separated):
        0xAddress1,0.1;0xAddress2,0.2
    
    Format 3 (same amount):
        0xAddress1
        0xAddress2
        amount:0.5
    """
    entries = []
    lines = text.strip().split('\n')
    default_amount = None
    
    # Cek apakah ada default amount
    for line in lines:
        line = line.strip()
        if line.lower().startswith('amount:'):
            default_amount = float(line.split(':')[1].strip())
    
    for line in lines:
        line = line.strip()
        if not line or line.lower().startswith('amount:'):
            continue
        
        # Coba format dengan semicolon
        if ';' in line:
            pairs = line.split(';')
            for pair in pairs:
                pair = pair.strip()
                if ',' in pair:
                    addr, amt = pair.split(',', 1)
                    entries.append({
                        'address': addr.strip(),
                        'amount': float(amt.strip())
                    })
        elif ',' in line and '0x' in line:
            addr, amt = line.split(',', 1)
            entries.append({
                'address': addr.strip(),
                'amount': float(amt.strip())
            })
        elif ' ' in line:
            parts = line.split()
            if len(parts) >= 2:
                entries.append({
                    'address': parts[0].strip(),
                    'amount': float(parts[1].strip())
                })
            elif len(parts) == 1 and Web3.is_address(parts[0].strip()):
                if default_amount:
                    entries.append({
                        'address': parts[0].strip(),
                        'amount': default_amount
                    })
        elif Web3.is_address(line):
            if default_amount:
                entries.append({
                    'address': line,
                    'amount': default_amount
                })
    
    return entries


def validate_address(address: str) -> bool:
    """Validasi alamat Ethereum"""
    try:
        return Web3.is_address(address)
    except Exception:
        return False


# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /start - Tampilkan info bot"""
    keyboard = [
        [InlineKeyboardButton("💰 Cek Saldo", callback_data="balance")],
        [InlineKeyboardButton("📤 Kirim Single", callback_data="single_send")],
        [InlineKeyboardButton("📦 Batch Send", callback_data="batch_send")],
        [InlineKeyboardButton("📊 Status Network", callback_data="network")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        f"🤖 *TeQoin Testnet Auto-Sender Bot*\n\n"
        f"👋 Halo! Bot ini bisa mengirim ETH testnet "
        f"ke banyak alamat sekaligus di TeQoin L2.\n\n"
        f"📌 *Wallet Address:*\n`{WALLET_ADDRESS}`\n\n"
        f"⛓️ *Network:* TeQoin L2 (Chain ID: {TEQOIN_CHAIN_ID})\n"
        f"🔗 *Explorer:* {TEQOIN_BLOCK_EXPLORER}\n\n"
        f"📋 *Commands:*\n"
        f"/saldo - Cek saldo wallet\n"
        f"/kirim `<addr> <jumlah>` - Kirim ke 1 alamat\n"
        f"/batch - Kirim ke banyak alamat\n"
        f"/network - Cek status network\n"
        f"/help - Bantuan lengkap\n\n"
        f"⚡ Klik tombol di bawah atau ketik command!"
    )
    
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)


async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /saldo - Cek saldo wallet"""
    try:
        bal = get_balance(WALLET_ADDRESS)
        msg = (
            f"💰 *Saldo Wallet*\n\n"
            f"📍 `{WALLET_ADDRESS}`\n\n"
            f"💎 *{bal:.6f} {TEQOIN_CURRENCY_SYMBOL}*\n\n"
            f"🔗 [Lihat di Explorer]({TEQOIN_BLOCK_EXPLORER}/address/{WALLET_ADDRESS})\n"
            f"🚰 [Minta dari Faucet](https://teqoin.io/faucet)"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def send_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /kirim - Kirim ETH ke satu alamat"""
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "📝 *Format:*\n`/kirim <alamat> <jumlah>`\n\n"
            "*Contoh:*\n`/kirim 0x1234...abcd 0.5`",
            parse_mode="Markdown"
        )
        return
    
    to_address = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("❌ Jumlah tidak valid! Gunakan angka (contoh: 0.5)")
        return
    
    if not validate_address(to_address):
        await update.message.reply_text("❌ Alamat wallet tidak valid!")
        return
    
    if amount <= 0:
        await update.message.reply_text("❌ Jumlah harus lebih dari 0!")
        return
    
    # Cek saldo
    bal = get_balance(WALLET_ADDRESS)
    if bal < amount:
        await update.message.reply_text(
            f"❌ Saldo tidak cukup!\n"
            f"Saldo: {bal:.6f} ETH\n"
            f"Dibutuhkan: {amount} ETH"
        )
        return
    
    status_msg = await update.message.reply_text(
        f"⏳ Mengirim {amount} ETH ke `{to_address}`...",
        parse_mode="Markdown"
    )
    
    try:
        result = send_eth(to_address, amount)
        
        if result['status'] == 1:
            msg = (
                f"✅ *Transaksi Berhasil!*\n\n"
                f"📤 Ke: `{result['to']}`\n"
                f"💰 Jumlah: {result['amount']} ETH\n"
                f"⛽ Gas Used: {result['gas_used']}\n"
                f"🔗 [Tx Hash]({TEQOIN_BLOCK_EXPLORER}/tx/0x{result['tx_hash']})"
            )
        else:
            msg = f"❌ Transaksi gagal!\nHash: `0x{result['tx_hash']}`"
        
        await status_msg.edit_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def batch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /batch - Mulai batch send"""
    msg = (
        f"📦 *Batch Send - TeQoin Testnet*\n\n"
        f"Kirimkan daftar alamat tujuan dengan format:\n\n"
        f"*Format 1 (per baris):*\n"
        f"`0xAddr1 0.1`\n"
        f"`0xAddr2 0.2`\n"
        f"`0xAddr3 0.1`\n\n"
        f"*Format 2 (comma-separated):*\n"
        f"`0xAddr1,0.1;0xAddr2,0.2`\n\n"
        f"*Format 3 (same amount):*\n"
        f"`0xAddr1`\n"
        f"`0xAddr2`\n"
        f"`0xAddr3`\n"
        f"`amount:0.5`\n\n"
        f"⚠️ Maksimal {MAX_BATCH_SIZE} alamat per batch\n"
        f"💰 Saldo wallet: {get_balance(WALLET_ADDRESS):.6f} ETH\n\n"
        f"📝 Kirim daftar alamat sekarang (atau /batal untuk membatalkan):"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return AWAITING_BATCH_INPUT


async def batch_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses input batch send"""
    text = update.message.text.strip()
    
    if text.lower() == '/batal':
        await update.message.reply_text("❌ Batch send dibatalkan.")
        return ConversationHandler.END
    
    # Parse input
    entries = parse_batch_input(text)
    
    if not entries:
        await update.message.reply_text(
            "❌ Format tidak dikenali! Coba lagi dengan format yang benar.\n"
            "Ketik /batal untuk membatalkan."
        )
        return AWAITING_BATCH_INPUT
    
    if len(entries) > MAX_BATCH_SIZE:
        await update.message.reply_text(
            f"❌ Terlalu banyak alamat! Maks {MAX_BATCH_SIZE}, "
            f"Anda mengirim {len(entries)}."
        )
        return AWAITING_BATCH_INPUT
    
    # Validasi semua alamat
    invalid = []
    for entry in entries:
        if not validate_address(entry['address']):
            invalid.append(entry['address'])
    
    if invalid:
        await update.message.reply_text(
            f"❌ Alamat tidak valid:\n" + 
            "\n".join(f"- `{a}`" for a in invalid[:10]),
            parse_mode="Markdown"
        )
        return AWAITING_BATCH_INPUT
    
    # Hitung total yang dibutuhkan
    total_amount = sum(e['amount'] for e in entries)
    bal = get_balance(WALLET_ADDRESS)
    
    if bal < total_amount:
        await update.message.reply_text(
            f"❌ Saldo tidak cukup!\n"
            f"Saldo: {bal:.6f} ETH\n"
            f"Total dibutuhkan: {total_amount:.6f} ETH\n"
            f"Kekurangan: {total_amount - bal:.6f} ETH"
        )
        return ConversationHandler.END
    
    # Konfirmasi
    summary = f"📦 *Batch Summary:*\n"
    summary += f"📍 Jumlah alamat: {len(entries)}\n"
    summary += f"💰 Total: {total_amount:.6f} ETH\n"
    summary += f"💳 Saldo: {bal:.6f} ETH\n\n"
    summary += "📋 *Detail:*\n"
    for i, e in enumerate(entries[:10], 1):
        summary += f"{i}. `{e['address'][:10]}...` → {e['amount']} ETH\n"
    if len(entries) > 10:
        summary += f"... dan {len(entries) - 10} alamat lainnya\n"
    
    status_msg = await update.message.reply_text(
        summary + f"\n⏳ *Memulai batch send...*",
        parse_mode="Markdown"
    )
    
    # Eksekusi batch send
    results = []
    nonce = get_nonce()
    success_count = 0
    fail_count = 0
    
    for i, entry in enumerate(entries):
        try:
            result = send_eth(entry['address'], entry['amount'], nonce=nonce + i)
            
            if result['status'] == 1:
                success_count += 1
                results.append(f"✅ `{entry['address'][:12]}...` → {entry['amount']} ETH")
            else:
                fail_count += 1
                results.append(f"❌ `{entry['address'][:12]}...` → FAILED")
        except Exception as e:
            fail_count += 1
            results.append(f"❌ `{entry['address'][:12]}...` → Error: {str(e)[:30]}")
        
        # Update progress setiap 5 transaksi
        if (i + 1) % 5 == 0 or i == len(entries) - 1:
            progress = int((i + 1) / len(entries) * 100)
            await status_msg.edit_text(
                f"⏳ *Progress: {progress}%* ({i+1}/{len(entries)})\n\n"
                + "\n".join(results[-5:]),
                parse_mode="Markdown"
            )
        
        # Delay antar transaksi
        if i < len(entries) - 1:
            await asyncio.sleep(DELAY_BETWEEN_TX)
    
    # Hasil final
    final_msg = (
        f"🏁 *Batch Send Selesai!*\n\n"
        f"✅ Berhasil: {success_count}\n"
        f"❌ Gagal: {fail_count}\n"
        f"📊 Total: {len(entries)} transaksi\n"
        f"💰 Total terkirim: {total_amount:.6f} ETH\n\n"
        f"🔗 [Lihat di Explorer]({TEQOIN_BLOCK_EXPLORER}/address/{WALLET_ADDRESS})"
    )
    
    await status_msg.edit_text(final_msg, parse_mode="Markdown")
    
    # Kirim detail terpisah jika banyak
    if len(results) > 10:
        detail = "📋 *Detail Transaksi:*\n" + "\n".join(results)
        # Telegram limit: 4096 chars
        for i in range(0, len(detail), 4000):
            chunk = detail[i:i+4000]
            await update.message.reply_text(chunk, parse_mode="Markdown")
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batalkan operasi"""
    await update.message.reply_text("❌ Operasi dibatalkan.")
    return ConversationHandler.END


async def network_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /network - Cek status network"""
    try:
        block_number = w3.eth.block_number
        connected = w3.is_connected()
        chain_id = w3.eth.chain_id
        
        msg = (
            f"📊 *Status Network TeQoin L2*\n\n"
            f"🟢 Connected: {'Ya' if connected else 'Tidak'}\n"
            f"🔗 RPC: `{TEQOIN_RPC_URL}`\n"
            f"⛓️ Chain ID: {chain_id}\n"
            f"🧱 Block: {block_number:,}\n"
            f"💰 Currency: {TEQOIN_CURRENCY_SYMBOL}\n\n"
            f"🔗 [Block Explorer]({TEQOIN_BLOCK_EXPLORER})\n"
            f"🚰 [Faucet](https://teqoin.io/faucet)"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /help - Bantuan"""
    msg = (
        f"📖 *Bantuan TeQoin Bot*\n\n"
        f"*Commands:*\n"
        f"/start - Menu utama\n"
        f"/saldo - Cek saldo wallet\n"
        f"/kirim `<addr> <jml>` - Kirim ke 1 alamat\n"
        f"/batch - Batch send (banyak alamat)\n"
        f"/network - Status network\n"
        f"/help - Bantuan ini\n\n"
        f"*Contoh /kirim:*\n"
        f"`/kirim 0xABC...123 0.5`\n\n"
        f"*Contoh /batch:*\n"
        f"Ketik /batch, lalu kirimkan daftar alamat\n\n"
        f"🚰 *Butuh testnet ETH?*\n"
        f"Kunjungi: https://teqoin.io/faucet\n\n"
        f"⚠️ *Disclaimer:*\n"
        f"Bot ini hanya untuk TESTNET.\n"
        f"Jangan gunakan untuk mainnet!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def check_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /cek - Cek status transaksi berdasarkan hash"""
    if not context.args:
        await update.message.reply_text(
            "📝 Format: `/cek <tx_hash>`\n"
            "Contoh: `/cek 0xabc123...`",
            parse_mode="Markdown"
        )
        return
    
    tx_hash = context.args[0]
    if not tx_hash.startswith('0x'):
        tx_hash = '0x' + tx_hash
    
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            status_emoji = "✅"
            status_text = "Berhasil"
        else:
            status_emoji = "❌"
            status_text = "Gagal"
        
        msg = (
            f"{status_emoji} *Transaksi {status_text}*\n\n"
            f"🔗 Hash: `{tx_hash}`\n"
            f"🧱 Block: {receipt['blockNumber']:,}\n"
            f"⛽ Gas Used: {receipt['gasUsed']}\n"
            f"📍 From: `{receipt['from']}`\n"
            f"📍 To: `{receipt.get('to', 'Contract Creation')}`\n\n"
            f"🔗 [Explorer]({TEQOIN_BLOCK_EXPLORER}/tx/{tx_hash})"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Transaksi tidak ditemukan atau error: {str(e)}")


# ============================================================
# MAIN - Run Bot
# ============================================================

def main():
    """Jalankan bot"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN tidak ditemukan di .env!")
        return
    if not PRIVATE_KEY:
        print("❌ WALLET_PRIVATE_KEY tidak ditemukan di .env!")
        return
    
    print(f"🤖 Bot dimulai...")
    print(f"📍 Wallet: {WALLET_ADDRESS}")
    print(f"⛓️ Network: TeQoin L2 (Chain {TEQOIN_CHAIN_ID})")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler untuk batch send
    batch_conv = ConversationHandler(
        entry_points=[CommandHandler("batch", batch_start)],
        states={
            AWAITING_BATCH_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, batch_process),
            ],
        },
        fallbacks=[CommandHandler("batal", cancel)],
    )
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("saldo", balance_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("kirim", send_single))
    app.add_handler(CommandHandler("send", send_single))
    app.add_handler(CommandHandler("cek", check_tx))
    app.add_handler(CommandHandler("network", network_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(batch_conv)
    
    # Start polling
    print("✅ Bot berjalan! Tekan Ctrl+C untuk berhenti.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
