from zope.interface import implements, Interface

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.utils import contentDispositionHeader

from uwosh.timeslot import timeslotMessageFactory as _

import time

class IManagerSummary(Interface):
    """
    ManagerSummary view interface
    """


class ManagerSummary(BrowserView):
    """
    ManagerSummary browser view
    """
    implements(IManagerSummary)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def portal_catalog(self):
        return getToolByName(self.context, 'portal_catalog')

    @property
    def portal(self):
        return getToolByName(self.context, 'portal_url').getPortalObject()
        
    def removeAllPeople(self):
        self.context.removeAllPeople()
        self.request.response.redirect(self.context.absolute_url())
        
    def exportToCSV(self):
        currentDateTime = time.strftime('%Y%m%d%H%M', time.localtime())
        filename = '%s-%s.csv' % (self.context.Title(), currentDateTime)
        header_value = contentDispositionHeader('attachment', self.context.getCharset(), filename=filename)
        
        self.request.response.setHeader("Content-Disposition", header_value)
        self.request.response.setHeader("Content-Type", 'text/comma-separated-values;charset=%s' % self.context.getCharset())
        
        return self.context.exportToCSV()
