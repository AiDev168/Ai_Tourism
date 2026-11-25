"""Create the demo-only self-signed localhost TLS certificate once."""
from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


root = Path(os.environ["RAHGARD_DEMO_TLS_DIR"])
root.mkdir(parents=True, exist_ok=True)
key_path = root / "localhost.key"
cert_path = root / "localhost.crt"
if key_path.exists() or cert_path.exists():
    if key_path.is_file() and cert_path.is_file() and not key_path.is_symlink() and not cert_path.is_symlink():
        print("PRESENT")
        raise SystemExit(0)
    raise SystemExit("BLOCKED: partial or unsafe localhost certificate state")
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
cert = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(name)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=5))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=90))
    .add_extension(x509.SubjectAlternativeName([
        x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]), critical=False)
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .sign(key, hashes.SHA256())
)
key_path.write_bytes(key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
))
cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
print("CREATED")
