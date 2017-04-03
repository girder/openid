import LoginView from 'girder/views/layout/LoginView';
import { wrap } from 'girder/utilities/PluginUtils';

import OpenIdLoginView from './OpenIdLoginView';

wrap(LoginView, 'render', function (render) {
    render.call(this);
    new OpenIdLoginView({
        el: this.$('.modal-body'),
        parentView: this
    }).render();
    return this;
});
