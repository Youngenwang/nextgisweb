import { createApp } from "vue";
import { DatePicker } from "ant-design-vue";


import Component from "./component.vue";


export function test(el) {
    createApp(Component).mount(el)
}

export function antd(el) {
    createApp(DatePicker).mount(el)
}