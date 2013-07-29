from zope.interface import implements, Interface

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.validation import validation
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from plone.memoize import instance

from Products.contentmigration.utils import unrestricted_move


class ISubmitSelection(Interface):
    pass


class SubmitSelection(BrowserView):
    implements(ISubmitSelection)

    resultTemplate = ZopeTwoPageTemplateFile('signupresults.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @instance.memoize
    def extra_fields(self):
        return self.context.getExtraFieldsVocabulary()

    def submitUserSelection(self):
        self.results = list()

        self.getUserInput()
        self.getMemberInfo()

        if not self.areAnyRequiredFieldsEmpty() \
           and self.isAtLeastOneSlotSelected():
            for slotLabel in self.selectedSlots:
                self.getSlotAndSignUserUpForIt(slotLabel)

        return self.resultTemplate()

    def getUserInput(self):
        for (field, _) in self.extra_fields():
            setattr(self, field, self.request.get(field, ''))

        self.selectedSlots = self.request.get('slotSelection', None)

        if type(self.selectedSlots) != list:
            self.selectedSlots = [self.selectedSlots]

        self.confirmation = bool(self.request.get('confirmation',
                                                  None))

    def getMemberInfo(self):
        portal_membership = getToolByName(self, 'portal_membership')
        member = portal_membership.getAuthenticatedMember()

        self.username = member.getUserName()
        self.fullname = member.getProperty('fullname')
        if self.fullname == '':
            self.fullname = self.username
        self.email = member.getProperty('email')

    def isAtLeastOneSlotSelected(self):
        return self.selectedSlots != [None]

    def areAnyRequiredFieldsEmpty(self):
        return len(self.getListOfEmptyRequiredFields()) > 0

    def getListOfEmptyRequiredFields(self):
        fieldNames = dict(self.extra_fields())
        emptyRequiredFields = []

        requiredExtraFields = self.context.getExtraFields()
        for field in requiredExtraFields:
            if (len(getattr(self, field)) < 1) and (field in fieldNames):
                emptyRequiredFields.append(fieldNames[field])

        return emptyRequiredFields

    def getSlotAndSignUserUpForIt(self, slotLabel):
        status = 'error'
        waiting = True
        message = ''

        allowSignupForMultipleSlots = self.context.getAllowSignupForMultipleSlots()

        (date, time) = slotLabel.split(' @ ')
        day = self.context.getDay(date)
        timeSlot = day.getTimeSlot(time)
        allowWaitingList = timeSlot.getAllowWaitingList()
        numberOfAvailableSpots = timeSlot.getNumberOfAvailableSpots()

        if timeSlot.isCurrentUserSignedUpForThisSlot():
            status = 'error'
            message = 'You are already signed up for this slot.'

        elif (not allowSignupForMultipleSlots) \
             and numberOfAvailableSpots > 0 \
             and self.context.isCurrentUserSignedUpForAnySlot():
            current_slot = self.context.getSlotsCurrentUserIsSignedUpFor()[0]

            if not self.confirmation:
                status = 'confirm'
                message = current_slot.getLabel()

            else:
                user_id = self.context.getCurrentUsername()
                unrestricted_move(timeSlot,
                                  current_slot._getOb(user_id))
                status = 'success'
                waiting = False

        elif allowWaitingList or numberOfAvailableSpots > 0:
            person = self.createPersonObject(timeSlot)

            if numberOfAvailableSpots > 0:
                self.signupPerson(person)
                waiting = False
            elif self.isEmailValid():
                self.sendWaitingListConfirmationEmail(self.context, slotLabel)

            status = 'success'

        else:
            # if (not AllowWait) and (spots == 0)

            # This expression covering the cases here can be derived
            # from simplifying the full expression that describes the
            # cases covered by this last branching from the IF
            # statement:
            #
            #       not signedUpForThisSlot
            #   and not (not Multi and (spots > 0) and SignupAny)
            #   and not (AllowWait or (spots > 0))
            #
            # Pulling out the common NOT
            #
            #   not (   signedupForThisSlot
            #        or (not Multi and (spots > 0) and SignupAny)
            #        or AllowWait
            #        or (spots > 0)
            #       )
            #
            # It is clear from this that this suite of the IF
            # statement will only be executed when all of the four
            # OR'ed expressions are false. The first expression will
            # always be as we false, because its True value is
            # captured by the first test expression of the IF
            # statement. The second expression is redundant as it
            # evaluates to false whenever the last one is False, hence
            # we can simplify the expression to:
            #
            #   not (False or AllowWait or (spots > 0))
            #
            # Distributing the NOT:
            #
            #   True and (not AllowWait) and (not (spots > 0))
            #
            # Or the more readable form (given that spots can't be
            # negative) and removing the redundant True:
            #
            #   (not AllowWait) and (spots == 0)

            status = 'error'
            message = 'The slot you selected is already full. Please select a different one'

        result = dict()
        result['slotLabel'] = slotLabel
        result['status']  = status
        result['waiting'] = waiting
        result['message'] = message
        self.results.append(result)

    def createPersonObject(self, container):
        container.invokeFactory('Person', self.username)
        newPerson = container[self.username]
        newPerson.setEmail(self.email)
        newPerson.setTitle(self.fullname)
        for (field, _) in self.extra_fields():
            setattr(newPerson, field, getattr(self, field))
        newPerson.reindexObject()
        return newPerson

    def signupPerson(self, person):
        portal_workflow = getToolByName(self, 'portal_workflow')
        portal_workflow.doActionFor(person, 'signup')
        person.reindexObject()

    def isEmailValid(self):
        isEmail = validation.validatorFor('isEmail')
        return isEmail(self.email) == 1

    def sendWaitingListConfirmationEmail(self, signupSheet, slotLabel):
        url = signupSheet.absolute_url()

        extraEmailContent = signupSheet.getExtraEmailContent()
        contactInfo = signupSheet.getContactInfo()
        toEmail = self.email
        fromEmail = "%s <%s>" % (self.context.email_from_name,
                                 self.context.email_from_address)
        subject = signupSheet.Title() + ' - Waiting List Confirmation'

        message = 'Hi ' + self.fullname + ',\n\n'
        message += 'This message is to confirm that you have been added to the waiting list for:\n'
        message += slotLabel + '\n\n'

        if extraEmailContent != ():
            for line in extraEmailContent:
                message += line + '\n'
            message += '\n'

        message += url + '\n\n'

        if contactInfo != ():
            message += 'If you have any questions please contact:\n'
            for line in contactInfo:
                message += line + '\n'
            message += '\n'

        mailHost = self.context.MailHost
        mailHost.secureSend(message, toEmail, fromEmail, subject)
