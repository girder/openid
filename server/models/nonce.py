from girder.models.model_base import Model


class Nonce(Model):
    def initialize(self):
        self.name = 'openid_nonce'
        self.ensureIndex(('expires', {'expireAfterSeconds': 0}))

    def validate(self, doc):
        return doc
