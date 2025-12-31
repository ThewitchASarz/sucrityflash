"""
Cryptographic utilities for RSA signatures and key management.
"""
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
import hashlib
from config import settings


class RSAKeyManager:
    """Manages RSA key pair generation and signature operations."""

    @staticmethod
    def generate_key_pair() -> tuple[str, str]:
        """
        Generate RSA-2048 key pair.

        Returns:
            tuple[str, str]: (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=settings.RSA_PUBLIC_EXPONENT,
            key_size=settings.RSA_KEY_SIZE,
            backend=default_backend()
        )

        # Serialize private key (PEM format)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Serialize public key (PEM format)
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        return private_pem, public_pem

    @staticmethod
    def get_public_key_fingerprint(public_key_pem: str) -> str:
        """
        Generate SHA-256 fingerprint of public key.

        Args:
            public_key_pem: PEM-encoded public key

        Returns:
            str: Hex-encoded SHA-256 fingerprint
        """
        return hashlib.sha256(public_key_pem.encode()).hexdigest()

    @staticmethod
    def sign_data(private_key_pem: str, data: str) -> str:
        """
        Sign data with RSA private key (RSA-SHA256).

        Args:
            private_key_pem: PEM-encoded private key
            data: Data to sign

        Returns:
            str: Hex-encoded signature
        """
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )

        signature = private_key.sign(
            data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return signature.hex()

    @staticmethod
    def verify_signature(public_key_pem: str, data: str, signature_hex: str) -> bool:
        """
        Verify RSA signature (RSA-SHA256).

        Args:
            public_key_pem: PEM-encoded public key
            data: Original data that was signed
            signature_hex: Hex-encoded signature

        Returns:
            bool: True if signature is valid
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )

            signature = bytes.fromhex(signature_hex)

            public_key.verify(
                signature,
                data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return True
        except InvalidSignature:
            return False
        except Exception:
            return False


# Global instance
rsa_manager = RSAKeyManager()
