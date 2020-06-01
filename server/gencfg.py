import os
print('MONGO_URI  = "mongodb://localhost:27017/feeds"')
print('SECRET_KEY = "{}"'.format(os.urandom(16).hex()))
print('API_KEY    = "{}"'.format(os.urandom(16).hex()))
