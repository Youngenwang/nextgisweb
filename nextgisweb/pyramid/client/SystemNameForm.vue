<template>
    <Form :model="data" layout="horizontal">
        <FormItem>
            <Input v-model:value="data.full_name"/>
        </FormItem>
        <FormItem>
            <Button type="primary" @click="save">Save</Button>
        </FormItem>
    </Form>
</template>


<script>
    import { ref } from "vue";
    import { Form, Input, Button } from "ant-design-vue";
    import { appHelper } from "@nextgisweb/webpack/vue.js";
    import route from "ngw/route";

    const API_URL = route.pyramid.system_name();

    export default appHelper({
        setup() {
            const data = ref({});
            fetch(API_URL)
                .then(resp => resp.json())
                .then(payload => data.value = payload)
            return { data }
        },
        methods: {
            async save() {
                const response = await fetch(API_URL, {
                    method: "PUT",
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.data)
                });
                window.location.replace(route.pyramid.control_panel());
            }
        },
        components: {
            Form: Form,
            FormItem: Form.Item,
            Input,
            Button
        }
    })
</script>