# -*- coding utf-8 -*-

import time

from .protocoltreenode import ProtocolTreeNode


class ProtocolEntity(object):
    __ID_GEN = 0

    def __init__(self, tag):
        self.tag = tag

    def getTag(self):
        return self.tag

    def isType(self, typ):
        return self.tag == typ

    def _createProtocolTreeNode(self, attributes, children=None, data=None):
        return ProtocolTreeNode(self.getTag(), attributes, children, data)

    @staticmethod
    def _getCurrentTimestamp():
        return int(time.time())

    @staticmethod
    def _generateId(short=False):
        ProtocolEntity.__ID_GEN += 1
        return str(ProtocolEntity.__ID_GEN) if short else str(int(time.time())) + "-" + str(ProtocolEntity.__ID_GEN)

    def toProtocolTreeNode(self):
        pass

    @staticmethod
    def fromProtocolTreeNode(protocolTreeNode):
        pass
