<%inherit file='nextgisweb:pyramid/template/base.mako' />

<%def name="head()">
    <% import json %>
    <script type="text/javascript">
        require([
            "@nextgisweb/pyramid/SystemNameForm.vue",
            "dojo/domReady!"
        ], function (Form) {
            Form.default.app().mount('#form');
        });
    </script>
</%def>

<div id="form" style="width: 100%;"></div>
