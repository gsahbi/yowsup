import binascii
import logging

from Crypto.Cipher import AES

from axolotl.kdf.hkdfv3 import HKDFv3
from axolotl.util.byteutil import ByteUtil
from yowsup.common.tools import MimeTools
from yowsup.structs import ProtocolTreeNode
from .message import MessageProtocolEntity

logger = logging.getLogger(__name__)

wa_mimes = {
    'audio/ogg; codecs=opus': '.ogg',
    'image/jpeg': '.jpg',
    'text/plain': '.txt'
}


class DownloadableMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            DownloadableMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            DownloadableMessageProtocolEntity.load_properties(self, **kwargs)

        self.crypt_keys = None

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, v):
        self._url = v

    @property
    def mime_type(self):
        return self._mime_type

    @mime_type.setter
    def mime_type(self, v):
        self._mime_type = v

    @property
    def file_sha256(self):
        return self._file_sha256

    @file_sha256.setter
    def file_sha256(self, v):
        self._file_sha256 = v

    @property
    def file_length(self):
        return self._file_length

    @file_length.setter
    def file_length(self, v):
        self._file_length = int(v) if v else 0

    @property
    def media_key(self):
        return self._media_key

    @media_key.setter
    def media_key(self, v):
        self._media_key = v

    @property
    def file_enc_sha256(self):
        return self._file_enc_sha256

    @file_enc_sha256.setter
    def file_enc_sha256(self, v):
        self._file_enc_sha256 = v

    def __str__(self):
        out = super().__str__()
        out += "MimeType: %s\n" % self.mime_type
        out += "File Hash: %s\n" % self.file_sha256
        out += "URL: %s\n" % self.url
        out += "File Size: %s\n" % self.file_length
        out += "File %s encrypted\n" % ("is" if self.is_encrypted() else "is NOT")
        return out

    def decrypt(self, encdata, refkey):
        derivative = HKDFv3().deriveSecrets(refkey, binascii.unhexlify(self.crypt_keys), 112)
        parts = ByteUtil.split(derivative, 16, 32)
        iv = parts[0]
        cipherKey = parts[1]
        e_data = encdata[:-10]
        AES.key_size = 128
        cr_obj = AES.new(key=cipherKey, mode=AES.MODE_CBC, IV=iv)
        return cr_obj.decrypt(e_data)

    def is_encrypted(self):
        return self.crypt_keys and self.media_key

    def get_extension(self):
        # try well known extensions
        if self.mime_type in wa_mimes:
            return wa_mimes[self.mime_type]

        return MimeTools.getExtension(self.mime_type)

    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        data = {
            'media_key': self.media_key,
            'mime_type': self.mime_type,
            'url': self.url,
            'file_sha256': self.file_sha256,
            'file_length': self.file_length,
            'file_enc_sha256': self.file_enc_sha256
        }

        bodyNode = ProtocolTreeNode("body", {"mediatype": self.media_type}, None, data)
        node.addChild(bodyNode)
        return node

    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        data = body.getData()

        self.media_key = data["media_key"] if "media_key" in data else None
        self.mime_type = data["mime_type"] if "mime_type" in data else None
        self.url = data["url"] if "url" in data else None
        self.file_sha256 = data["file_sha256"] if "file_sha256" in data else None
        self.file_length = data["file_length"] if "file_length" in data else None
        self.file_enc_sha256 = data["file_enc_sha256"] if "file_enc_sha256" in data else None
