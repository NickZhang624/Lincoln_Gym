import uuid

def genID():
    return uuid.uuid4().fields[3]

print(genID())