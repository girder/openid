from girder.models.model_base import Model


class Association(Model):
    def initialize(self):
        self.name = 'openid_association'
        self.ensureIndices((
            'url',
            ([('url', 1), ('handle', 1)], {}),
            ('expires', {'expireAfterSeconds': 0})
        ))

    def validate(self, doc):
        return doc


class Nonce(Model):
    def initialize(self):
        self.name = 'openid_nonce'
        self.ensureIndex(('expires', {'expireAfterSeconds': 0}))

    def validate(self, doc):
        return doc
