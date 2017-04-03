import View from 'girder/views/View';
import { apiRoot, restRequest } from 'girder/rest';
import { splitRoute } from 'girder/misc';

import OpenIdLoginViewTemplate from '../templates/openIdLoginView.pug';
import '../stylesheets/openIdLoginView.styl';

var OpenIdLoginView = View.extend({
    events: {
        'click .g-openid-button': function (event) {
            event.preventDefault();
            var url = $(event.currentTarget).attr('g-url');
            url = window.encodeURIComponent(url);
            window.location = `${apiRoot}/openid/login?url=${url}&redirect=`;
        }
    },

    initialize: function (settings) {
        this.modeText = settings.modeText || 'log in';
        this.providers = null;

        restRequest({
            path: 'openid/provider'
        }).done(resp => {
            this.providers = resp;
            this.render();
        });
    },

    render: function () {
        if (this.providers === null) {
            return;
        }

        if (this.providers.length) {
            this.$el.append(OpenIdLoginViewTemplate({
                modeText: this.modeText,
                providers: this.providers
            }));
        }

    },
});

export default OpenIdLoginView;
