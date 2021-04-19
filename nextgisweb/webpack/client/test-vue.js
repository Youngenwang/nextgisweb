import {createApp} from "vue";
import Component from "./component.vue";

export function test(el) {
    createApp(Component).mount(el)
}