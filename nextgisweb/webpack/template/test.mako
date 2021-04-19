<%inherit file='nextgisweb:templates/base.mako' />

<button id="testDijit">Test dijit</button>
<button id="testLodash">Test lodash</button>
<button id="testMixed">Test mixed</button>

<script>
    require(["dojo/domReady!"], function () {
        document.getElementById("testDijit").onclick = function () {
            require(['@nextgisweb/webpack/test-dijit'], function (module) {
                module.test();
            })
        };
        document.getElementById("testLodash").onclick = function () {
            require(['@nextgisweb/webpack/test-lodash'], function (module) {
                module.test();
            })
        };
        document.getElementById("testMixed").onclick = function () {
            require(['@nextgisweb/webpack/test-mixed'], function (module) {
                module.test();
            })
        };
    })
</script>