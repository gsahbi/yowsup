# -*- coding utf-8 -*-

import yowsup.layers


class YowNetworkLayerInterface(yowsup.layers.YowLayerInterface):
    def connect(self):
        self._layer.createConnection()

    def disconnect(self):
        self._layer.destroyConnection()

    def getStatus(self):
        return self._layer.getStatus()
