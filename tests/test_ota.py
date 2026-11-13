import hashlib
import hmac
import io
import json
import unittest
from unittest.mock import MagicMock, patch

from app import ota


class OtaClientTests(unittest.TestCase):
    ip = "192.0.2.12"
    key = "A" * 43
    nonce = "01" * 16

    def response(self, status, payload):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = json.dumps(payload).encode()
        return response

    @patch("app.ota.HTTPConnection")
    def test_upload_authenticates_the_exact_firmware_body(self, http):
        firmware = b"test firmware"
        connection = http.return_value
        connection.getresponse.side_effect = [
            self.response(200, {"nonce": self.nonce}),
            self.response(200, {"result": "rebooting"}),
        ]

        ota.upload(self.ip, firmware, self.key)

        http.assert_called_once_with(self.ip, 8081, timeout=10)
        challenge, post = connection.request.call_args_list
        self.assertEqual(challenge.args, ("GET", "/api/v1/ota/challenge"))
        self.assertEqual(post.args, ("POST", "/api/v1/ota"))
        self.assertEqual(post.kwargs["body"], firmware)
        digest = hashlib.sha256(firmware).hexdigest()
        message = b"mcz-ota-v1:" + self.nonce.encode() + b":" + digest.encode()
        expected_mac = hmac.new(self.key.encode(), message, "sha256").hexdigest()
        self.assertEqual(post.kwargs["headers"], {
            "Content-Type": "application/octet-stream",
            "X-MCZ-Nonce": self.nonce,
            "X-MCZ-SHA256": digest,
            "X-MCZ-MAC": expected_mac,
        })
        connection.close.assert_called_once()

    @patch("app.ota.HTTPConnection")
    def test_invalid_challenge_prevents_upload(self, http):
        connection = http.return_value
        connection.getresponse.return_value = self.response(200, {"nonce": "invalid"})
        with self.assertRaisesRegex(ValueError, "demande OTA valide"):
            ota.upload(self.ip, b"firmware", self.key)
        connection.request.assert_called_once_with("GET", "/api/v1/ota/challenge")
        connection.close.assert_called_once()

    @patch("app.ota.HTTPConnection")
    def test_disconnect_after_post_is_not_retried(self, http):
        connection = http.return_value
        connection.getresponse.side_effect = [
            self.response(200, {"nonce": self.nonce}),
            ConnectionResetError(),
        ]
        with self.assertRaisesRegex(ValueError, "Téléversement non confirmé"):
            ota.upload(self.ip, b"firmware", self.key)
        self.assertEqual(connection.request.call_count, 2)
        connection.close.assert_called_once()

    def test_firmware_rejects_non_app_images_and_oversized_images(self):
        valid_image = b"\xe9" + bytes(31) + b"\x32\x54\xcd\xab"
        path = MagicMock()
        path.open.return_value = io.BytesIO(valid_image)
        self.assertEqual(ota.read_firmware(path), valid_image)
        path.open.return_value = io.BytesIO(b"\xe9" + bytes(35))
        with self.assertRaisesRegex(ValueError, "firmware.bin"):
            ota.read_firmware(path)
        path.open.return_value = io.BytesIO(valid_image.ljust(ota.MAX_FIRMWARE_BYTES + 1, b"\0"))
        with self.assertRaisesRegex(ValueError, "dépasse la taille"):
            ota.read_firmware(path)
