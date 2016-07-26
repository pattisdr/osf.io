import Ember from 'ember';

export default Ember.Component.extend({
    isOpen: false,
    removeSelf: Ember.computed('contributorToRemove', 'currentUser', function() {
        if (this.get('contributorToRemove')) {
            return this.get('contributorToRemove').id.split('-')[1] === this.get('currentUser').id;
        } else {
            return false;
        }
    }),
    actions: {
        removeContributor(contrib) {
            this.sendAction('removeContributor', contrib);
        },
        close() {
            this.set('isOpen', false);
        }
    }
});
