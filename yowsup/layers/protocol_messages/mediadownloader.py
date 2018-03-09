import binascii
import hashlib
import logging
import os
import tempfile
import threading
from urllib.request import urlopen

from Crypto.Cipher import AES

from axolotl.kdf.hkdfv3 import HKDFv3
from axolotl.util.byteutil import ByteUtil
from yowsup.layers.protocol_messages.protocolentities import DownloadableMessageProtocolEntity

logger = logging.getLogger(__name__)


class MediaDownloader(threading.Thread):

    def __init__(self, me: DownloadableMessageProtocolEntity,
                 successCallback=None, errorCallback=None, progressCallback=None, asynch=False):
        assert me
        self.me = me
        self.successCallback = successCallback
        self.errorCallback = errorCallback
        self.progressCallback = progressCallback
        self.asynch = asynch
        if self.asynch:
            threading.Thread.__init__(self)

    def start(self):

        if self.asynch:
            super(MediaDownloader, self).start()
        else:
            self.run()

    @staticmethod
    def verify_sha256(fname, sha256):
        hash_md5 = hashlib.sha256()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest() == sha256

    def run(self):
        """
        Downloads & Decrypts
        Returns file path of the message attached in the message
        """
        try:
            enc_path = self.download(self.me.url)

            # verify downloaded file sha256
            if not self.verify_sha256(enc_path, binascii.hexlify(self.me.file_enc_sha256).decode()):
                raise Exception("downloaded file checksum is incorrect")

            key = self.me.media_key
            out = os.path.splitext(enc_path)[0] + self.me.get_extension() or ''

            if self.progressCallback:
                self.progressCallback("Decrypting file %s" % enc_path)

            out_file = self.decrypt_file(enc_path, key, self.me.crypt_keys, out)

            # verify downloaded file sha256
            if not self.verify_sha256(out_file, binascii.hexlify(self.me.file_sha256).decode()):
                raise Exception("decypted file checksum is incorrect")

            # Remove enc file
            try:
                os.remove(enc_path)
            except OSError:
                pass

            self.successCallback(out_file)
        except Exception as e:
            if self.errorCallback:
                self.errorCallback(str(e))
            else:
                logger.error(str(e))

    def download(self, url):
        try:
            u = urlopen(url)
            path = tempfile.mkstemp()[1]
            with open(path, "wb") as f:
                fileSize = int(u.getheader("Content-Length"))
                fileSizeDl = 0
                blockSz = 8192
                lastEmit = 0
                while True:
                    buf = u.read(blockSz)

                    if not buf:
                        break

                    fileSizeDl += len(buf)
                    f.write(buf)
                    status = (fileSizeDl * 100 / fileSize)

                    if self.progressCallback and lastEmit != status:
                        self.progressCallback("Downloading %d %% : %s" % (int(status), url))
                        lastEmit = status

            return path

        except Exception as e:
            raise Exception("Error occured at transfer " + str(e))

    @staticmethod
    def decrypt_file(enc_path, media_key, wakey, out_path=""):
        media_key = binascii.hexlify(media_key)
        derivative = HKDFv3().deriveSecrets(binascii.unhexlify(media_key), binascii.unhexlify(wakey), 112)

        splits = ByteUtil.split(derivative, 16, 32)
        iv = splits[0]
        cipher_key = splits[1]
        bs = AES.block_size
        cipher = AES.new(key=cipher_key, mode=AES.MODE_CBC, IV=iv)

        if out_path == "":
            out_path = os.path.splitext(enc_path)[0]

        chunk_size = 4096 * bs
        with open(enc_path, "rb") as in_file:
            with open(out_path, "wb") as out_file:
                while True:
                    chunk = in_file.read(chunk_size)
                    try:
                        piece = cipher.decrypt(chunk)
                    except:
                        # Last chunk most likely to get into here
                        # Because cipher needs a multiple of 16
                        chunk = chunk[:-10]
                        # assert len(chunk) % bs == 0
                        piece = cipher.decrypt(chunk)
                        padding_len = piece[-1]
                        piece = piece[:-padding_len]
                    if len(chunk) == 0:
                        break  # end of file

                    out_file.write(piece)

        return out_path

    @staticmethod
    def _pad(s):
        x = (16 - len(s) % 16) * chr(16 - len(s) % 16)
        return s + x.encode()

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]
