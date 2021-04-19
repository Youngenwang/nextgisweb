<template>
    <Form :model="data" layout="vertical">
        <FormItem label="Web GIS name">
            <Input v-model:value="data.full_name"/>
        </FormItem>
        <FormItem>
            <Button type="primary" @click="save">Submit</Button>
        </FormItem>
    </Form>
</template>


<script>
    import { ref } from "vue";
    import { Form, Input, Button } from "ant-design-vue";
    import route from "ngw/route";

    const API_URL = route.pyramid.system_name();

    export default {
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
            }
        },
        components: {
            Form: Form,
            FormItem: Form.Item,
            Input,
            Button
        }
    }
</script>