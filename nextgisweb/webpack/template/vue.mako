<%inherit file='nextgisweb:templates/base.mako' />

<div id="el"></div>

<script>
    require(["@nextgisweb/webpack/test-vue"], function (module) {
        module.test("#el");
    })
</script>