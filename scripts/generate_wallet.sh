#!/usr/bin/env bash
# Yangi Solana wallet yaratish va private key ni base58 formatda chiqarish
set -e

echo "🔑 Yangi Solana wallet yaratilmoqda..."

# solana-keygen mavjudligini tekshirish
if command -v solana-keygen &>/dev/null; then
    KEYFILE="/tmp/sniper_wallet_$(date +%s).json"
    solana-keygen new --no-bip39-passphrase -o "$KEYFILE" --force

    echo ""
    echo "Wallet yaratildi: $KEYFILE"
    echo ""
    echo "Public key:"
    solana-keygen pubkey "$KEYFILE"
    echo ""
    echo "Private key (JSON array) - .env ga joylashtiring:"
    cat "$KEYFILE"
    echo ""
    echo "⚠️  Bu faylni xavfsiz joyda saqlang!"

    # Xavfsiz o'chirish uchun eslatma
    echo ""
    echo "Faylni o'chirish: rm $KEYFILE"
else
    # Python orqali yaratish (Solana CLI yo'q bo'lsa)
    python3 -c "
import os, json, base64
import struct

# Ed25519 keypair yaratish
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes_raw()
    public_bytes = key.public_key().public_bytes_raw()
    full_key = list(private_bytes) + list(public_bytes)

    print('Private key (JSON array):')
    print(json.dumps(full_key))
    print()

    # Base58 encode
    import subprocess
    result = subprocess.run(['python3', '-c',
        f'import base58; print(base58.b58encode(bytes({full_key})).decode())'],
        capture_output=True, text=True)
    if result.returncode == 0:
        print('Private key (Base58):')
        print(result.stdout.strip())
except ImportError:
    print('Solana CLI yoki cryptography kutubxonasini o\\'rnating:')
    print('  pip install cryptography base58')
    print('  yoki: sh -c \"\$(curl -sSfL https://release.solana.com/stable/install)\"')
"
fi
