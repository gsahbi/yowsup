from yowsup.structs import ProtocolTreeNode

from yowsup.layers.protocol_messages.protocolentities import MessageProtocolEntity


class LocationMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, ptn=None, **kwargs):
        super().__init__(ptn, **kwargs)
        if ptn:
            LocationMessageProtocolEntity.fromProtocolTreeNode(self, ptn)
        else:
            LocationMessageProtocolEntity.load_properties(self, **kwargs)

    def __str__(self):
        out = super().__str__()
        out += "Latitude: %s\n" % self.latitude
        out += "Longitude: %s\n" % self.longitude
        out += "Name: %s\n" % self.name
        out += "Address: %s\n" % self.address
        out += "URL: %s\n" % self.url

        return out

    @property
    def latitude(self): return self._latitude

    @latitude.setter
    def latitude(self, v):
        self._latitude = v


    @property
    def longitude(self): return self._longitude

    @longitude.setter
    def longitude(self, v):
        self._longitude = v


    @property
    def name(self): return self._name

    @name.setter
    def name(self, v):
        self._name = v


    @property
    def address(self): return self._address

    @address.setter
    def address(self, v):
        self._address = v


    @property
    def url(self): return self._url

    @url.setter
    def url(self, v):
        self._url = v


    @property
    def jpeg_thumbnail(self): return self._jpeg_thumbnail

    @jpeg_thumbnail.setter
    def jpeg_thumbnail(self, v):
        self._jpeg_thumbnail = v


    def toProtocolTreeNode(self):
        node = super().toProtocolTreeNode()
        data = {
            "degrees_latitude": self.latitude,
            "degrees_longitude": self.longitude,
        }

        if self.name:
            data["name"] = self.name
        if self.address:
            data["address"] = self.address
        if self.url:
            data["url"] = self.url

        attribs = {
            "mediatype": self.media_type,
            "type": "location"
        }

        bodyNode = ProtocolTreeNode("body", attribs, None, data)
        node.addChild(bodyNode)
        return node


    def fromProtocolTreeNode(self, node):
        body = node.getChild("body")
        data = body.getData()

        self.latitude = data["degrees_latitude"] if "degrees_latitude" in data else None
        self.longitude = data["degrees_longitude"] if "degrees_longitude" in data else None
        self.name = data["name"] if "name" in data else None
        self.address = data["address"] if "address" in data else None
        self.url = data["url"] if "url" in data else None
        self.jpeg_thumbnail = data["jpeg_thumbnail"] if "jpeg_thumbnail" in data else None
