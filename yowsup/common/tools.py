import base64
import calendar
import codecs
import datetime
import hashlib
import logging
import math
import os
import os.path
import re
import sys
import tempfile
import time
import urllib.request

from PIL import Image
from dateutil import tz
from preview_generator.manager import PreviewManager

from .constants import YowConstants
from .optionalmodules import PILOptionalModule, FFVideoOptionalModule

logger = logging.getLogger(__name__)


class Jid:
    @staticmethod
    def normalize(number):
        if '@' in number:
            return number
        elif "-" in number:
            return "%s@%s" % (number, YowConstants.WHATSAPP_GROUP_SERVER)
        return "%s@%s" % (number, YowConstants.WHATSAPP_SERVER)

    @staticmethod
    def denormalize(number):
        if '@' in number:
            return number.split("@", 1)[0]
        return number

class HexTools:
    decode_hex = codecs.getdecoder("hex_codec")

    @staticmethod
    def decodeHex(hexString):
        result = HexTools.decode_hex(hexString)[0]
        if sys.version_info >= (3, 0):
            result = result.decode('latin-1')
        return result


class WATools:
    @staticmethod
    def generateIdentity():
        return os.urandom(20)

    @staticmethod
    def getFileHashForUpload(filePath):
        sha1 = hashlib.sha256()
        f = open(filePath, 'rb')
        try:
            sha1.update(f.read())
        finally:
            f.close()
        b64Hash = base64.b64encode(sha1.digest())
        return b64Hash if type(b64Hash) is str else b64Hash.decode()

    @staticmethod
    def getFileHashForUpload2(filePath):
        sha1 = hashlib.sha256()
        f = open(filePath, 'rb')
        try:
            hash = hashlib.sha256(f.read()).hexdigest()
        finally:
            f.close()
        return hash


class StorageTools:
    @staticmethod
    def constructPath(*path):
        path = os.path.join(*path)
        fullPath = os.path.expanduser(os.path.join(YowConstants.PATH_STORAGE, path))
        if not os.path.exists(os.path.dirname(fullPath)):
            os.makedirs(os.path.dirname(fullPath))
        return fullPath

    @staticmethod
    def getStorageForPhone(phone):
        return StorageTools.constructPath(phone + '/')

    @staticmethod
    def writeIdentity(phone, identity):
        path = StorageTools.getStorageForPhone(phone)
        with open(os.path.join(path, "id"), 'wb') as idFile:
            idFile.write(identity)

    @staticmethod
    def getIdentity(phone):
        path = StorageTools.getStorageForPhone(phone)
        out = None
        idPath = os.path.join(path, "id")
        if os.path.isfile(idPath):
            with open(idPath, 'rb') as idFile:
                out = idFile.read()
        return out

    @staticmethod
    def writeNonce(phone, nonce):
        path = StorageTools.getStorageForPhone(phone)
        with open(os.path.join(path, "nonce"), 'wb') as idFile:
            idFile.write(nonce.encode("latin-1") if sys.version_info >= (3, 0) else nonce)

    @staticmethod
    def getNonce(phone):
        path = StorageTools.getStorageForPhone(phone)
        out = None
        noncePath = os.path.join(path, "nonce")
        if os.path.isfile(noncePath):
            with open(noncePath, 'rb') as idFile:
                out = idFile.read()
        return out


class TimeTools:
    @staticmethod
    def parseIso(iso):
        d = datetime.datetime(*map(int, re.split('[^\d]', iso)[:-1]))
        return d

    @staticmethod
    def utcToLocal(dt):
        utc = tz.gettz('UTC')
        local = tz.tzlocal()
        dtUtc = dt.replace(tzinfo=utc)

        return dtUtc.astimezone(local)

    @staticmethod
    def utcTimestamp():
        utcNow = datetime.datetime.utcnow()
        return calendar.timegm(utcNow.timetuple())

    @staticmethod
    def datetimeToTimestamp(dt):
        return time.mktime(dt.timetuple())


class ImageTools:
    @staticmethod
    def scaleImage(infile, outfile, imageFormat, width, height):
        with PILOptionalModule() as imp:
            Image = imp("Image")
            im = Image.open(infile)
            # Convert P mode images
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((width, height))
            im.save(outfile, imageFormat)
            return True
        return False

    @staticmethod
    def getImageDimensions(imageFile):
        with PILOptionalModule() as imp:
            Image = imp("Image")
            im = Image.open(imageFile)
            return im.size

    @staticmethod
    def generatePreviewFromImage(image):
        fd, path = tempfile.mkstemp()

        preview = None
        if ImageTools.scaleImage(image, path, "JPEG", YowConstants.PREVIEW_WIDTH, YowConstants.PREVIEW_HEIGHT):
            fileObj = os.fdopen(fd, "rb+")
            fileObj.seek(0)
            preview = fileObj.read()
            fileObj.close()
        os.remove(path)
        return preview


class AudioTools:
    @staticmethod
    def getAudioProperties(audioFile):
        if ".ogg" in audioFile or ".mp3" in audioFile:
            import audioread
            with audioread.audio_open(audioFile) as f:
                return f.duration
        raise Exception("Unsupported/extension file type for: " + audioFile);


class DocumentTools:
    @staticmethod
    def getDocumentProperties(documentFile):
        if '.pdf' in documentFile:
            from PyPDF2 import PdfFileReader
            pdf = PdfFileReader(open(documentFile, 'rb'))
            return pdf.getNumPages()
        return 0

    @staticmethod
    def generatePreviewFromDocument(documentFile):
        preview = None

        manager = PreviewManager('/tmp/cache/', create_folder=True)
        path = manager.get_jpeg_preview(documentFile, height=YowConstants.PREVIEW_DOCUMENT_HEIGHT,
                                        width=YowConstants.PREVIEW_DOCUMENT_WIDTH)
        image = open(path, "rb+")
        preview = image.read()
        image.close()
        os.remove(path)
        return preview


class MapTools:
    def generatePreviewFromLatLong(self, latitute, longitude):
        preview = None
        try:
            # Get the high resolution image
            self.getXY(latitute, longitude, YowConstants.MAP_ZOOM)
            preview = self.generateImage()
        except IOError:
            logger.warning("Could not generate the image - try adjusting the zoom level and checking your coordinates")
        else:
            # Save the image to disk
            # img.save("high_resolution_image.png")
            logger.warning("The map has successfully been created")

        return preview

    def getXY(self, latitude, longitude, zoom):
        """
        Generates an X,Y tile coordinate based on the latitude, longitude
        and zoom level
        Returns:    An X,Y tile coordinate
        """

        tile_size = 256

        # Use a left shift to get the power of 2
        # i.e. a zoom level of 2 will have 2^2 = 4 tiles
        numTiles = 1 << zoom

        # Find the x_point given the longitude
        point_x = (tile_size / 2 + longitude * tile_size / 360.0) * numTiles // tile_size

        # Convert the latitude to radians and take the sine
        sin_y = math.sin(latitude * (math.pi / 180.0))

        # Calulate the y coorindate
        point_y = ((tile_size / 2) + 0.5 * math.log((1 + sin_y) / (1 - sin_y)) * -(
                tile_size / (2 * math.pi))) * numTiles // tile_size

        return int(point_x), int(point_y)

    def generateImage(self, **kwargs):
        """
        Generates an image by stitching a number of google map tiles together.

        Args:
            start_x:        The top-left x-tile coordinate
            start_y:        The top-left y-tile coordinate
            tile_width:     The number of tiles wide the image should be -
                            defaults to 5
            tile_height:    The number of tiles high the image should be -
                            defaults to 5
        Returns:
            A high-resolution Goole Map image.
        """

        start_x = kwargs.get('start_x', None)
        start_y = kwargs.get('start_y', None)
        tile_width = kwargs.get('tile_width', 5)
        tile_height = kwargs.get('tile_height', 5)

        # Check that we have x and y tile coordinates
        if start_x == None or start_y == None:
            start_x, start_y = self.getXY()

        # Determine the size of the image
        width, height = 256 * tile_width, 256 * tile_height

        # Create a new image of the size require
        map_img = Image.new('RGB', (width, height))

        for x in range(0, tile_width):
            for y in range(0, tile_height):
                url = 'https://mt0.google.com/vt?x=' + str(start_x + x) + '&y=' + str(start_y + y) + '&z=' + str(
                    self._zoom)

            current_tile = str(x) + '-' + str(y)
            urllib.request.urlretrieve(url, current_tile)

            im = Image.open(current_tile)
            map_img.paste(im, (x * 256, y * 256))

            os.remove(current_tile)

        return map_img


class VideoTools:
    @staticmethod
    def getVideoProperties(videoFile):
        if sys.version_info <= (3, 0):
            with FFVideoOptionalModule() as imp:
                VideoStream = imp("VideoStream")
                s = VideoStream(videoFile)
                return s.width, s.height, s.bitrate, s.duration  # , s.codec_name
        else:
            import av
            container = av.open(videoFile)
            for i, frame in enumerate(container.decode(video=0)):
                break
            return frame.width, frame.height, container.bit_rate, container.duration / av.time_base

    @staticmethod
    def generatePreviewFromVideo(videoFile):
        if sys.version_info <= (3, 0):
            with FFVideoOptionalModule() as imp:
                VideoStream = imp("VideoStream")
                fd, path = tempfile.mkstemp('.jpg')
                stream = VideoStream(videoFile)
                stream.get_frame_at_sec(0).image().save(path)
                preview = ImageTools.generatePreviewFromImage(path)
                os.remove(path)
                return preview
        else:
            # install av lib using pip3 install av
            import av
            container = av.open(videoFile)
            for i, frame in enumerate(container.decode(video=0)):
                fd, path = tempfile.mkstemp('.jpg')
                frame.to_image().save(path)
                preview = ImageTools.generatePreviewFromImage(path)
                os.remove(path)
                return preview
