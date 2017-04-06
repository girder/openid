import datetime
import time
from girder.utility.model_importer import ModelImporter
from openid import association, oidutil
from openid.store import interface, nonce

class GirderStore(interface.OpenIDStore, ModelImporter):
    """
    Stores persistent OpenID data using Girder's persistence
    layer, namely the association and nonce models in this plugin.
    """
    def storeAssociation(self, server_url, association):
        self.model('association', 'openid').save({
            'url': server_url,
            'handle': association.handle,
            'secret': oidutil.toBase64(association.secret),
            'issued': association.issued,
            'lifetime': association.lifetime,
            'type': association.assoc_type,
            'expires': datetime.datetime.utcnow() + datetime.timedelta(seconds=association.lifetime)
        })

    def _mkAssoc(self, doc):
        return association.Association(
            handle=doc['handle'], secret=oidutil.fromBase64(doc['secret']), issued=doc['issued'],
            lifetime=doc['lifetime'], assoc_type=doc['type'])

    def getAssociation(self, server_url, handle=None):
        q = {
            'url': server_url
        }

        if handle is not None:
            q['handle'] = handle

        assocs = [self._mkAssoc(d) for d in self.model('association', 'openid').find(q)]
        if not assocs:
            return None
        if handle is not None:
            return assocs[0]

        def _key(assoc):
            return assoc.issued

        return min(assocs, key=_key)

    def removeAssociation(self, server_url, handle):
        model = self.model('association', 'openid')
        assoc = model.findOne({
            'url': server_url,
            'handle': handle
        })
        if assoc:
            model.remove(assoc)

    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > nonce.SKEW:
            return False

        model = self.model('nonce', 'openid')
        n = ''.join((server_url, str(timestamp), salt))
        if model.findOne({'_id': n}):
            return False

        model.save({
            '_id': n,
            'expires': datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        })
        return True

    def cleanupNonces(self):
        pass

    def cleanupAssociations(self):
        pass

    def cleanup(self):
        pass
