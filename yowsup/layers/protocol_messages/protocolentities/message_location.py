from yowsup.layers.protocol_messages.protocolentities import MessageProtocolEntity


class LocationMessageProtocolEntity(MessageProtocolEntity):

    def __init__(self, latitude, longitude, name=None, url=None, encoding=None, _id=None, _from=None, to=None,
                 notify=None, timestamp=None, participant=None,
                 preview=None, offline=None, retry=None, address=None):

        super(LocationMessageProtocolEntity, self).__init__("location", _id, _from, to, notify, timestamp, participant,
                                                            preview, offline, retry)
        self.setLocationMediaProps(latitude, longitude, name, address, url)

    def __str__(self):
        out = super(MessageProtocolEntity, self).__str__()
        out += "Latitude: %s\n" % self.latitude
        out += "Longitude: %s\n" % self.longitude
        out += "Name: %s\n" % self.name
        out += "Address: %s\n" % self.address
        out += "URL: %s\n" % self.url

        return out

    def getLatitude(self):
        return self.latitude

    def getLongitude(self):
        return self.longitude

    def getLocationName(self):
        return self.name

    def getLocationURL(self):
        return self.url

    def getAddress(self):
        return self.address

    def setLocationMediaProps(self, latitude, longitude, locationName=None, address=None, url=None):
        self.latitude = str(latitude)
        self.longitude = str(longitude)
        self.name = str(locationName)
        self.address = str(address)
        self.url = str(url)

    def toProtocolTreeNode(self):
        node = super(LocationMessageProtocolEntity, self).toProtocolTreeNode()

        mediaNode = node.getChild("enc")
        mediaNode.setAttribute("latitude", self.latitude)
        mediaNode.setAttribute("longitude", self.longitude)

        if self.name:
            mediaNode.setAttribute("name", self.name)
        if self.address:
            mediaNode.setAttribute("address", self.address)
        if self.url:
            mediaNode.setAttribute("url", self.url)

        return node

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = MessageProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = LocationMessageProtocolEntity
        mediaNode = node.getChild("media")
        entity.setLocationMediaProps(
            mediaNode.getAttributeValue("latitude"),
            mediaNode.getAttributeValue("longitude"),
            mediaNode.getAttributeValue("name"),
            mediaNode.getAttributeValue("url"),
            mediaNode.getAttributeValue("address")
        )
        return entity
