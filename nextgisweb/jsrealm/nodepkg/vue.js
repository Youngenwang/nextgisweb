import { createApp } from 'vue';

export function appHelper(component) {
    component.app = function () {
        return createApp(component)
    };
    return component
}