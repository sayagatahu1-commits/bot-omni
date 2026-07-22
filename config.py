# config.py - Konfigurasi TeQoin L2 Testnet

TEQOIN_RPC_URL = "https://rpc.teqoin.io"
TEQOIN_CHAIN_ID = 420377
TEQOIN_CURRENCY_SYMBOL = "ETH"
TEQOIN_BLOCK_EXPLORER = "https://testnet-blockscan.teqoin.io"

# Gas settings (TeQoin L2 = zero/low fee)
DEFAULT_GAS_LIMIT = 21000
DEFAULT_GAS_PRICE_GWEI = 1  # Sangat rendah karena L2

# Batch settings
MAX_BATCH_SIZE = 50  # Maksimal alamat per batch
DELAY_BETWEEN_TX = 2  # Delay antar transaksi (detik)
