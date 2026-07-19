from web3 import Web3

# GANTI INI PAKE RPC + WALLET LU
RPC_URL = "https://testnet-rpc.teqoin.io"  # RPC TeQoin lu
WALLET = "0xe2619b6a0f2a84c6e4c9c3d8f5e1a2b3c4d5e6f7"  # Ganti address wallet lu

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Cari semua token yg pernah masuk wallet
latest = w3.eth.block_number
logs = w3.eth.get_logs({
    'fromBlock': latest - 20000,  # scan 20rb block terakhir
    'toBlock': 'latest',
    'topics': [
        w3.keccak(text="Transfer(address,address,uint256)").hex(),
        None,
        '0x000000000000000000000000' + WALLET[2:].lower()
    ]
})

contracts = set()
for log in logs:
    contracts.add(log['address'])
    
print("=== CONTRACT TOKEN KETEMU ===")
for i, c in enumerate(contracts, 1):
    print(f"{i}. {c}")
print("=============================")
