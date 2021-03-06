"""Common configuration constants
"""

PROJECTNAME = 'uwosh.timeslot'

ADD_PERMISSIONS = {
    'Person': 'uwosh.timeslot: Add Person',
    'Time Slot': 'uwosh.timeslot: Add Time Slot',
    'Day': 'uwosh.timeslot: Add Day',
    'Signup Sheet': 'uwosh.timeslot: Add Signup Sheet',
}


DefaultExtraFields = [
    'phone|Phone',
    'department|Department',
    'classification|Employee Classification|Academic<Academic Staff>,Classified<Classified Staff>,Faculty,LTE<Limited Term Employee>,Other,Spouse - Faculty,Student'
]
