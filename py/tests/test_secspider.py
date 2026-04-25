import base64
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa

from base.secspider import build_secspider_package
from secspider_tool import main as secspider_main


class TestSecSpiderBuilder(unittest.TestCase):
    def test_build_package_emits_required_headers_and_payload(self):
        private_key = ECC.generate(curve="Ed25519")
        package_text = build_secspider_package(
            source_text="class Spider:\n    pass\n",
            name="[直] omofun",
            version="1",
            remark="",
            kid="kid-1",
            signing_private_key=private_key,
            master_secret=b"0123456789abcdef0123456789abcdef",
        )

        self.assertIn("//@name:[直] omofun", package_text)
        self.assertIn("//@version:1", package_text)
        self.assertIn("//@remark:", package_text)
        self.assertIn("//@format:secspider/1", package_text)
        self.assertIn("//@alg:aes-256-gcm", package_text)
        self.assertIn("//@wrap:hkdf-aes-keywrap", package_text)
        self.assertIn("//@sign:ed25519", package_text)
        self.assertIn("//@kid:kid-1", package_text)
        self.assertIn("//@nonce:base64:", package_text)
        self.assertIn("//@ek:base64:", package_text)
        self.assertIn("//@hash:sha256:", package_text)
        self.assertIn("//@sig:base64:", package_text)
        self.assertIn("payload.base64:", package_text)

    def test_build_package_signature_verifies_over_headers_and_payload(self):
        private_key = ECC.generate(curve="Ed25519")
        package_text = build_secspider_package(
            source_text="class Spider:\n    pass\n",
            name="fixture",
            version="3",
            remark="demo",
            kid="kid-sign",
            signing_private_key=private_key,
            master_secret=b"0123456789abcdef0123456789abcdef",
        )

        headers = {}
        payload_b64 = ""
        for line in package_text.splitlines():
            if line.startswith("//@"):
                key, _, value = line[3:].partition(":")
                headers[key] = value
            elif line.startswith("payload.base64:"):
                payload_b64 = line.removeprefix("payload.base64:")

        signing_bytes = "\n".join(
            [
                f"//@name:{headers['name']}",
                f"//@version:{headers['version']}",
                f"//@remark:{headers['remark']}",
                f"//@format:{headers['format']}",
                f"//@alg:{headers['alg']}",
                f"//@wrap:{headers['wrap']}",
                f"//@sign:{headers['sign']}",
                f"//@kid:{headers['kid']}",
                f"//@nonce:{headers['nonce']}",
                f"//@ek:{headers['ek']}",
                f"//@hash:{headers['hash']}",
                f"payload.base64:{payload_b64}",
            ]
        ).encode("utf-8")
        signature = base64.b64decode(headers["sig"].removeprefix("base64:"))

        verifier = eddsa.new(private_key.public_key(), "rfc8032")
        verifier.verify(signing_bytes, signature)

    def test_build_package_encrypts_source_and_wraps_content_key(self):
        private_key = ECC.generate(curve="Ed25519")
        master_secret = b"0123456789abcdef0123456789abcdef"
        source_text = "class Spider:\n    value = 'plain'\n"
        package_text = build_secspider_package(
            source_text=source_text,
            name="fixture",
            version="5",
            remark="",
            kid="kid-wrap",
            signing_private_key=private_key,
            master_secret=master_secret,
        )

        self.assertNotIn(source_text, package_text)
        headers = {}
        payload_b64 = ""
        for line in package_text.splitlines():
            if line.startswith("//@"):
                key, _, value = line[3:].partition(":")
                headers[key] = value
            elif line.startswith("payload.base64:"):
                payload_b64 = line.removeprefix("payload.base64:")

        wrap_key = HKDF(
            master=master_secret,
            key_len=32,
            salt=headers["kid"].encode("utf-8"),
            hashmod=SHA256,
            num_keys=1,
            context=f"secspider:{headers['name']}:{headers['version']}:wrap-key".encode("utf-8"),
        )
        wrap_nonce = HKDF(
            master=master_secret,
            key_len=12,
            salt=headers["kid"].encode("utf-8"),
            hashmod=SHA256,
            num_keys=1,
            context=f"secspider:{headers['name']}:{headers['version']}:wrap-nonce".encode("utf-8"),
        )
        wrap_blob = base64.b64decode(headers["ek"].removeprefix("base64:"))
        wrap_cipher = AES.new(wrap_key, AES.MODE_GCM, nonce=wrap_nonce)
        content_key = wrap_cipher.decrypt_and_verify(wrap_blob[:-16], wrap_blob[-16:])

        payload_blob = base64.b64decode(payload_b64)
        payload_nonce = base64.b64decode(headers["nonce"].removeprefix("base64:"))
        payload_cipher = AES.new(content_key, AES.MODE_GCM, nonce=payload_nonce)
        decrypted = payload_cipher.decrypt_and_verify(payload_blob[:-16], payload_blob[-16:]).decode("utf-8")

        self.assertEqual(decrypted, source_text)


class TestSecSpiderCli(unittest.TestCase):
    def test_genkeys_writes_private_and_public_key_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            private_path = temp_path / "signing-private.pem"
            public_path = temp_path / "signing-public.pem"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = secspider_main(
                    [
                        "genkeys",
                        "--private-key",
                        str(private_path),
                        "--public-key",
                        str(public_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(private_path.is_file())
            self.assertTrue(public_path.is_file())
            self.assertIn("wrote", stdout.getvalue())

    def test_pack_builds_secspider_file_from_source_and_key_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            private_path = temp_path / "signing-private.pem"
            public_path = temp_path / "signing-public.pem"
            secret_path = temp_path / "master-secret.txt"
            source_path = temp_path / "fixture.py"
            output_path = temp_path / "fixture.sec.py"

            secspider_main(
                [
                    "genkeys",
                    "--private-key",
                    str(private_path),
                    "--public-key",
                    str(public_path),
                ]
            )
            secret_path.write_text("0123456789abcdef0123456789abcdef", encoding="utf-8")
            source_path.write_text("class Spider:\n    pass\n", encoding="utf-8")

            exit_code = secspider_main(
                [
                    "pack",
                    "--input",
                    str(source_path),
                    "--output",
                    str(output_path),
                    "--name",
                    "fixture",
                    "--version",
                    "9",
                    "--remark",
                    "",
                    "--kid",
                    "kid-cli",
                    "--private-key",
                    str(private_path),
                    "--master-secret-file",
                    str(secret_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            package_text = output_path.read_text(encoding="utf-8")
            self.assertIn("//@name:fixture", package_text)
            self.assertIn("//@version:9", package_text)
            self.assertIn("//@kid:kid-cli", package_text)
            self.assertIn("payload.base64:", package_text)

    def test_pack_uses_default_name_version_and_secret_file_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "红果短剧.py"
            output_path = temp_path / "红果短剧.sec.py"
            private_path = temp_path / "signing-private.pem"
            public_path = temp_path / "signing-public.pem"
            secret_path = temp_path / "master-secret.txt"

            secspider_main(
                [
                    "genkeys",
                    "--private-key",
                    str(private_path),
                    "--public-key",
                    str(public_path),
                ]
            )
            secret_path.write_text("0123456789abcdef0123456789abcdef", encoding="utf-8")
            source_path.write_text("class Spider:\n    pass\n", encoding="utf-8")

            with contextlib.chdir(temp_path):
                exit_code = secspider_main(
                    [
                        "pack",
                        "--input",
                        str(source_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            package_text = output_path.read_text(encoding="utf-8")
            self.assertIn("//@name:红果短剧", package_text)
            self.assertIn("//@version:1", package_text)
            self.assertIn("//@remark:", package_text)
            self.assertIn("//@kid:k2026_04", package_text)

    def test_pack_uses_default_output_name_txt_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "默认命名.py"
            private_path = temp_path / "signing-private.pem"
            public_path = temp_path / "signing-public.pem"
            secret_path = temp_path / "master-secret.txt"

            secspider_main(
                [
                    "genkeys",
                    "--private-key",
                    str(private_path),
                    "--public-key",
                    str(public_path),
                ]
            )
            secret_path.write_text("0123456789abcdef0123456789abcdef", encoding="utf-8")
            source_path.write_text("class Spider:\n    pass\n", encoding="utf-8")

            with contextlib.chdir(temp_path):
                exit_code = secspider_main(
                    [
                        "pack",
                        "--input",
                        str(source_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            output_path = temp_path / "默认命名.txt"
            self.assertTrue(output_path.is_file())
            package_text = output_path.read_text(encoding="utf-8")
            self.assertIn("//@name:默认命名", package_text)


if __name__ == "__main__":
    unittest.main()
