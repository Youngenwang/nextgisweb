import { createApp } from "vue";
import { DatePicker } from "ant-design-vue";


import Component from "./component.vue";
import SystemNameForm from "@nextgisweb/pyramid/SystemNameForm.vue"

export function test(el) {
    createApp(Component).mount(el)
}

export function antd(el) {
    createApp(SystemNameForm).mount(el)
}
 