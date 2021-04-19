<%inherit file='nextgisweb:templates/base.mako' />

<div id="el"></div>

<div id="datePicker"></div>

<script>
    require(["@nextgisweb/jsrealm/test-vue"], function (module) {
        module.test("#el");
        module.antd("#datePicker");
    })
</script>