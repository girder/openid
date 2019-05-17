import View from '@girder/core/views/View';
import { getApiRoot, restRequest } from '@girder/core/rest';
import { splitRoute } from '@girder/core/misc';

import OpenIdLoginViewTemplate from '../templates/openIdLoginView.pug';
import '../stylesheets/openIdLoginView.styl';

var OpenIdLoginView = View.extend({
    events: {
        'click .g-openid-button': function (event) {
            event.preventDefault();
            var url = $(event.currentTarget).attr('g-url');
            url = window.encodeURIComponent(url);
            window.location = `${getApiRoot()}/openid/login?url=${url}&redirect=`;
        }
    },

    initialize: function (settings) {
        this.modeText = settings.modeText || 'log in';
        this.providers = null;

        restRequest({
            url: 'openid/provider'
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
