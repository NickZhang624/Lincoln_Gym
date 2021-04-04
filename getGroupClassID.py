import uuid

def getGroupClassID():
    return uuid.uuid4().fields[3]

print(getGroupClassID())