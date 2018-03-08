import logging
import sys
import tempfile
from urllib.request import urlopen

logger = logging.getLogger(__name__)


class MediaDownloader:
    def __init__(self, successClbk=None, errorClbk=None, progressCallback=None):
        self.successCallback = successClbk
        self.errorCallback = errorClbk
        self.progressCallback = progressCallback

    def download(self, url, successCallback=None, errorCallback=None, progressCallback=None):
        try:
            u = urlopen(url)
            path = tempfile.mkstemp()[1]
            with open(path, "wb") as f:
                meta = u.info()

                if sys.version_info >= (3, 0):
                    fileSize = int(u.getheader("Content-Length"))
                else:
                    fileSize = int(meta.getheaders("Content-Length")[0])

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
                        self.progressCallback(int(status))
                        lastEmit = status

            if self.successCallback:
                self.successCallback(path)
        except Exception as e:
            logger.exception("Error occured at transfer " + str(e))
            if self.errorCallback:
                self.errorCallback()
