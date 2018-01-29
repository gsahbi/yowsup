import binascii
import mimetypes
import os
from urllib.request import urlopen

from Crypto.Cipher import AES
from axolotl.kdf.hkdfv3 import HKDFv3
from axolotl.util.byteutil import ByteUtil

from yowsup.common.tools import WATools
from .message import MessageProtocolEntity


class DownloadableMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, node=None):
        super(DownloadableMessageProtocolEntity, self).__init__(node)
        self.setDownloadableMediaProps(**node.getChild("body").data)

    def __str__(self):
        out = super(DownloadableMessageProtocolEntity, self).__str__()
        out += "MimeType: %s\n" % self.mimeType
        out += "File Hash: %s\n" % self.fileHash
        out += "URL: %s\n" % self.url
        out += "File Size: %s\n" % self.size
        out += "File name: %s\n" % self.fileName
        out += "File %s encrypted\n" % "is" if self.isEncrypted() else "is NOT"
        return out

    def decrypt(self, encdata, refkey):
        derivative = HKDFv3().deriveSecrets(refkey, binascii.unhexlify(self.cryptKeys), 112)
        parts = ByteUtil.split(derivative, 16, 32)
        iv = parts[0]
        cipherKey = parts[1]
        e_data = encdata[:-10]
        AES.key_size = 128
        cr_obj = AES.new(key=cipherKey, mode=AES.MODE_CBC, IV=iv)
        return cr_obj.decrypt(e_data)

    def isEncrypted(self):
        return self.cryptKeys and self.mediaKey

    def getMediaContent(self):
        data = urlopen(self.url.decode('ASCII')).read()
        if self.isEncrypted():
            data = self.decrypt(data, self.mediaKey)
        return bytearray(data)

    def getMediaSize(self):
        return self.size

    def getMediaUrl(self):
        return self.url

    def getMimeType(self):
        return self.mimeType

    def getExtension(self):
        return mimetypes.guess_extension(self.mimeType)

    def toProtocolTreeNode(self):
        node = super(DownloadableMessageProtocolEntity, self).toProtocolTreeNode()
        mediaNode = node.getChild("enc")
        mediaNode.setAttribute("mimetype", self.mimeType)
        mediaNode.setAttribute("filehash", self.fileHash)
        mediaNode.setAttribute("url", self.url["url"].encode())
        mediaNode.setAttribute("size", str(self.size))
        mediaNode.setAttribute("mediakey", self.url["mediaKey"])
        mediaNode.setAttribute("file_enc_sha256", self.url["file_enc_sha256"])

        return node

    def setDownloadableMediaProps(self, mime_type, file_sha256, file_enc_sha256,
                                  url, file_length, media_key, file_name=None, **kwargs):
        self.mimeType = mime_type
        self.fileHash = file_sha256
        self.url = url
        self.size = int(file_length)
        self.fileEncSHA256 = file_enc_sha256
        self.mediaKey = media_key
        self.cryptKeys = None
        self.fileName = file_name


    @staticmethod
    def fromBuilder(builder):
        url = builder.get("url")
        ip = builder.get("ip")
        assert url, "Url is required"
        mimeType = builder.get("mimetype", mimetypes.guess_type(builder.getOriginalFilepath()))
        filehash = WATools.getFileHashForUpload2(builder.getFilepath())
        size = os.path.getsize(builder.getFilepath())
        fileName = os.path.basename(builder.getFilepath())
        entity = DownloadableMessageProtocolEntity(builder.mediaType, mimeType, filehash, url, ip, size, fileName,
                                                   to=builder.jid, preview=builder.get("preview"))

    @staticmethod
    def fromFilePath(fpath, url, mediaType, ip, to, mimeType=None, preview=None, filehash=None, filesize=None):
        mimeType = mimeType or mimetypes.guess_type(fpath)
        filehash = filehash or WATools.getFileHashForUpload2(fpath)
        size = filesize or os.path.getsize(fpath)
        fileName = os.path.basename(fpath)
        return DownloadableMessageProtocolEntity(mediaType, mimeType, filehash, url, ip, size, fileName, to=to,
                                                 preview=preview)
